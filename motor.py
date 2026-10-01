"""Cálculo da fila "Hoje". Tudo sai da planilha; valores em centavos (int)."""
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

import relogio
import validacao
from validacao import BaseInvalida
from leitor_xlsx import Planilha, data_por_extenso, serial_para_data, serial_para_datahora

# --- Parâmetros do método (não são dados da empresa; são escolhas de cálculo) ---
PESO_VALOR = 0.40            # peso do valor vencido no score (0 a 1)
PESO_RISCO = 0.60            # peso do risco no score; o risco é o índice da tela Risco por cliente (0 a 100)
HORAS_SEM_INSISTIR = 48      # quem foi cobrado há menos que isso desce na fila
FATOR_COBRADO_RECENTE = 0.35 # multiplicador do score de quem foi cobrado na janela acima


def centavos(valor):
    c = valor * 100
    assert c == c.to_integral_value(), "valor com fração de centavo"
    return int(c)


def carregar(caminho):
    p = Planilha(caminho)

    ref = None
    for lin in p.linhas("Leia-me"):
        if lin and lin[0] and "REFER" in str(lin[0]).upper():
            if len(lin) < 2 or lin[1] is None:
                raise BaseInvalida("na aba Leia-me, a linha 'DATA DE REFERÊNCIA' está sem data ao lado.")
            try:
                ref = data_por_extenso(lin[1])
            except ValueError as e:
                raise BaseInvalida("aba Leia-me: " + str(e))
    if not ref:
        raise BaseInvalida("a aba Leia-me não tem a linha 'DATA DE REFERÊNCIA' com a data ao lado (ex.: 12 de setembro de 2026).")

    clientes = {}
    for i, r in enumerate(p.tabela("Clientes"), 2):
      with _linha("Clientes", i):
        cod = int(r["Código do cliente"])
        clientes[cod] = {
            "codigo": cod,
            "nome": r["Nome do cliente"],
            "categoria": r["Categoria"],
            "regiao": r["Região"],
            "prazo_dias": int(r["Prazo em dias"]),
            "limite": centavos(r["Limite de crédito"]),
            "contato": r["Contato"],
            "telefone": r.get("Telefone") or "",
            "desde": serial_para_data(r["Cliente desde"]),
        }

    titulos = []
    for i, r in enumerate(p.tabela("Títulos"), 2):
      with _linha("Títulos", i):
        pg = r["Data de pagamento"]
        titulos.append({
            "numero": r["Número do título"],
            "cliente": int(r["Código do cliente"]),
            "emissao": serial_para_data(r["Data de emissão"]),
            "valor": centavos(r["Valor do título"]),
            "vencimento": serial_para_data(r["Data de vencimento"]),
            "pagamento": serial_para_data(pg) if pg is not None else None,
        })

    cobrancas = []
    for i, r in enumerate(p.tabela("Cobranças"), 2):
      with _linha("Cobranças", i):
        cobrancas.append({
            "cliente": int(r["Código do cliente"]),
            "quando": serial_para_datahora(r["Data e hora do contato"]),
            "canal": r["Canal"],
            "tom": r["Tom usado"],
            "valor": centavos(r["Valor cobrado"]),
            "n_titulos": int(r["Títulos na cobrança"]),
            "origem": "Planilha",
        })
    validacao.erros(ref, clientes, titulos, cobrancas)
    return ref, clientes, titulos, cobrancas


class _linha:
    """Diz a aba e a linha da planilha quando um valor não se deixa ler (coluna faltando, data vazia, texto no lugar de número)."""

    def __init__(self, aba, linha):
        self.aba, self.linha = aba, linha

    def __enter__(self):
        return self

    def __exit__(self, tipo, erro, tb):
        if erro is None or isinstance(erro, BaseInvalida):
            return False
        if isinstance(erro, KeyError):
            raise BaseInvalida("aba %s: não encontrei a coluna %s (linha %d). Os títulos das colunas precisam ser os mesmos da base original."
                               % (self.aba, erro, self.linha))
        raise BaseInvalida("aba %s, linha %d: tem uma data ou um valor em branco, ou texto onde devia haver número ou data. "
                           "Confira as células dessa linha." % (self.aba, self.linha))


def calcular(caminho, extras=None, agora=None, leitura=None):
    """Fila "Hoje". `extras`: cobranças registradas na Central, somadas às da planilha.
    `agora`: o relógio da base (data de referência + hora do computador); ver relogio.py.
    `leitura`: {código do cliente: leitura de risco de risco.analisar}. O risco da fila é o MESMO índice que a tela
    Risco por cliente mostra; não existe um segundo cálculo de risco aqui."""
    if leitura is None:
        raise ValueError("motor.calcular precisa da leitura de risco (risco.analisar): passe leitura={codigo: r}")
    ref, clientes, titulos, cobrancas = carregar(caminho)
    cobrancas = cobrancas + list(extras or [])
    agora = agora or relogio.agora(ref)

    por_cliente = defaultdict(list)
    for t in titulos:
        por_cliente[t["cliente"]].append(t)

    abertos = [t for t in titulos if t["pagamento"] is None]
    vencidos = [t for t in abertos if t["vencimento"] < ref]

    resumo = {
        "data_ref": ref,
        "n_titulos": len(titulos),
        "n_clientes": len(clientes),
        "primeira_emissao": min(t["emissao"] for t in titulos),
        "ultima_emissao": max(t["emissao"] for t in titulos),
        "aberto": sum(t["valor"] for t in abertos),
        "n_abertos": len(abertos),
        "vencido": sum(t["valor"] for t in vencidos),
        "n_vencidos": len(vencidos),
        "a_vencer": sum(t["valor"] for t in abertos if t["vencimento"] >= ref),
    }
    assert resumo["aberto"] == resumo["vencido"] + resumo["a_vencer"]

    # Semana = os 7 dias até a data da base, inclusive. "Entrou" = pago nessa janela; "venceu e não entrou" =
    # venceu nessa janela e continua em aberto. Estes números moram aqui; a tela Hoje e o relatório leem daqui.
    ini7 = ref - timedelta(days=6)
    ini8s = ini7 - timedelta(days=56)
    entrou = [t for t in titulos if t["pagamento"] and ini7 <= t["pagamento"] <= ref]
    anteriores = [t for t in titulos if t["pagamento"] and ini8s <= t["pagamento"] < ini7]
    venceu7 = [t for t in titulos if ini7 <= t["vencimento"] <= ref]
    resumo.update({
        "janela_ini": ini7,
        "entrou_7d": sum(t["valor"] for t in entrou),
        "n_entrou_7d": len(entrou),
        "n_clientes_entrou_7d": len({t["cliente"] for t in entrou}),
        "entrou_media_8s": sum(t["valor"] for t in anteriores) // 8,
        "venceu_7d": sum(t["valor"] for t in venceu7),
        "n_venceu_7d": len(venceu7),
        "venceu_7d_aberto": sum(t["valor"] for t in venceu7 if t["pagamento"] is None),
        "n_venceu_7d_aberto": sum(1 for t in venceu7 if t["pagamento"] is None),
    })

    ultima_cobranca = {}
    for c in sorted(cobrancas, key=lambda c: c["quando"]):
        ultima_cobranca[c["cliente"]] = c

    fila = []
    for cod, cli in clientes.items():
        venc = sorted((t for t in vencidos if t["cliente"] == cod), key=lambda t: t["vencimento"])
        if not venc:
            continue
        r = leitura[cod]
        for t in venc:
            t["dias_atraso"] = (ref - t["vencimento"]).days
        total = sum(t["valor"] for t in venc)
        assert total == r["vencido"], "vencido da fila difere do vencido da leitura de risco (%s)" % cli["nome"]

        cob = ultima_cobranca.get(cod)
        horas = max(0.0, (agora - cob["quando"]).total_seconds() / 3600) if cob else None
        cobrado_recente = horas is not None and horas < HORAS_SEM_INSISTIR

        fila.append({
            "cliente": cli, "titulos": venc, "vencido": total, "n": len(venc),
            "mais_antigo": venc[0]["dias_atraso"], "leitura": r,
            "indice": r["indice"], "risco": r["indice"] / 100,
            "cobranca": cob, "horas_desde_cobranca": horas, "cobrado_recente": cobrado_recente,
        })

    maior = max((f["vencido"] for f in fila), default=1)  # fila vazia (nada vencido) é um resultado válido
    for f in fila:
        f["valor_rel"] = (f["vencido"] / maior) ** 0.5
        base = 100 * (PESO_VALOR * f["valor_rel"] + PESO_RISCO * f["risco"])
        f["score_base"] = base
        f["score"] = base * (FATOR_COBRADO_RECENTE if f["cobrado_recente"] else 1)

    fila.sort(key=lambda f: (-f["score"], -f["vencido"]))
    for i, f in enumerate(fila, 1):
        f["posicao"] = i
    assert sum(f["vencido"] for f in fila) == resumo["vencido"]
    resumo["n_clientes_vencido"] = len(fila)
    return resumo, fila
