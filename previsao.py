"""Previsão de caixa das próximas quatro semanas, só da carteira que já existe (sem venda nova).

Não faz conta própria de comportamento de cliente: pega de risco.py o mesmo padrão de pagamento, a mesma
detecção de piora, a mesma sazonalidade e o mesmo índice de risco que as telas de risco usam.
Valor de título é exato, em centavos (int). O que é estimado sai arredondado para reais na hora de mostrar.
"""
import math
from datetime import timedelta

import risco
from frases import arred, reais, reais_est  # noqa: F401  (reais_est é a mesma das telas)
from risco import _q, atrasos_esperados

HORIZONTE_DIAS = 28
SEMANAS = 4
MIN_CONDICIONAL = 3   # pagamentos históricos necessários para dizer quando um título já atrasado deve entrar

# Chance de o título entrar. A base não registra nenhum título que tenha deixado de ser pago (todo título antigo foi
# pago), então essas duas taxas NÃO podem ser calibradas com os dados: são premissas, mostradas na tela.
K_RISCO = 0.30   # cliente com índice de risco 100 perde 30% de chance; índice 0 não perde nada
K_IDADE = 0.50   # título que já passou de todo atraso que o cliente teve (posição 1) perde 50%; título no prazo não perde


def est(c):
    """Centavos -> reais inteiros (arredonda meio para cima). Só para estimativas."""
    return (c + 50) // 100


def arredonda_partes(partes):
    """Arredonda cada parte para reais de modo que a soma das partes arredondadas seja o total arredondado."""
    out, acum, acum_r = [], 0, 0
    for c in partes:
        acum += c
        r = est(acum)
        out.append(r - acum_r)
        acum_r = r
    return out


def _dia(x):
    return int(math.floor(x + 0.5))


def _semana(ref, data):
    k = (data - ref).days
    return (k - 1) // 7 + 1 if 1 <= k <= HORIZONTE_DIAS else None


def _titulo(ref, r, t):
    cli = r["cliente"]
    d = (ref - t["vencimento"]).days
    posicao = next((v.get("posicao") for v in r["vencidos"] if v["numero"] == t["numero"]), None) if d > 0 else None  # sem histórico suficiente não há posição
    linha = {
        "numero": t["numero"], "cliente": cli["codigo"], "valor": t["valor"], "vencimento": t["vencimento"],
        "dias_atraso": d if d > 0 else 0, "emissao": t["emissao"],
        "semana_planilha": 1 if t["vencimento"] <= ref else _semana(ref, t["vencimento"]),
        "origem": None, "datas": None, "semanas": None, "prob_bp": None, "esperado": 0, "categoria": None,
    }
    atrasos, origem = atrasos_esperados(r, t["vencimento"].month)
    if atrasos is None:
        linha["categoria"] = "sem_historico"
        linha["motivo"] = origem
        return linha
    linha["origem"] = origem
    base = atrasos
    if d > 0:  # já está atrasado: só vale o que ele fez DEPOIS de ter passado desse atraso
        base = [x for x in atrasos if x >= d]
        if len(base) < MIN_CONDICIONAL:
            base = [x for x in r["pag"]["atrasos_ns"] if x >= d]
            if len(base) >= MIN_CONDICIONAL:
                linha["origem"] = "historico"
        if len(base) < MIN_CONDICIONAL:
            linha["categoria"] = "sem_precedente"
            linha["maximo_historico"] = r["pag"]["maximo"]
            linha["n_similares"] = len(base)
            linha["n_historico"] = r["n_pagos"]
            return linha
    atraso = {"esp": _dia(_q(base, .5)), "cons": _dia(_q(base, .9)), "otim": _dia(_q(base, .1))}
    minimo = ref + timedelta(days=1)
    linha["datas"] = {k: max(t["vencimento"] + timedelta(days=v), minimo) for k, v in atraso.items()}
    linha["atraso_dias"] = atraso
    linha["semanas"] = {k: _semana(ref, v) for k, v in linha["datas"].items()}
    p = (1 - K_RISCO * r["indice"] / 100) * (1 - K_IDADE * (posicao or 0))
    linha["prob_bp"] = int(round(p * 10000))
    linha["esperado"] = t["valor"] * linha["prob_bp"] // 10000
    linha["posicao"] = posicao
    linha["categoria"] = "projetado"
    return linha


def prever(ref, rs):
    linhas, por_cli = [], {}
    for r in rs:
        abertos = [t for t in r["titulos"] if not t["pagamento"]]
        ls = [_titulo(ref, r, t) for t in sorted(abertos, key=lambda t: t["vencimento"])]
        linhas += ls
        por_cli[r["cliente"]["codigo"]] = ls
    semanas = [(ref + timedelta(days=7 * i + 1), ref + timedelta(days=7 * i + 7)) for i in range(SEMANAS)]

    def por_semana(chave_semana, valor):
        out = [0] * SEMANAS
        for l in linhas:
            s = chave_semana(l)
            if s:
                out[s - 1] += valor(l)
        return out
    plan = por_semana(lambda l: l["semana_planilha"], lambda l: l["valor"])
    cen = {k: por_semana(lambda l, k=k: l["semanas"][k] if l["semanas"] else None, lambda l: l["esperado"])
           for k in ("esp", "cons", "otim")}

    def acum(xs):
        out, s = [], 0
        for x in xs:
            s += x
            out.append(s)
        return out
    cum = {"plan": acum(plan), **{k: acum(v) for k, v in cen.items()}}

    # Decomposição exata da diferença planilha − previsão, título a título
    dec = {"adiado": 0, "sem_data": 0, "probabilidade": 0, "antecipado": 0}
    for l in linhas:
        na_plan = l["semana_planilha"] is not None
        if l["categoria"] == "projetado":
            na_prev = l["semanas"]["esp"] is not None
            if na_plan and na_prev:
                dec["probabilidade"] += l["valor"] - l["esperado"]
            elif na_plan:
                dec["adiado"] += l["valor"]
            elif na_prev:
                dec["antecipado"] -= l["esperado"]
        elif na_plan:
            dec["sem_data"] += l["valor"]
    prev = {
        "semanas": semanas, "linhas": linhas, "por_cliente": por_cli,
        "planilha": plan, "cen": cen, "cum": cum, "dec": dec,
        "total_planilha": cum["plan"][-1], "total_esp": cum["esp"][-1],
        "total_cons": cum["cons"][-1], "total_otim": cum["otim"][-1],
    }
    prev["diferenca"] = prev["total_planilha"] - prev["total_esp"]
    prev["clientes"] = _por_cliente(ref, rs, prev)
    prev["planilha_sem_vencidos"] = sum(l["valor"] for l in linhas if l["dias_atraso"] == 0 and l["semana_planilha"])
    prev["vencidos_na_planilha"] = sum(l["valor"] for l in linhas if l["dias_atraso"] > 0)
    prev["fora_janela"] = sum(l["valor"] for l in linhas if l["semana_planilha"] is None)
    return prev


def _por_cliente(ref, rs, prev):
    fim = ref + timedelta(days=HORIZONTE_DIAS)
    out = []
    for r in rs:
        ls = prev["por_cliente"][r["cliente"]["codigo"]]
        plan = sum(l["valor"] for l in ls if l["semana_planilha"])
        esp = sum(l["esperado"] for l in ls if l["categoria"] == "projetado" and l["semanas"]["esp"])
        if not ls:
            continue
        adiados = [l for l in ls if l["categoria"] == "projetado" and l["semana_planilha"] and not l["semanas"]["esp"]]
        sem_data = [l for l in ls if l["categoria"] != "projetado" and l["semana_planilha"]]
        antec = [l for l in ls if l["categoria"] == "projetado" and not l["semana_planilha"] and l["semanas"]["esp"]]
        c = {"cliente": r["cliente"], "r": r, "planilha": plan, "previsao": esp, "diferenca": plan - esp,
             "n": len(ls), "adiados": adiados, "sem_data": sem_data, "antecipados": antec,
             "projetados": [l for l in ls if l["categoria"] == "projetado"]}
        c["frase"] = _frase_cliente(ref, fim, r, c)
        out.append(c)
    out.sort(key=lambda c: -abs(c["diferenca"]))
    return out


def _dias(n):
    return "%d dia%s" % (n, "" if n == 1 else "s")


def _frase_cliente(ref, fim, r, c):
    nome, p = r["cliente"]["nome"], r["pag"]
    data = lambda d: d.strftime("%d/%m")
    if c["planilha"] == 0 and c["previsao"] == 0 and not c["sem_data"]:
        return "%s não tem nada vencendo nem esperado nas quatro semanas." % nome
    # como ele paga (o mesmo número das telas de risco)
    if p["ok"] and p.get("piora") and any(l["origem"] == "recente" for l in c["projetados"]):
        habito = ("Piorou: hoje paga com cerca de %s de atraso (o típico dos últimos pagamentos), não os %s do resto da história"
                  % (_dias(arred(p["rec_med"])), _dias(arred(p["base_med"]))))
    elif p["ok"]:
        habito = "Costuma pagar com cerca de %s de atraso" % _dias(arred(p["mediana"]))
    else:
        habito = "Sem histórico suficiente para datar os pagamentos"
    partes = []
    if c["adiados"]:
        v = sum(l["valor"] for l in c["adiados"])
        ult = max(l["datas"]["esp"] for l in c["adiados"])
        partes.append("%d título%s (%s) que a planilha põe nas quatro semanas só deve%s entrar depois de %s"
                      % (len(c["adiados"]), "" if len(c["adiados"]) == 1 else "s", reais(v),
                         "" if len(c["adiados"]) == 1 else "m", data(fim)))
    if c["sem_data"]:
        v = sum(l["valor"] for l in c["sem_data"])
        sp = [l for l in c["sem_data"] if l["categoria"] == "sem_precedente"]
        fora = [l for l in sp if l["dias_atraso"] > l["maximo_historico"]]
        borda = [l for l in sp if l["dias_atraso"] <= l["maximo_historico"]]
        if fora:
            pior = max(l["dias_atraso"] for l in fora)
            partes.append("%s (%s) %s há %s, mais que todo atraso que ele já teve (máximo %s), então não projeto data"
                          % ("1 título" if len(fora) == 1 else "%d títulos" % len(fora), reais(sum(l["valor"] for l in fora)),
                             "vencido" if len(fora) == 1 else "vencidos, o pior", _dias(pior), _dias(fora[0]["maximo_historico"])))
        if borda:
            pior = max(l["dias_atraso"] for l in borda)
            partes.append("%s (%s) %s há %s, na ponta do que ele já fez (só %d dos %d pagamentos dele levaram tanto tempo), "
                          "então não projeto data"
                          % ("1 título" if len(borda) == 1 else "%d títulos" % len(borda), reais(sum(l["valor"] for l in borda)),
                             "vencido" if len(borda) == 1 else "vencidos, o pior", _dias(pior),
                             min(l["n_similares"] for l in borda), borda[0]["n_historico"]))
        sh = [l for l in c["sem_data"] if l["categoria"] == "sem_historico"]
        if sh:
            partes.append("%s sem histórico para datar" % reais(sum(l["valor"] for l in sh)))
    if c["antecipados"]:
        v = sum(l["esperado"] for l in c["antecipados"])
        partes.append("%d título%s que vence%s depois da janela deve%s ser pago%s dentro dela"
                      % (len(c["antecipados"]), "" if len(c["antecipados"]) == 1 else "s",
                         "" if len(c["antecipados"]) == 1 else "m", "" if len(c["antecipados"]) == 1 else "m",
                         "" if len(c["antecipados"]) == 1 else "s"))
    prob = [l for l in c["projetados"] if l["semana_planilha"] and l["semanas"]["esp"]]
    if prob and not partes:
        pm = sum(l["prob_bp"] for l in prob) / len(prob) / 100
        partes.append("os títulos entram no prazo esperado, com chance média de %d%% (pelo risco dele)" % round(pm))
    return "%s. %s." % (habito, "; ".join(p_[0].upper() + p_[1:] if i == 0 else p_ for i, p_ in enumerate(partes)) if partes else "Sem ajuste")


# ---------------------------------------------------------------- conferência

def conferencias(ref, rs, prev, resumo):
    """Lista de (mensagem, passou?) para conferir.py."""
    from motor import carregar
    import servico
    _, _, titulos, _ = carregar(servico.caminho_base())
    lim = ref + timedelta(days=HORIZONTE_DIAS)
    indep = sum(t["valor"] for t in titulos if not t["pagamento"] and t["vencimento"] <= lim)
    ab = [l for l in prev["linhas"]]
    res = []
    add = lambda m, c: res.append((m, bool(c)))
    add("planilha: soma dos vencimentos bate com conta independente feita direto nos títulos", prev["total_planilha"] == indep)
    add("planilha + títulos que vencem depois da janela = saldo em aberto da tela Hoje",
        prev["total_planilha"] + prev["fora_janela"] == resumo["aberto"])
    add("todo título em aberto foi tratado uma vez (%d)" % len(ab), len(ab) == resumo["n_abertos"]
        and len({l["numero"] for l in ab}) == len(ab))
    add("decomposição da diferença fecha no centavo", sum(prev["dec"].values()) == prev["diferenca"])
    add("soma por cliente = total (planilha e previsão)",
        sum(c["planilha"] for c in prev["clientes"]) == prev["total_planilha"]
        and sum(c["previsao"] for c in prev["clientes"]) == prev["total_esp"])
    add("soma das semanas = acumulado final, nos quatro cenários",
        sum(prev["planilha"]) == prev["total_planilha"]
        and all(sum(prev["cen"][k]) == prev["cum"][k][-1] for k in ("esp", "cons", "otim")))
    add("acumulado: conservador ≤ esperado ≤ otimista em TODAS as semanas",
        all(prev["cum"]["cons"][i] <= prev["cum"]["esp"][i] <= prev["cum"]["otim"][i] for i in range(SEMANAS)))
    add("acumulado nunca diminui", all(all(a <= b for a, b in zip(v, v[1:])) for v in prev["cum"].values()))
    add("estimativas arredondadas somam o total arredondado (semanas)",
        sum(arredonda_partes(prev["cen"]["esp"])) == est(prev["total_esp"]))
    add("estimativas arredondadas somam o total arredondado (decomposição)",
        sum(arredonda_partes(list(prev["dec"].values()))) == est(prev["diferenca"]))
    add("valores em centavos são inteiros",
        all(isinstance(l["valor"], int) and isinstance(l["esperado"], int) for l in ab))
    add("nenhuma chance de entrada fora de 0–100%", all(0 <= (l["prob_bp"] or 0) <= 10000 for l in ab))
    # mesma conta das telas de risco
    mesma = True
    for c in prev["clientes"]:
        r, p = c["r"], c["r"]["pag"]
        for l in c["projetados"]:
            if l["origem"] == "historico" and l["dias_atraso"] == 0:
                mesma &= l["atraso_dias"]["esp"] == _dia(_q(p["atrasos_ns"], .5))
                mesma &= abs(_q(p["atrasos_ns"], .5) - p["mediana"]) < 1e-9  # mediana que a tela de risco mostra
            if l["origem"] == "recente":
                mesma &= bool(p.get("piora"))  # só quem a tela de risco marca como piorou usa comportamento recente
    add("previsão usa o mesmo padrão e a mesma detecção de piora da tela de risco", mesma)
    pior = [c for c in prev["clientes"] if c["r"]["pag"].get("piora")]
    add("quem a tela de risco diz que piorou é projetado com o atraso recente dela (atraso típico %s)"
        % ", ".join("%s: %d dias" % (c["cliente"]["nome"], round(c["r"]["pag"]["rec_med"])) for c in pior),
        all(_dia(_q(c["r"]["pag"]["atrasos_rec_pagos"], .5)) == _dia(c["r"]["pag"]["rec_med"]) for c in pior))
    return res
