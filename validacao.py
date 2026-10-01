"""Validação da planilha. Duas categorias:

  erros(...)  : problema que impede o cálculo (levanta BaseInvalida com uma mensagem que diz O QUE está errado e ONDE).
  avisos(...) : a Central funciona, mas alguém precisa olhar (aparece num quadro amarelo em Hoje e em Risco).

Nenhuma validação altera dado: só lê e avisa.
"""
from collections import Counter


class BaseInvalida(Exception):
    """A planilha tem um problema que impede o cálculo. str(e) é a explicação para quem vai corrigir a planilha."""


def erros(ref, clientes, titulos, cobrancas):
    if not clientes:
        raise BaseInvalida("a aba Clientes não tem nenhuma linha.")
    if not titulos:
        raise BaseInvalida("a aba Títulos não tem nenhuma linha.")
    desconhecidos = sorted({t["cliente"] for t in titulos} - set(clientes))
    if desconhecidos:
        exemplos = [t["numero"] for t in titulos if t["cliente"] in desconhecidos][:3]
        raise BaseInvalida(
            "a aba Títulos tem título(s) do(s) cliente(s) de código %s, que não existe(m) na aba Clientes (por exemplo %s). "
            "Cadastre o cliente na aba Clientes ou corrija o código." % (", ".join(map(str, desconhecidos)), ", ".join(exemplos)))
    repetidos = [n for n, q in Counter(t["numero"] for t in titulos).items() if q > 1]
    if repetidos:
        raise BaseInvalida("há número de título repetido na aba Títulos (por exemplo %s). Cada título deve aparecer uma vez só."
                           % ", ".join(map(str, repetidos[:3])))


def avisos(ref, clientes, titulos, cobrancas):
    out = []
    com_titulo = {t["cliente"] for t in titulos}
    sem = [c["nome"] for cod, c in clientes.items() if cod not in com_titulo]
    if sem:
        out.append("Cliente cadastrado sem nenhum título, por isso fora das telas de risco e de previsão: %s." % ", ".join(sem))
    futuros = [t for t in titulos if t["pagamento"] and t["pagamento"] > ref]
    if futuros:
        out.append("%d título%s com data de pagamento depois da data de referência (%s), como %s. Confira a data da aba Leia-me."
                   % (len(futuros), "" if len(futuros) == 1 else "s", ref.strftime("%d/%m/%Y"), futuros[0]["numero"]))
    emitidos_depois = [t for t in titulos if t["emissao"] > ref]
    if emitidos_depois:
        out.append("%d título%s emitido%s depois da data de referência, como %s."
                   % (len(emitidos_depois), "" if len(emitidos_depois) == 1 else "s", "" if len(emitidos_depois) == 1 else "s",
                      emitidos_depois[0]["numero"]))
    invertidos = [t for t in titulos if (t["pagamento"] and t["pagamento"] < t["emissao"]) or t["vencimento"] < t["emissao"]]
    if invertidos:
        out.append("%d título%s com data incoerente (pagamento ou vencimento antes da emissão), como %s."
                   % (len(invertidos), "" if len(invertidos) == 1 else "s", invertidos[0]["numero"]))
    fora = sorted({c["cliente"] for c in cobrancas} - set(clientes))
    if fora:
        out.append("A aba Cobranças cita cliente(s) de código %s que não estão na aba Clientes; esses contatos foram ignorados."
                   % ", ".join(map(str, fora)))
    if not any(t["pagamento"] is None and t["vencimento"] < ref for t in titulos):
        out.append("Nenhum título está vencido na data de referência; a fila de Hoje fica vazia.")
    return out
