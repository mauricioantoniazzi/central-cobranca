"""Registro das cobranças feitas pela Central. Guardado à parte da planilha da empresa.

  Base_bruta.xlsx                    dado da empresa: a Central só LÊ, nunca escreve.
  dados/cobrancas_registradas.json   o que foi registrado aqui (a pasta pode ser trocada com CENTRAL_DADOS).
  dados/configuracao.json            a assinatura que sai nos textos.

A hora de cada registro vem do relógio da base (relogio.py): data de referência + hora do computador.
"""
import json
import os
import threading
from datetime import datetime, timedelta

import relogio

PASTA = os.path.dirname(os.path.abspath(__file__))
CANAIS = ("WhatsApp", "E-mail", "Telefone")
_trava = threading.Lock()


def pasta_dados():
    return os.environ.get("CENTRAL_DADOS") or os.path.join(PASTA, "dados")


def arquivo():
    return os.path.join(pasta_dados(), "cobrancas_registradas.json")


def arquivo_config():
    return os.path.join(pasta_dados(), "configuracao.json")


def _ler(caminho, padrao):
    if not os.path.exists(caminho):
        return padrao
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _gravar(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    os.replace(tmp, caminho)  # grava inteiro ou não grava: nunca deixa arquivo pela metade


def _vazio():
    return {"versao": 1, "proximo_id": 1, "registros": []}


def listar():
    """Registros da Central, mais recentes primeiro, com 'quando' como datetime."""
    with _trava:
        dados = _ler(arquivo(), _vazio())
    out = []
    for r in dados["registros"]:
        r = dict(r)
        r["quando"] = datetime.fromisoformat(r["quando"])
        out.append(r)
    out.sort(key=lambda r: (r["quando"], r["id"]), reverse=True)
    return out


def como_cobrancas():
    """No mesmo formato das cobranças da planilha, para alimentar a tela Hoje."""
    return [{"cliente": r["cliente"], "quando": r["quando"], "canal": r["canal"], "tom": r["tom"],
             "valor": r["valor"], "n_titulos": len(r["titulos"]), "origem": "Central", "id": r["id"]}
            for r in listar()]


def registrar(ref, cliente, canal, tom_chave, tom_nome, valor, titulos, mensagem):
    if canal not in CANAIS:
        raise ValueError("canal inválido: %r" % canal)
    if not isinstance(valor, int) or valor < 0:
        raise ValueError("valor deve ser inteiro em centavos")
    if not titulos:
        raise ValueError("escolha ao menos um título")
    quando = relogio.agora(ref)
    with _trava:
        dados = _ler(arquivo(), _vazio())
        rid = dados["proximo_id"]
        dados["proximo_id"] = rid + 1
        dados["registros"].append({
            "id": rid, "cliente": int(cliente), "quando": quando.isoformat(timespec="minutes"), "canal": canal,
            "tom_chave": tom_chave, "tom": tom_nome, "valor": valor, "titulos": list(titulos), "mensagem": mensagem})
        _gravar(arquivo(), dados)
    return rid, quando


def remover(rid):
    with _trava:
        dados = _ler(arquivo(), _vazio())
        antes = len(dados["registros"])
        dados["registros"] = [r for r in dados["registros"] if r["id"] != rid]
        _gravar(arquivo(), dados)
    return len(dados["registros"]) < antes


def assinatura():
    with _trava:
        return _ler(arquivo_config(), {}).get("assinatura", "")


def salvar_assinatura(nome):
    with _trava:
        cfg = _ler(arquivo_config(), {})
        cfg["assinatura"] = nome.strip()[:80]
        _gravar(arquivo_config(), cfg)


def resumo_contatos(cobrancas, agora, dias=7):
    """Contatos de cobrança nos últimos `dias` dias (planilha da empresa + Central), no relógio da base."""
    ini = agora.replace(hour=0, minute=0) - timedelta(days=dias - 1)
    rec = [c for c in cobrancas if ini <= c["quando"] <= agora.replace(hour=23, minute=59)]
    return {"n": len(rec), "valor": sum(c["valor"] for c in rec), "n_clientes": len({c["cliente"] for c in rec}),
            "ini": ini.date()}
