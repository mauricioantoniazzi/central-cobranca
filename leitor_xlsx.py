"""Leitor mínimo de .xlsx usando só a biblioteca padrão (zipfile + xml).

Números saem como Decimal (nunca float), textos como str, vazios como None.
"""
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _chave(texto):
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return sem_acento.casefold().strip()


def _coluna(ref):
    letras = re.match(r"[A-Z]+", ref).group()
    n = 0
    for c in letras:
        n = n * 26 + ord(c) - 64
    return n - 1


def _texto_de(no):
    return "".join(t.text or "" for t in no.iter("{%s}t" % NS["m"]))


class Planilha:
    def __init__(self, caminho):
        self._z = zipfile.ZipFile(caminho)
        self._compartilhadas = self._ler_compartilhadas()
        self._abas = self._mapear_abas()

    def _ler_compartilhadas(self):
        if "xl/sharedStrings.xml" not in self._z.namelist():
            return []
        raiz = ET.fromstring(self._z.read("xl/sharedStrings.xml"))
        return [_texto_de(si) for si in raiz.findall("m:si", NS)]

    def _mapear_abas(self):
        wb = ET.fromstring(self._z.read("xl/workbook.xml"))
        rels = ET.fromstring(self._z.read("xl/_rels/workbook.xml.rels"))
        alvo = {r.get("Id"): r.get("Target") for r in rels.findall("rel:Relationship", NS)}
        abas = {}
        for s in wb.find("m:sheets", NS):
            rid = s.get("{%s}id" % NS["r"])
            abas[_chave(s.get("name"))] = "xl/" + alvo[rid].lstrip("/").replace("xl/", "")
        return abas

    def linhas(self, nome_aba):
        """Lista de linhas; cada linha é uma lista de valores (str, Decimal ou None)."""
        raiz = ET.fromstring(self._z.read(self._abas[_chave(nome_aba)]))
        saida = []
        for row in raiz.find("m:sheetData", NS):
            valores = []
            for c in row.findall("m:c", NS):
                idx = _coluna(c.get("r"))
                while len(valores) <= idx:
                    valores.append(None)
                tipo = c.get("t")
                if tipo == "inlineStr":
                    valores[idx] = _texto_de(c.find("m:is", NS))
                else:
                    v = c.find("m:v", NS)
                    if v is None or v.text is None:
                        continue
                    if tipo == "s":
                        valores[idx] = self._compartilhadas[int(v.text)]
                    elif tipo == "str":
                        valores[idx] = v.text
                    else:
                        valores[idx] = Decimal(v.text)
            saida.append(valores)
        return saida

    def tabela(self, nome_aba):
        """Primeira linha como cabeçalho; devolve lista de dicts {cabeçalho: valor}."""
        linhas = self.linhas(nome_aba)
        cab = linhas[0]
        registros = []
        for lin in linhas[1:]:
            if not any(v is not None for v in lin):
                continue
            lin = lin + [None] * (len(cab) - len(lin))
            registros.append({cab[i]: lin[i] for i in range(len(cab)) if cab[i]})
        return registros


def serial_para_data(n):
    return date(1899, 12, 30) + timedelta(days=int(n))


def serial_para_datahora(n):
    minutos = int((n - int(n)) * 24 * 60 + Decimal("0.5"))
    return datetime(1899, 12, 30) + timedelta(days=int(n), minutes=minutos)


MESES = {m: i + 1 for i, m in enumerate(
    "janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro".split())}


def _sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower().strip(". ")


def data_por_extenso(valor):
    """Data de referência da aba Leia-me. Aceita '12 de agosto de 2026' (também 'set' ou 'set.'), '12/08/2026',
    '2026-08-12' e uma data do Excel. Se não entender, levanta ValueError dizendo o que esperava."""
    if isinstance(valor, Decimal):
        return serial_para_data(valor)
    t = str(valor).strip()
    m = re.match(r"(\d{1,2})\s+de\s+([A-Za-zÀ-ú.]+)\s+de\s+(\d{4})", t, re.I)
    if m:
        nome = _sem_acento(m.group(2))
        numero = MESES.get(nome) or next((n for k, n in MESES.items() if len(nome) >= 3 and k.startswith(nome)), None)
        if numero:
            return date(int(m.group(3)), numero, int(m.group(1)))
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    raise ValueError("não entendi a data de referência %r; escreva como '12 de setembro de 2026' ou '12/09/2026'" % t)
