"""Risco por cliente: comportamento de pagamento, compras e exposição, tudo calculado
sobre os 24 meses de títulos. Dinheiro em centavos (int). Quando não há histórico
suficiente para uma conta, ela devolve None com o motivo, em vez de estimar."""
import statistics
from collections import defaultdict
from datetime import timedelta

from frases import arred, pct1, reais, reais_est
from motor import carregar

# --- Parâmetros do método ---
JANELA_RECENTE_DIAS = 90     # "meses recentes" para pagamento e compras
MIN_RECENTES = 5             # títulos pagos na janela recente para acusar mudança
MIN_REGIME_RECENTE = 3       # pagamentos recentes mínimos para adotar o comportamento recente como regime
MIN_BASE = 20                # títulos pagos no padrão histórico
PIORA_MIN_DIAS = 7           # piora só vale se passar disto em dias...
PIORA_MIN_SIGMAS = 2.0       # ...e disto em unidades da variação do próprio cliente
SAZ_MIN_DIAS = 7             # mês sazonal: excesso mínimo em dias...
SAZ_MIN_SIGMAS = 1.5         # ...e em variações do cliente, em anos diferentes
QUEDA_COMPRA_MIN = 0.25      # queda mínima de compras (fração) ...
QUEDA_COMPRA_SIGMAS = 1.5    # ...e em desvios das compras do próprio cliente
MIN_JANELAS_COMPRA = 4       # janelas de 90 dias de histórico antes da recente
MIN_PEDIDOS = 10             # pedidos para medir o ritmo de compra
ATRASO_CHEIO = 30            # mediana de atraso que vale 100% no fator "atraso habitual"
AMPLITUDE_CHEIA = 40         # P10–P90 que vale 100% no fator "imprevisibilidade"
PADRAO_ESTAVEL_MAX_AMPLITUDE = 12  # "atrasa sempre igual": P10–P90 máximo, em dias
PADRAO_ESTAVEL_MIN_MEDIANA = 5     # e atraso típico mínimo
PADRAO_ESTAVEL_MIN_ATRASADOS = 0.8  # e fração mínima de títulos pagos com atraso
PADRAO_ESTAVEL_MIN_NA_LISTA = 0.5   # e fração mínima dos fins de mês em que estaria na lista de vencidos

# (chave, nome, peso). Os pesos somam 100.
FATORES = [
    ("habitual", "Atraso habitual", 10),
    ("variacao", "Imprevisibilidade", 15),
    ("piora", "Piora recente", 25),
    ("compras", "Compras", 20),
    ("limite", "Uso do limite", 10),
    ("vencido", "Vencido fora do padrão", 20),
]

MESES_ABREV = "jan fev mar abr mai jun jul ago set out nov dez".split()
MESES_NOME = ("janeiro fevereiro março abril maio junho julho agosto setembro outubro "
              "novembro dezembro").split()


def _q(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def _sigma(xs):
    """Variação típica robusta (IQR/1,349), com piso de 2 dias."""
    return max((_q(xs, .75) - _q(xs, .25)) / 1.349, 2.0)


def _sigma_mad(xs):
    """Variação típica pela mediana dos desvios (MAD), menos inflada por meses sazonais."""
    m = statistics.median(xs)
    return max(1.4826 * statistics.median(abs(x - m) for x in xs), 2.0)


def _dias(n):
    n = arred(n)
    return "%d dia%s" % (n, "" if abs(n) == 1 else "s")


def _lista_meses(ms):
    nomes = [MESES_NOME[m - 1] for m in sorted(ms)]
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def _sazonais(pagos, mediana, sigma):
    """Meses do calendário em que o atraso dispara em anos diferentes (>= 2 anos)."""
    por = defaultdict(list)
    for t in pagos:
        por[(t["vencimento"].year, t["vencimento"].month)].append(t["atraso"])
    anos = defaultdict(list)
    for (a, m), xs in por.items():
        if statistics.median(xs) - mediana >= max(SAZ_MIN_DIAS, SAZ_MIN_SIGMAS * sigma):
            anos[m].append(a)
    return {m for m, a in anos.items() if len(set(a)) >= 2}  # repetiu em pelo menos 2 anos


def analisar_cliente(cli, titulos, ref):
    cod = cli["codigo"]
    meus = [t for t in titulos if t["cliente"] == cod]
    pagos = [dict(t, atraso=(t["pagamento"] - t["vencimento"]).days) for t in meus if t["pagamento"]]
    abertos = [t for t in meus if not t["pagamento"]]
    vencidos = [dict(t, dias_atraso=(ref - t["vencimento"]).days) for t in abertos if t["vencimento"] < ref]
    saldo = sum(t["valor"] for t in abertos)
    r = {"cliente": cli, "saldo": saldo, "n_abertos": len(abertos), "vencidos": vencidos,
         "vencido": sum(t["valor"] for t in vencidos), "n_pagos": len(pagos), "titulos": meus}
    r["primeira_compra"] = min(t["emissao"] for t in meus)
    r["ultima_compra"] = max(t["emissao"] for t in meus)
    r["ocupacao"] = saldo / cli["limite"]

    # ---------- padrão de pagamento ----------
    p = {"ok": len(pagos) >= MIN_BASE}
    r["pag"] = p
    if p["ok"]:
        todos = [t["atraso"] for t in pagos]
        med_all, sig_all = statistics.median(todos), _sigma_mad(todos)
        saz = _sazonais(pagos, med_all, sig_all)
        nsaz = [t for t in pagos if t["vencimento"].month not in saz]
        corte = ref - timedelta(days=JANELA_RECENTE_DIAS)
        base = [t["atraso"] for t in nsaz if t["vencimento"] < corte]
        # Título vencido e ainda em aberto entra com o atraso de hoje (piso do atraso real):
        # sem isso, cliente lento pareceria melhor só porque o pior ainda não foi pago.
        rec = ([t["atraso"] for t in nsaz if t["vencimento"] >= corte]
               + [t["dias_atraso"] for t in vencidos
                  if t["vencimento"] >= corte and t["vencimento"].month not in saz])
        todos_ns = [t["atraso"] for t in nsaz]
        p.update({
            "sazonais": sorted(saz), "mediana": statistics.median(todos_ns), "n_ns": len(todos_ns),
            "p10": _q(todos_ns, .10), "p25": _q(todos_ns, .25), "p75": _q(todos_ns, .75), "p90": _q(todos_ns, .90),
            "maximo": max(todos), "minimo": min(todos), "sigma": _sigma(todos_ns),
            "pct_atrasados": sum(1 for x in todos if x > 0) / len(todos),
            # séries completas, para quem precisar da distribuição (ex.: previsão de caixa)
            "atrasos_ns": sorted(todos_ns),
            "atrasos_rec_pagos": sorted(t["atraso"] for t in nsaz if t["vencimento"] >= corte),
            "atrasos_saz": {m: sorted(t["atraso"] for t in pagos if t["vencimento"].month == m) for m in saz},
        })
        if len(base) >= MIN_BASE:
            p.update({"base_n": len(base), "base_med": statistics.median(base), "base_sigma": _sigma(base),
                      "base_p10": _q(base, .10), "base_p90": _q(base, .90)})
            if len(rec) >= MIN_RECENTES:
                d = statistics.median(rec) - p["base_med"]
                piora = d >= PIORA_MIN_DIAS and d / p["base_sigma"] >= PIORA_MIN_SIGMAS
                n_ab = sum(1 for t in vencidos if t["vencimento"] >= corte and t["vencimento"].month not in saz)
                rec_n, rec_med = len(rec), statistics.median(rec)
                pagos_rec = p["atrasos_rec_pagos"]
                if piora and len(pagos_rec) >= MIN_REGIME_RECENTE:
                    # A DETECÇÃO acima é conservadora (conta os abertos pelo atraso de hoje). Mas o atraso que se
                    # diz que o cliente pratica hoje, e que a previsão de caixa usa, vem só dos títulos já pagos:
                    # atraso de título aberto ainda não é atraso, é piso dele.
                    rec_n, rec_med = len(pagos_rec), statistics.median(pagos_rec)
                p.update({"rec_n": rec_n, "rec_abertos": n_ab, "rec_med": rec_med, "delta": rec_med - p["base_med"],
                          "delta_sig": (rec_med - p["base_med"]) / p["base_sigma"], "piora": piora})
            else:
                p["piora_motivo"] = ("só %d título%s venceu nos últimos %d dias; preciso de %d para comparar"
                                     % (len(rec), "" if len(rec) == 1 else "s", JANELA_RECENTE_DIAS, MIN_RECENTES))
        else:
            p["piora_motivo"] = "só %d títulos pagos no padrão histórico; preciso de %d" % (len(base), MIN_BASE)
        # vencidos hoje contra o padrão certo (sazonal ou não)
        for t in vencidos:
            ref_set = [x["atraso"] for x in pagos
                       if (x["vencimento"].month in saz) == (t["vencimento"].month in saz)]
            if len(ref_set) < 8:
                ref_set = todos
            n = len(ref_set)
            t["posicao"] = (sum(1 for x in ref_set if x < t["dias_atraso"])
                            + sum(1 for x in ref_set if x == t["dias_atraso"]) / 2) / n
            t["sazonal"] = t["vencimento"].month in saz
    else:
        p["motivo"] = "só %d títulos pagos; preciso de %d para descrever o padrão de pagamento" % (len(pagos), MIN_BASE)

    # em quantos fins de mês ele teria aparecido numa lista de vencidos
    fins, d = [], r["primeira_compra"].replace(day=1)
    while True:
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)   # 1º do mês seguinte
        fim = d - timedelta(days=1)
        if fim >= ref:
            break
        fins.append(fim)
    primeiro_venc = min(t["vencimento"] for t in meus)
    fins = [f for f in fins if f >= primeiro_venc]
    r["fins_mes"] = len(fins)
    r["fins_mes_vencido"] = sum(
        1 for f in fins if any(t["vencimento"] <= f and (t["pagamento"] is None or t["pagamento"] > f) and t["emissao"] <= f
                               for t in meus))

    # série mensal (mês de vencimento) para o gráfico
    meses = defaultdict(list)
    for t in pagos:
        meses[(t["vencimento"].year, t["vencimento"].month)].append(t["atraso"])
    abertos_mes = defaultdict(int)
    for t in vencidos:
        k = (t["vencimento"].year, t["vencimento"].month)
        abertos_mes[k] = max(abertos_mes[k], t["dias_atraso"])
    r["serie"] = meses
    r["serie_aberta"] = abertos_mes

    # trecho fora do padrão (só quando a piora é confirmada)
    r["trecho"] = None
    if p.get("piora"):
        saz = set(p["sazonais"])
        ks = sorted(meses)
        trecho = []
        for k in reversed(ks):
            if k[1] in saz:
                continue
            if statistics.median(meses[k]) > p["p90"]:  # o mesmo "padrão" que a faixa do gráfico e o texto mostram
                trecho.append(k)
            else:
                break
        if len(trecho) >= 2:
            r["trecho"] = (min(trecho), max(trecho))

    # ---------- compras ----------
    c = {}
    r["compras"] = c
    datas = sorted({t["emissao"] for t in meus})
    c["dias_sem_comprar"] = (ref - datas[-1]).days
    if len(datas) >= MIN_PEDIDOS:
        gaps = [(b - a).days for a, b in zip(datas, datas[1:])]
        c["gap_med"], c["gap_p90"], c["gap_max"] = statistics.median(gaps), _q(gaps, .9), max(gaps)
    else:
        c["gap_motivo"] = "só %d dias de pedido; preciso de %d para medir o ritmo" % (len(datas), MIN_PEDIDOS)

    def janela(i):  # i=0 recente; i>=1 janelas anteriores de 90 dias
        fim, ini = ref - timedelta(days=90 * i), ref - timedelta(days=90 * (i + 1))
        return sum(t["valor"] for t in meus if ini < t["emissao"] <= fim)
    n_jan = (ref - r["primeira_compra"]).days // JANELA_RECENTE_DIAS - 1
    if n_jan >= MIN_JANELAS_COMPRA:
        base_v = [janela(i) for i in range(1, n_jan + 1)]
        rec_v = janela(0)
        media, dp = statistics.mean(base_v), statistics.pstdev(base_v)
        queda = 1 - rec_v / media
        c.update({"rec": rec_v, "media": media, "queda": queda, "n_jan": n_jan,
                  "queda_confirmada": queda >= QUEDA_COMPRA_MIN and rec_v < media - QUEDA_COMPRA_SIGMAS * dp})
    else:
        c["motivo"] = ("só %d meses de histórico de compras; preciso de pelo menos %d para comparar"
                       % ((ref - r["primeira_compra"]).days // 30, (MIN_JANELAS_COMPRA + 1) * 3))
    c["parou"] = "gap_max" in c and c["dias_sem_comprar"] > c["gap_max"]
    c["atrasado"] = "gap_p90" in c and not c["parou"] and c["dias_sem_comprar"] > c["gap_p90"]

    compras_mes = defaultdict(int)
    for t in meus:
        compras_mes[(t["emissao"].year, t["emissao"].month)] += t["valor"]
    r["compras_mes"] = compras_mes
    return r


def _ind(ok, **kw):
    return dict(ok=ok, **kw)


def fatores(r):
    """Cada fator: pontos brutos 0..1 (ou None se faltar dado) e a frase que o justifica."""
    p, c, nome = r["pag"], r["compras"], r["cliente"]["nome"]
    out = {}

    # 1 atraso habitual
    if p["ok"]:
        s = min(1.0, p["mediana"] / ATRASO_CHEIO)
        out["habitual"] = (s, "Costuma pagar %s depois do vencimento (o atraso típico de %d pagamentos%s)."
                           % (_dias(p["mediana"]), p["n_ns"],
                              ", sem contar os meses sazonais" if p["sazonais"] else ""))
    else:
        out["habitual"] = (None, "Sem dados suficientes: " + p["motivo"] + ".")

    # 2 imprevisibilidade
    if p["ok"]:
        amp = p["p90"] - p["p10"]
        s = min(1.0, amp / AMPLITUDE_CHEIA)
        if amp <= 8:
            txt = "Previsível: 80%% dos pagamentos caem entre %s e %s depois do vencimento."
        elif amp <= 20:
            txt = "Varia um pouco: 80%% dos pagamentos caem entre %s e %s depois do vencimento."
        else:
            txt = "Imprevisível: 80%% dos pagamentos caem entre %s e %s depois do vencimento, uma faixa de %s."
        args = (_dias(p["p10"]), _dias(p["p90"])) + ((_dias(amp),) if amp > 20 else ())
        out["variacao"] = (s, txt % args)
    else:
        out["variacao"] = (None, "Sem dados suficientes: " + p["motivo"] + ".")

    # 3 piora recente
    if not p["ok"]:
        out["piora"] = (None, "Sem dados suficientes: " + p["motivo"] + ".")
    elif "piora_motivo" in p:
        out["piora"] = (None, "Não dá para dizer se piorou: " + p["piora_motivo"] + ".")
    else:
        d, ds = p["delta"], p["delta_sig"]
        saz = (" Meses sazonais (%s) ficaram de fora da comparação." % _lista_meses(p["sazonais"])) if p["sazonais"] else ""
        if p["piora"]:
            s = 0.5 + 0.5 * min(1.0, (ds - PIORA_MIN_SIGMAS) / 4)
            out["piora"] = (s, "Piorou: nos últimos %d dias paga com %s de atraso (o típico de %d títulos já pagos%s), contra %s no resto da "
                               "história. São %s a mais, %s vezes a variação normal dele.%s"
                            % (JANELA_RECENTE_DIAS, _dias(p["rec_med"]), p["rec_n"],
                               ("; mais %d em aberto, já atrasados" % p["rec_abertos"]) if p["rec_abertos"] else "",
                               _dias(p["base_med"]),
                               _dias(d), pct1(ds), saz))
        else:
            s = 0.1 * min(1.0, max(ds, 0) / PIORA_MIN_SIGMAS)
            if d > 0:
                txt = ("Sem piora confirmada: nos últimos %d dias o atraso típico é %s, contra %s antes. A diferença de %s cabe na "
                       "variação normal dele (%s vezes), então não conta como deterioração.%s"
                       % (JANELA_RECENTE_DIAS, _dias(p["rec_med"]), _dias(p["base_med"]), _dias(d), pct1(ds), saz))
            else:
                txt = ("Sem piora: nos últimos %d dias o atraso típico é %s, contra %s antes.%s"
                       % (JANELA_RECENTE_DIAS, _dias(p["rec_med"]), _dias(p["base_med"]), saz))
            out["piora"] = (s, txt)

    # 4 compras
    dsc = c["dias_sem_comprar"]
    if c["parou"]:
        out["compras"] = (1.0, "Parou de comprar: o último pedido foi há %s e o maior intervalo entre pedidos dele, em toda a "
                               "história, foi de %s." % (_dias(dsc), _dias(c["gap_max"])))
    elif "queda" in c:
        q = c["queda"]
        ritmo = (" Último pedido há %s%s." % (_dias(dsc), ", acima do que é normal para ele" if c["atrasado"] else "")
                 if "gap_p90" in c else "")
        if c["queda_confirmada"]:
            s = 0.5 + 0.5 * min(1.0, (q - QUEDA_COMPRA_MIN) / 0.5)
            out["compras"] = (s, "Compra menos: nos últimos %d dias comprou %s, %d%% abaixo da média de %s por período de %d dias "
                                 "dos %d períodos anteriores, e fora da oscilação normal dele.%s"
                              % (JANELA_RECENTE_DIAS, reais(c["rec"]), round(100 * q), reais_est(round(c["media"])),
                                 JANELA_RECENTE_DIAS, c["n_jan"], ritmo))
        else:
            s = 0.15 * min(1.0, max(q, 0) / QUEDA_COMPRA_MIN)
            if q > 0:
                txt = ("Compras dentro da oscilação normal: nos últimos %d dias comprou %s, %d%% abaixo da média de %s, "
                       "diferença que ele já teve antes.%s" % (JANELA_RECENTE_DIAS, reais(c["rec"]), round(100 * q),
                                                              reais_est(round(c["media"])), ritmo))
            else:
                txt = ("Compras estáveis ou crescendo: nos últimos %d dias comprou %s, %d%% acima da média de %s.%s"
                       % (JANELA_RECENTE_DIAS, reais(c["rec"]), round(-100 * q), reais_est(round(c["media"])), ritmo))
            out["compras"] = (s, txt)
    else:
        out["compras"] = (None, "Sem dados suficientes para comparar compras: " + c["motivo"] + ".")

    # 5 limite
    lim = r["cliente"]["limite"]
    out["limite"] = (min(1.0, r["ocupacao"]),
                     "Tem %s em aberto, %d%% do limite de %s." % (reais(r["saldo"]), round(100 * r["ocupacao"]), reais(lim)))

    # 6 vencido fora do padrão
    if not r["vencidos"]:
        out["vencido"] = (0.0, "Não tem nenhum título vencido hoje.")
    elif not p["ok"]:
        out["vencido"] = (None, "Sem dados suficientes: " + p["motivo"] + ".")
    else:
        pior = max(r["vencidos"], key=lambda t: t["posicao"])
        pct = round(100 * pior["posicao"])
        if pior["sazonal"]:
            cont = " Esse vencimento cai em mês sazonal dele, comparado só com os outros meses sazonais."
        else:
            cont = ""
        if pior["posicao"] >= 0.95 and pior["dias_atraso"] > p["maximo"]:
            frase_v = ("Tem %s vencidos; o pior título está há %s em atraso, mais que o maior atraso que ele já teve (%s).%s"
                       % (reais(r["vencido"]), _dias(pior["dias_atraso"]), _dias(p["maximo"]), cont))
        elif pior["posicao"] <= 0.25:
            frase_v = ("Tem %s vencidos, mas o pior título está há %s em atraso, dentro do que ele costuma atrasar: só %d%% dos "
                       "pagamentos dele foram mais rápidos.%s" % (reais(r["vencido"]), _dias(pior["dias_atraso"]), pct, cont))
        else:
            frase_v = ("Tem %s vencidos; o pior título está há %s em atraso, mais do que %d%% dos pagamentos dele.%s"
                       % (reais(r["vencido"]), _dias(pior["dias_atraso"]), pct, cont))
        out["vencido"] = (pior["posicao"], frase_v)
    return out


def indice(r):
    fs = fatores(r)
    linhas, soma_pesos, soma_pontos = [], 0, 0.0
    for chave, nome, peso in FATORES:
        s, frase_f = fs[chave]
        pontos = None if s is None else s * peso
        linhas.append({"chave": chave, "nome": nome, "peso": peso, "score": s, "pontos": pontos, "frase": frase_f})
        if s is not None:
            soma_pesos += peso
            soma_pontos += pontos
    r["fatores"] = linhas
    r["peso_usado"] = soma_pesos
    r["indice"] = round(100 * soma_pontos / soma_pesos)
    r["parcial"] = soma_pesos < 100
    r["valor_em_risco"] = r["saldo"] * r["indice"] // 100


def _peso_faturamento(resultados, ref):
    ini = ref - timedelta(days=365)
    tot = 0
    for r in resultados:
        r["fat12"] = sum(t["valor"] for t in r["titulos"] if ini < t["emissao"] <= ref)
        tot += r["fat12"]
    for r in resultados:
        r["pct_fat"] = r["fat12"] / tot
    return tot


def classificar(r):
    """Etiquetas comportamentais, cada uma com o fato que a justifica."""
    p, c = r["pag"], r["compras"]
    tags = []
    if p["ok"] and p["sazonais"] and not p.get("piora"):
        tags.append("sazonal")
    estavel = (p["ok"] and p["pct_atrasados"] >= PADRAO_ESTAVEL_MIN_ATRASADOS
               and p["mediana"] >= PADRAO_ESTAVEL_MIN_MEDIANA
               and p["p90"] - p["p10"] <= PADRAO_ESTAVEL_MAX_AMPLITUDE and not p.get("piora")
               and not p["sazonais"] and r["fins_mes"] >= 12 and r["fins_mes_vencido"] / r["fins_mes"] >= PADRAO_ESTAVEL_MIN_NA_LISTA
               and not c["parou"] and not c.get("queda_confirmada"))
    if estavel:
        tags.append("atrasa_igual")
    silencioso = (not r["vencidos"] and p["ok"] and "delta" in p and p["delta"] > 0
                  and not c["parou"] and c.get("queda", 0) > 0
                  and (p.get("piora") or c.get("queda_confirmada")))
    if silencioso:
        tags.append("silencioso")
    if p.get("piora"):
        tags.append("piorou")
    if c["parou"]:
        tags.append("parou")
    elif c.get("queda_confirmada"):
        tags.append("compra_menos")
    faltou = [m for m in (p.get("motivo"), p.get("piora_motivo"), c.get("motivo")) if m]
    r["faltou"] = faltou
    if faltou:
        tags.append("falta_dado")
    r["tags"] = tags
    return tags


def totais(rs):
    """Totais da carteira pela leitura de risco. A tela Risco e o relatório leem daqui."""
    saldo = sum(r["saldo"] for r in rs)
    vr = sum(r["valor_em_risco"] for r in rs)
    return {"saldo": saldo, "valor_em_risco": vr, "pct_em_risco": (vr / saldo) if saldo else 0.0}


def atrasos_esperados(r, mes_vencimento):
    """Distribuição de atraso (dias) que vale para um título deste cliente que vence no mês dado.

    É a MESMA leitura das telas de risco: se a piora foi confirmada, vale o comportamento recente
    (nunca a média de dois anos); se o mês é sazonal para o cliente, vale o atraso daquele mês do calendário;
    senão, o padrão histórico sem os meses sazonais. Devolve (lista ordenada, origem) ou (None, motivo)."""
    p = r["pag"]
    if not p["ok"]:
        return None, p["motivo"]
    if mes_vencimento in p["atrasos_saz"] and len(p["atrasos_saz"][mes_vencimento]) >= MIN_REGIME_RECENTE:
        return p["atrasos_saz"][mes_vencimento], "sazonal"
    if p.get("piora") and len(p["atrasos_rec_pagos"]) >= MIN_REGIME_RECENTE:
        return p["atrasos_rec_pagos"], "recente"
    return p["atrasos_ns"], "historico"


def analisar(caminho):
    ref, clientes, titulos, cobrancas = carregar(caminho)
    com_titulo = {t["cliente"] for t in titulos}  # cliente sem nenhum título não tem o que analisar; validacao.avisos o menciona
    resultados = [analisar_cliente(c, titulos, ref) for c in clientes.values() if c["codigo"] in com_titulo]
    _peso_faturamento(resultados, ref)
    for r in resultados:
        indice(r)
        classificar(r)
        r["alerta"] = alerta(r, ref)
    resultados.sort(key=lambda r: (-r["valor_em_risco"], -r["indice"]))
    lista_data = sorted((t for r in resultados for t in r["vencidos"]), key=lambda t: t["vencimento"])
    for r in resultados:
        r["pos_lista_data"] = [i + 1 for i, t in enumerate(lista_data) if t["cliente"] == r["cliente"]["codigo"]]
    assert sum(r["saldo"] for r in resultados) == sum(t["valor"] for t in titulos if not t["pagamento"])
    return ref, resultados, len(lista_data)


def _fora_do_padrao(r):
    p = r["pag"]
    if not p["ok"]:
        return []
    return [t for t in r["vencidos"] if t["posicao"] >= 0.95 and t["dias_atraso"] > p["maximo"] and not t["sazonal"]]


fora_do_padrao = _fora_do_padrao  # nome público: quem precisa dos títulos que passaram de todo atraso do cliente


def alerta(r, ref):
    """Alerta por extenso: o que está acontecendo e o que fazer."""
    texto = _alerta_base(r)
    fora = _fora_do_padrao(r)
    if fora and not ({"parou", "piorou"} & set(r["tags"])):
        t = max(fora, key=lambda t: t["dias_atraso"])
        texto += (" Atenção: tem %s vencido há %s (%s), mais que o maior atraso que ele já teve (%s). "
                  "Ligar agora, sem esperar a próxima rodada de cobrança." % (
                      reais(sum(x["valor"] for x in fora)), _dias(t["dias_atraso"]), t["numero"], _dias(r["pag"]["maximo"])))
    return texto


def _alerta_base(r):
    p, c, nome, cli = r["pag"], r["compras"], r["cliente"]["nome"], r["cliente"]
    tags = r["tags"]
    if "atrasa_igual" in tags:
        real = cli["prazo_dias"] + arred(p["mediana"])
        return ("%s aparece na lista de vencidos em %d dos %d fins de mês da base, porque o prazo contratado é de %d dias e ele não "
                "paga nesse prazo: em %d títulos pagos o atraso típico é de %s depois do vencimento, 80%% caem entre %s e %s e o maior atraso "
                "que ele já teve foi de %s. O prazo real dele é de cerca de %d dias. Isto não é cliente ruim, é cliente com outro "
                "prazo. O que fazer: não cobrar antes de %s de atraso, que é o pior que ele já fez; só depois disso ligar. "
                "Se a Aurora quiser que esse prazo deixe de ser exceção, renegociar o prazo contratado, em vez de cobrar todo mês."
                % (nome, r["fins_mes_vencido"], r["fins_mes"], cli["prazo_dias"], r["n_pagos"], _dias(p["mediana"]),
                   _dias(p["p10"]), _dias(p["p90"]), _dias(p["maximo"]), real, _dias(p["maximo"])))
    if "silencioso" in tags:
        partes = []
        if p.get("piora"):
            partes.append("paga cada vez mais tarde (%s de atraso nos últimos %d dias, contra %s antes)"
                          % (_dias(p["rec_med"]), JANELA_RECENTE_DIAS, _dias(p["base_med"])))
        else:
            partes.append("paga um pouco mais tarde (%s contra %s antes)" % (_dias(p["rec_med"]), _dias(p["base_med"])))
        partes.append("e comprou %d%% menos nos últimos %d dias que a média dele" % (round(100 * c["queda"]), JANELA_RECENTE_DIAS))
        return ("%s nunca aparece em lista de vencidos, porque não tem nada vencido hoje, mas %s. É o tipo de cliente que some "
                "sem ninguém perceber. O que fazer: o comercial deve ligar esta semana para entender o que mudou, sem tom de "
                "cobrança, antes que o saldo de %s cresça." % (nome, " ".join(partes), reais(r["saldo"])))
    if "parou" in tags:
        extra = (" Tem %s vencidos, o pior há %s."
                 % (reais(r["vencido"]), _dias(max(t["dias_atraso"] for t in r["vencidos"])))) if r["vencidos"] else ""
        return ("%s parou de comprar: o último pedido foi há %s e o maior intervalo que ele já teve entre pedidos foi de %s.%s "
                "O que fazer: o comercial deve ligar para entender se perdemos o cliente e, se houver título vencido, a cobrança e "
                "a conversa comercial precisam ir juntas, com uma só pessoa conduzindo. Não liberar novo pedido a prazo antes de "
                "acertar o vencido." % (nome, _dias(c["dias_sem_comprar"]), _dias(c["gap_max"]), extra))
    if "piorou" in tags:
        extra = ""
        if c.get("queda_confirmada"):
            extra = (" Ao mesmo tempo, as compras caíram %d%% nos últimos %d dias, o que reforça o sinal." % (
                round(100 * c["queda"]), JANELA_RECENTE_DIAS))
        ven = (" Já tem %s vencidos." % reais(r["vencido"])) if r["vencidos"] else ""
        return ("%s mudou de comportamento: pagava com cerca de %s de atraso e agora paga com %s, %s a mais, muito além da "
                "variação normal dele. Nunca deixou de pagar, mas a mudança é recente e contínua.%s%s O que fazer: ligar esta "
                "semana, antes de liberar novos pedidos a prazo, para entender a causa (caixa do cliente, disputa, troca de "
                "fornecedor) e acompanhar o saldo de %s, que ocupa %d%% do limite."
                % (nome, _dias(p["base_med"]), _dias(p["rec_med"]), _dias(p["delta"]), extra, ven,
                   reais(r["saldo"]), round(100 * r["ocupacao"])))
    if "sazonal" in tags:
        meses = _lista_meses(p["sazonais"])
        return ("%s atrasa mais em %s, e isso se repetiu em anos diferentes: é o calendário do negócio dele, não deterioração. "
                "Nos outros meses paga com cerca de %s de atraso. Por isso esses meses foram descontados da comparação. O que "
                "fazer: não tratar o atraso desses meses como inadimplência; combinar o vencimento com ele, se possível, e "
                "voltar a cobrar pelo padrão normal quando o mês passar."
                % (nome, meses, _dias(p["mediana"])))
    if not p["ok"] or "piora_motivo" in p:
        motivo = p.get("motivo") or p.get("piora_motivo")
        return ("%s tem pouco histórico: %s. Não estimo nada além disso. O que fazer: acompanhar os próximos vencimentos e "
                "voltar a olhar quando houver histórico suficiente." % (nome, motivo))
    amp = p["p90"] - p["p10"]
    if amp > 20 and p["mediana"] >= 15:
        return ("%s paga tarde e sem regularidade: o atraso típico é de %s depois do vencimento, mas 80%% dos pagamentos caem numa "
                "faixa de %s (de %s a %s), e o maior atraso foi de %s. Não há padrão em que se possa confiar, então o prazo "
                "contratado de %d dias não significa nada para ele. O que fazer: cobrar logo após o vencimento em vez de "
                "esperar, e considerar reduzir o limite ou pedir parte do valor antecipada. Não houve piora recente: "
                "%s" % (nome, _dias(p["mediana"]), _dias(amp), _dias(p["p10"]), _dias(p["p90"]), _dias(p["maximo"]),
                        cli["prazo_dias"], "o comportamento atual é o de sempre." if "delta" in p else "sem dados para comparar."))
    faixa = ("entre %s antes e %s depois do vencimento" % (_dias(-p["p10"]), _dias(p["p90"])) if p["p10"] < 0
             else "entre %s e %s depois do vencimento" % (_dias(p["p10"]), _dias(p["p90"])))
    base = ("%s tem padrão estável: paga com cerca de %s de atraso, 80%% dos pagamentos %s, sem piora e sem queda relevante de "
            "compras." % (nome, _dias(p["mediana"]), faixa))
    if _fora_do_padrao(r):
        return base
    return base + " O que fazer: nada além da rotina; cobrar só se passar de %s de atraso, o pior que já teve." % _dias(p["maximo"])


def casos(rs, n_lista):
    """Os dois achados que a planilha erra, como DADO (a tela só desenha). Cada caso: título, tom ('ok' ou 'aviso') e itens
    [{codigo, nome, antes, destaque, depois}]; o texto corrido de um item é nome + antes + destaque + depois."""
    iguais = sorted((r for r in rs if "atrasa_igual" in r["tags"]),
                    key=lambda r: (-(r["fins_mes_vencido"] / r["fins_mes"]), -r["pag"]["mediana"]))
    itens1 = []
    for r in iguais:
        p, cli = r["pag"], r["cliente"]
        itens1.append({
            "codigo": cli["codigo"], "nome": cli["nome"],
            "antes": ": contrato de %d dias, mas paga em cerca de %d dias depois do vencimento (80%% entre %d e %d, maior atraso %d). "
                     "Aparece na lista de vencidos em %d de %d fins de mês. " % (
                         cli["prazo_dias"], arred(p["mediana"]), arred(p["p10"]), arred(p["p90"]), p["maximo"],
                         r["fins_mes_vencido"], r["fins_mes"]),
            "destaque": "Prazo real: cerca de %d dias." % (cli["prazo_dias"] + arred(p["mediana"])),
            "depois": " Só cobrar depois de %d dias de atraso." % p["maximo"]})
    if not itens1:
        itens1 = [{"codigo": None, "nome": None, "antes": "Nenhum cliente passa nos critérios hoje.", "destaque": "", "depois": ""}]
    sil = [r for r in rs if "silencioso" in r["tags"]]
    itens2 = []
    if sil:
        for r in sil:
            itens2.append({"codigo": r["cliente"]["codigo"], "nome": r["cliente"]["nome"], "antes": ": " + r["alerta"],
                           "destaque": "", "depois": ""})
    else:
        itens2.append({"codigo": None, "nome": None, "destaque": "", "depois": "", "antes":
                       "Nenhum cliente da base é, ao mesmo tempo, sem título vencido, pagando mais tarde e comprando menos: "
                       "a busca pelos critérios (piora confirmada ou queda de compras confirmada, sem nada vencido) não encontrou ninguém."})
        for r in (r for r in rs if "piorou" in r["tags"] and "compra_menos" in r["tags"]):
            pos = r["pos_lista_data"]
            itens2.append({
                "codigo": r["cliente"]["codigo"], "nome": r["cliente"]["nome"],
                "antes": "", "destaque": "", "depois": "",
                "frase": ("O mais parecido é %s: nunca deixou de pagar, paga com %d dias de atraso contra %d antes e comprou %d%% menos. "
                          "Só que ele aparece na lista de vencidos, escondido: em uma lista por data, seus %d títulos ficam nas posições "
                          "%s de %d, misturados com outros clientes." % (
                              r["cliente"]["nome"], arred(r["pag"]["rec_med"]), arred(r["pag"]["base_med"]),
                              round(100 * r["compras"]["queda"]), len(pos), ", ".join(map(str, pos)), n_lista))})
    return [{"titulo": "Aparece como atrasado, mas não é risco", "tom": "ok", "itens": itens1},
            {"titulo": "Nunca aparece em lista, mas piora e compra menos", "tom": "aviso", "itens": itens2}]


def descobertas(rs, n_lista):
    """Até três achados que uma lista por data não mostra, como DADO curto (a tela Hoje só desenha; a Risco mostra os mesmos por extenso).
    Cada um: {tipo 'crit'|'ok'|'aten', rotulo, nome, codigo, o_que}. Nada é recalculado: tudo vem da leitura de cada cliente."""
    out = []
    piora = [r for r in rs if {"piorou", "silencioso"} & set(r["tags"])]
    if piora:
        r = max(piora, key=lambda x: x["valor_em_risco"])
        p, c = r["pag"], r["compras"]
        txt = "Pagava com cerca de %s de atraso; agora paga com %s." % (_dias(arred(p["base_med"])), _dias(arred(p["rec_med"])))
        if c.get("queda_confirmada"):
            txt += " Comprou %d%% menos." % round(100 * c["queda"])
        if "silencioso" in r["tags"]:
            rot = "Piora sem aparecer em lista"
        else:
            rot = "Mudou de comportamento"
        out.append({"tipo": "crit", "rotulo": rot, "nome": r["cliente"]["nome"], "codigo": r["cliente"]["codigo"], "o_que": txt})
    iguais = sorted((r for r in rs if "atrasa_igual" in r["tags"]),
                    key=lambda r: (-(r["fins_mes_vencido"] / r["fins_mes"]), -r["pag"]["mediana"]))
    if iguais:
        r = iguais[0]
        mais = len(iguais) - 1
        nome = r["cliente"]["nome"] + ((" e mais %d" % mais) if mais else "")
        out.append({"tipo": "ok", "rotulo": "Aparece como atrasado, mas não é risco", "nome": nome, "codigo": r["cliente"]["codigo"],
                    "o_que": "Paga sempre com o mesmo atraso (cerca de %s). Só cobrar depois de %s." % (
                        _dias(arred(r["pag"]["mediana"])), _dias(r["pag"]["maximo"]))})
    resto = [r for r in rs if r["cliente"]["codigo"] not in {x["codigo"] for x in out} and "parou" in r["tags"]]
    if resto:
        r = max(resto, key=lambda x: x["valor_em_risco"])
        c = r["compras"]
        out.append({"tipo": "aten", "rotulo": "Parou de comprar", "nome": r["cliente"]["nome"], "codigo": r["cliente"]["codigo"],
                    "o_que": "Último pedido há %s; o maior intervalo dele foi de %s." % (_dias(c["dias_sem_comprar"]), _dias(c["gap_max"]))})
    else:
        fora = [(r, risco_fora) for r in rs for risco_fora in [_fora_do_padrao(r)] if risco_fora]
        if fora:
            r, ts = max(fora, key=lambda x: x[0]["valor_em_risco"])
            t = max(ts, key=lambda x: x["dias_atraso"])
            out.append({"tipo": "aten", "rotulo": "Atraso maior que qualquer outro dele", "nome": r["cliente"]["nome"],
                        "codigo": r["cliente"]["codigo"],
                        "o_que": "Título vencido há %s; o maior atraso que ele já teve foi de %s." % (_dias(t["dias_atraso"]), _dias(r["pag"]["maximo"]))})
    return out


def achados(rs):
    """TODOS os casos em que a lista de vencidos engana ou esconde algo, um por cliente, cada um em uma ou duas frases (DADO; a tela só desenha).
    O texto completo de cada um continua em r["alerta"] e nos dois achados por extenso (casos). Cada item: {tipo, rotulo, nome, codigo, curto}."""
    out = []
    for r in rs:  # já vem na ordem do valor em risco
        t, p, c, cli = set(r["tags"]), r["pag"], r["compras"], r["cliente"]
        item = None
        if "piorou" in t or "silencioso" in t:
            txt = "Pagava com cerca de %s de atraso; agora paga com %s." % (_dias(arred(p["base_med"])), _dias(arred(p["rec_med"])))
            if c.get("queda_confirmada"):
                txt += " Comprou %d%% menos." % round(100 * c["queda"])
            item = ("crit", "Mudou de comportamento" if "piorou" in t else "Piora sem aparecer em lista", txt)
        elif "parou" in t:
            item = ("aten", "Parou de comprar", "Último pedido há %s; o maior intervalo dele foi de %s." % (_dias(c["dias_sem_comprar"]), _dias(c["gap_max"])))
        elif _fora_do_padrao(r):
            ts = _fora_do_padrao(r)
            tt = max(ts, key=lambda x: x["dias_atraso"])
            item = ("aten", "Atraso maior que o dele", "Título vencido há %s; o maior atraso que ele já teve foi de %s." % (_dias(tt["dias_atraso"]), _dias(p["maximo"])))
        elif "compra_menos" in t:
            item = ("aten", "Comprando menos", "Comprou %d%% menos nos últimos %d dias que a média dele." % (round(100 * c["queda"]), JANELA_RECENTE_DIAS))
        elif "atrasa_igual" in t:
            item = ("ok", "Aparece atrasado, mas não é risco", "Paga sempre com cerca de %s de atraso; só cobrar depois de %s." % (_dias(arred(p["mediana"])), _dias(p["maximo"])))
        elif "sazonal" in t:
            item = ("ok", "Atraso sazonal, não é risco", "Atrasa mais em %s, em anos diferentes: é o calendário dele." % _lista_meses(p["sazonais"]))
        if item:
            out.append({"tipo": item[0], "rotulo": item[1], "nome": cli["nome"], "codigo": cli["codigo"], "curto": item[2]})
    return out
