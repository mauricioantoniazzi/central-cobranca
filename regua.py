"""Régua de cobrança: que tom usar com cada cliente, por quê, e os fatos que alimentam o texto.

Nada aqui escreve texto para o cliente (isso é redacao.py). Aqui só se decide o tom a partir dos números
que as outras telas já calculam (risco.py e motor.py) e se monta o dicionário de fatos do texto.
"""
from datetime import datetime, timedelta

from frases import arred, reais
from risco import MESES_NOME  # noqa: F401  (mantido para quem importa daqui)

GRANDE_PCT_FAT = 0.10    # cliente "grande" = pesa 10% ou mais do faturamento dos últimos 12 meses
POSICAO_DESVIO = 0.90    # título mais lento que 90% dos pagamentos do próprio cliente conta como fora do padrão
PRAZO_RESPOSTA_DIAS = 3  # prazo pedido para resposta na cobrança formal

# chave -> (nome, o que é). A ordem é a da escada, do mais leve ao mais firme.
TONS = {
    "lembrete_leve": ("Lembrete leve",
                      "Atraso dentro do que o cliente já faz. Só lembra, sem pressão."),
    "lembrete_prazo": ("Lembrete leve e acerto de prazo",
                       "Cliente que paga sempre com o mesmo atraso. Lembra e propõe acertar o prazo no contrato."),
    "primeiro_aviso": ("Primeiro aviso cordial",
                       "Primeiro atraso fora do padrão, sem cobrança anterior. Pergunta antes de supor."),
    "grande_primeira": ("Primeiro aviso a cliente grande",
                        "Como o primeiro aviso, para cliente de grande peso: conversa direta, assume que pode ser problema de processo."),
    "conversa_piora": ("Conversa sobre a mudança",
                       "Cliente que passou a pagar mais tarde. Abre uma conversa para entender, sem ameaça."),
    "comercial": ("Conversa comercial",
                  "Cliente que parou de comprar. Começa pelo relacionamento; a pendência financeira é só mencionada."),
    "objetiva": ("Cobrança objetiva",
                 "Já houve contato e o título segue aberto. Retoma o contato e pede uma data de pagamento."),
    "formal": ("Cobrança formal",
               "Mais de um contato sem pagamento. Pede data firme até um prazo curto."),
}


def nome_tom(chave):
    return TONS[chave][0]


def contatos_do_cliente(cobrancas, cod):
    return sorted((c for c in cobrancas if c["cliente"] == cod), key=lambda c: c["quando"])


def _dias(n):
    return "%d dia%s" % (n, "" if n == 1 else "s")


def _contatos_desde_o_vencimento(r, contatos):
    """Contatos feitos depois do vencimento do título mais antigo ainda em aberto."""
    venc = min(t["vencimento"] for t in r["vencidos"])
    corte = datetime.combine(venc, datetime.min.time())
    return [c for c in contatos if c["quando"] >= corte]


def escolher(ref, r, contatos):
    """Devolve (chave do tom, lista de frases que explicam a escolha).

    Ordem das regras: parou de comprar, piorou, fora do padrão (escada pelos contatos já feitos), atrasa sempre
    igual, e por fim atraso normal."""
    p, c, tags = r["pag"], r["compras"], r["tags"]
    vencidos = r["vencidos"]
    total, mais_antigo = r["vencido"], max(t["dias_atraso"] for t in vencidos)
    nome_curto = r["cliente"]["nome"]
    razoes = []

    if "parou" in tags:
        razoes.append("Parou de comprar: o último pedido foi há %s e o maior intervalo dele entre pedidos, em toda a história, "
                      "foi de %s. Com um cliente que sumiu, a primeira conversa é comercial e a cobrança fica para depois."
                      % (_dias(c["dias_sem_comprar"]), _dias(c["gap_max"])))
        razoes.append("Tem %s vencidos, o mais antigo há %s; por isso o texto só menciona a pendência, sem listar título."
                      % (reais(total), _dias(mais_antigo)))
        return "comercial", razoes

    if "piorou" in tags:
        razoes.append("Piorou: hoje paga com cerca de %s de atraso, contra %s no resto da história, e nunca deixou de pagar. "
                      "Quem está piorando recebe uma conversa, não uma ameaça." % (
                          _dias(arred(p["rec_med"])), _dias(arred(p["base_med"]))))
        if c.get("queda_confirmada"):
            razoes.append("Também comprou %d%% menos nos últimos 90 dias. O texto não toca nisso: é assunto do comercial, "
                          "e dito numa cobrança soaria como ameaça." % round(100 * c["queda"]))
        return "conversa_piora", razoes

    desvio = [t for t in vencidos if t.get("posicao", 0) >= POSICAO_DESVIO and not t.get("sazonal")]
    if desvio:
        pior = max(desvio, key=lambda t: t["dias_atraso"])
        if p["ok"] and pior["dias_atraso"] > p["maximo"]:
            razoes.append("O pior título está há %s em atraso, mais que todo atraso que ele já teve em %d pagamentos (máximo %s)."
                          % (_dias(pior["dias_atraso"]), r["n_pagos"], _dias(p["maximo"])))
        else:
            razoes.append("O pior título está há %s em atraso, mais lento que %d%% dos pagamentos dele."
                          % (_dias(pior["dias_atraso"]), round(100 * pior["posicao"])))
        anteriores = _contatos_desde_o_vencimento(r, contatos)
        grande = r["pct_fat"] >= GRANDE_PCT_FAT
        if not anteriores:
            if grande:
                razoes.append("Cliente grande (%.0f%% do faturamento dos últimos 12 meses) saindo do padrão pela primeira vez, "
                              "sem nenhuma cobrança depois do vencimento: conversa direta, supondo problema de processo "
                              "antes de supor qualquer outra coisa." % (100 * r["pct_fat"]))
                return "grande_primeira", razoes
            razoes.append("Nenhuma cobrança depois do vencimento: é o primeiro aviso, cordial, que pergunta antes de supor.")
            return "primeiro_aviso", razoes
        ult = anteriores[-1]
        desc = "%d contato%s depois do vencimento do título mais antigo (o último em %s, por %s)" % (
            len(anteriores), "" if len(anteriores) == 1 else "s", ult["quando"].strftime("%d/%m"), ult["canal"])
        if len(anteriores) == 1:
            razoes.append("Já houve %s e o título segue aberto: cobrança objetiva, retomando o contato e pedindo uma data." % desc)
            if grande:
                razoes.append("Cliente grande (%.0f%% do faturamento): o texto mantém o respeito, sem perder a objetividade."
                              % (100 * r["pct_fat"]))
            return "objetiva", razoes
        razoes.append("Já houve %s e o título segue aberto: cobrança formal, com data firme para resposta." % desc)
        return "formal", razoes

    if "atrasa_igual" in tags:
        razoes.append("Atrasa sempre igual: paga com cerca de %s de atraso (80%% dos pagamentos entre %s e %s) e, pelo histórico, "
                      "teria aparecido na lista de vencidos em %d dos %d fins de mês. O atraso de agora (%s) é normal para ele."
                      % (_dias(arred(p["mediana"])), _dias(arred(p["p10"])), _dias(arred(p["p90"])),
                         r["fins_mes_vencido"], r["fins_mes"], _dias(mais_antigo)))
        razoes.append("Por isso: lembrete leve e a sugestão de acertar o prazo no contrato (hoje %d dias, na prática %d), "
                      "em vez de cobrar todo mês." % (r["cliente"]["prazo_dias"], r["cliente"]["prazo_dias"] + arred(p["mediana"])))
        return "lembrete_prazo", razoes

    if p["ok"] and "posicao" in vencidos[0]:
        pior = max(vencidos, key=lambda t: t["posicao"])
        razoes.append("Atraso de %s, dentro do que ele já fez (só %d%% dos pagamentos dele foram mais rápidos) e sem mudança "
                      "de comportamento: lembrete leve." % (_dias(mais_antigo), round(100 * pior["posicao"])))
    else:
        razoes.append("Atraso de %s e sem histórico suficiente para dizer se é normal para ele: o tom mais cuidadoso, "
                      "um lembrete leve." % _dias(mais_antigo))
    return "lembrete_leve", razoes


def contexto(ref, r, chave, canal, titulos_escolhidos, contatos, assinatura):
    """Os fatos de que o redator precisa. Só dados; nenhuma frase para o cliente."""
    cli, p, c = r["cliente"], r["pag"], r["compras"]
    sel = [t for t in r["vencidos"] if t["numero"] in set(titulos_escolhidos)]
    sel.sort(key=lambda t: t["vencimento"])
    anteriores = _contatos_desde_o_vencimento(r, contatos) if r["vencidos"] else []
    habitual = arred(p["mediana"]) if p["ok"] else None
    primeiro_contato = (cli.get("contato") or "").split()
    return {
        "tom": chave, "canal": canal, "cliente": cli["nome"], "contato": primeiro_contato[0] if primeiro_contato else "",
        "desde": cli["desde"].year if cli.get("desde") else None,
        "remetente": assinatura.strip(),
        "titulos": [{"numero": t["numero"], "valor": t["valor"], "vencimento": t["vencimento"], "dias": t["dias_atraso"]}
                    for t in sel],
        "total": sum(t["valor"] for t in sel), "hoje": ref,
        "mais_antigo": max((t["dias_atraso"] for t in sel), default=0),
        "contato_anterior": ({"quando": anteriores[-1]["quando"], "canal": anteriores[-1]["canal"],
                              "n": len(anteriores)} if anteriores else None),
        "ultimo_pedido": r["ultima_compra"], "dias_sem_pedido": c["dias_sem_comprar"],
        "total_vencido_cliente": r["vencido"],
        "prazo_contrato": cli["prazo_dias"], "atraso_habitual": habitual,
        "prazo_real": (cli["prazo_dias"] + habitual) if habitual is not None else None,
        "meses_historico": max(1, (ref - r["primeira_compra"]).days // 30),
        "bom_historico": bool(p["ok"] and p["p90"] <= 10),
        "grande": r["pct_fat"] >= GRANDE_PCT_FAT,
        "resposta_ate": ref + timedelta(days=PRAZO_RESPOSTA_DIAS),
    }
