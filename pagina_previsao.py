"""Tela "Previsão de caixa" (tema Aurora). HTML puro, gráficos em SVG inline.

Dois gráficos, cada um com o motivo de estar ali: a cascata mostra DE ONDE vem a diferença (planilha -> esperado) e o acumulado mostra QUANDO o
dinheiro entra, com a faixa de incerteza. As tabelas e os textos longos continuam na página, atrás de dobra.
"""
from html import escape

import previsao as pv
from frases import envolve_dinheiro, pl, reais, reais_int
from visual import _d, caixa_avisos, pagina as _casca

E = pv.reais_est


def _rotulo_eixo(v):
    """Centavos -> rótulo curto do eixo: 0, 'R$ 200 mil', 'R$ 1 milhão'."""
    r = v // 100
    if r == 0:
        return "0"
    if r % 1000000 == 0:
        return "R$ %d milh%s" % (r // 1000000, "ão" if r == 1000000 else "ões")
    return "R$ %d mil" % (r // 1000)


def _grafico(prev):
    W, H, L, R, T, B = 760, 330, 84, 175, 14, 58
    cum = prev["cum"]
    top = max(max(cum["plan"]), max(cum["otim"]))
    passo = next(s for s in (50000, 100000, 200000, 250000, 500000) if top / 100 / s <= 6)
    ymax = max(-(-top // (passo * 100)) * passo * 100, passo * 100)  # carteira sem nada a receber: o eixo não pode ter altura zero
    xs = lambda i: L + (W - L - R) * i / pv.SEMANAS
    ys = lambda v: T + (H - T - B) * (1 - v / ymax)
    pts = lambda serie: [(xs(i), ys(v)) for i, v in enumerate([0] + serie)]
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Caixa acumulado: planilha, esperado e faixa conservador–otimista">' % (W, H)]
    v = 0
    while v <= ymax:
        out.append('<line class="grid" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/><text x="%d" y="%.1f" text-anchor="end">%s</text>'
                   % (L, W - R, ys(v), ys(v), L - 6, ys(v) + 4, _rotulo_eixo(v)))
        v += passo * 100
    cons, otim = pts(cum["cons"]), pts(cum["otim"])
    out.append('<polygon class="faixa" points="%s"><title>faixa entre o cenário conservador e o otimista, no acumulado</title></polygon>'
               % " ".join("%.1f,%.1f" % p for p in otim + cons[::-1]))
    for nome, serie, cls in (("planilha", cum["plan"], "plan"), ("esperado", cum["esp"], "esp")):
        out.append('<polyline class="%s" points="%s"/>' % (cls, " ".join("%.1f,%.1f" % p for p in pts(serie))))
    for i in range(pv.SEMANAS + 1):
        lab = "hoje" if i == 0 else "sem. %d" % i
        out.append('<text x="%.1f" y="%d" text-anchor="middle">%s</text>' % (xs(i), H - B + 19, lab))
        if i:
            out.append('<text x="%.1f" y="%d" text-anchor="middle">%s</text>' % (xs(i), H - B + 44, prev["semanas"][i - 1][1].strftime("%d/%m")))
    x = xs(pv.SEMANAS) + 6
    rotulos = sorted(((ys(v) + 4, txt, v, cor) for txt, v, cor in (
        ("planilha", cum["plan"][-1], "#9199c6"), ("otimista", cum["otim"][-1], "#7aeaff"),
        ("esperado", cum["esp"][-1], "#c6b8ff"), ("conservador", cum["cons"][-1], "#7aeaff"))), key=lambda r: r[0])
    anterior = -99
    for y, txt, v, cor in rotulos:
        y = max(y, anterior + 24)  # rótulos não se sobrepõem
        anterior = y
        out.append('<text class="rot" x="%.1f" y="%.1f" style="fill:%s">%s %s</text>' % (x, y, cor, txt, E(v)))
    out.append("</svg>")
    return '<div class="rolagem">%s</div>' % "".join(out)


def _cascata(plan_int, partes, esp_int):
    """Cascata: planilha -> cada parte da diferença -> esperado. Valores em reais inteiros (as partes já vêm arredondadas para somar certo)."""
    nomes = ["Adiado", "Sem data", "Chance de não entrar", "Antecipado"]
    W, H, T, B, L = 640, 320, 26, 66, 10
    n = 6
    w = (W - L - 10) / n
    niveis = [plan_int]
    for v in partes:
        niveis.append(niveis[-1] - v)
    topo = max(niveis + [plan_int, esp_int, 1]) * 1.06
    ys = lambda v: T + (H - T - B) * (1 - v / topo)
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Da planilha ao esperado: adiado, sem data, chance de não entrar e antecipado">' % (W, H)]
    out.append('<line class="grid" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>' % (L, W - 10, ys(0), ys(0)))

    def barra(i, a, b, cls, valor, nome):
        x = L + w * i + w * 0.14
        y0, y1 = ys(max(a, b)), ys(min(a, b))
        out.append('<rect class="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4"/>' % (cls, x, y0, w * 0.72, max(y1 - y0, 2)))
        out.append('<text class="rot" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (x + w * 0.36, y0 - 6, valor))
        linhas = [nome] if " de " not in nome else [nome.split(" de ", 1)[0] + " de", nome.split(" de ", 1)[1]]
        for j, pedaco in enumerate(linhas):
            out.append('<text x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x + w * 0.36, H - B + 18 + 24 * j, pedaco))

    barra(0, 0, plan_int, "cb-plan", reais_int(plan_int), "Planilha")
    for i, v in enumerate(partes):
        rot = ("−" + reais_int(v)) if v > 0 else (("+" + reais_int(-v)) if v < 0 else reais_int(0))
        barra(i + 1, niveis[i], niveis[i + 1], "cb-menos" if v > 0 else "cb-mais", rot, nomes[i])
    barra(5, 0, esp_int, "cb-esp", reais_int(esp_int), "Esperado")
    out.append("</svg>")
    return "".join(out)


def _k(v):
    """Reais inteiros -> rótulo curto de gráfico: 'R$ 477 mil'."""
    return "R$ %d mil" % round(v / 1000) if abs(v) >= 1000 else reais_int(v)


def _grafico_semanas(prev, esp_sem):
    """Quanto entra em cada semana: o que a planilha aponta × o que espero. A planilha joga todo o vencido na semana 1."""
    W, H, L, T, B = 640, 280, 76, 24, 46
    p = prev
    plan = [pv.est(x) for x in p["planilha"]]
    topo = max(plan + list(esp_sem) + [1])
    passo = next(s for s in (50000, 100000, 200000, 250000, 500000) if topo / s <= 5)
    ymax = -(-topo // passo) * passo
    ys = lambda v: T + (H - T - B) * (1 - v / ymax)
    n = len(plan)
    w = (W - L - 10) / n
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Por semana: o que a planilha aponta e o que se espera receber">' % (W, H)]
    v = 0
    while v <= ymax:
        out.append('<line class="grid" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/><text x="%d" y="%.1f" text-anchor="end">%s</text>' % (L, W - 10, ys(v), ys(v), L - 6, ys(v) + 4, _k(v) if v else "0"))
        v += passo
    for i in range(n):
        x0 = L + w * i + w * 0.12
        bw = w * 0.36
        for j, (val, cls) in enumerate(((plan[i], "b-plan"), (esp_sem[i], "b-esp"))):
            out.append('<rect class="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3"/>' % (cls, x0 + j * (bw + 3), ys(val), bw, max(ys(0) - ys(val), 1)))
            out.append('<text class="rot" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (x0 + j * (bw + 3) + bw / 2, ys(val) - 5, _k(val)))
        out.append('<text x="%.1f" y="%d" text-anchor="middle">semana %d</text><text x="%.1f" y="%d" text-anchor="middle">%s a %s</text>' % (
            L + w * (i + .5), H - B + 18, i + 1, L + w * (i + .5), H - B + 34, p["semanas"][i][0].strftime("%d/%m"), p["semanas"][i][1].strftime("%d/%m")))
    out.append("</svg>")
    leg = ('<div class="leg"><span><i class="sw" style="background:rgba(185,195,255,.5)"></i>planilha</span>'
           '<span><i class="sw" style="background:linear-gradient(#9a8cff,#3cc8f0)"></i>esperado</span></div>')
    return "".join(out) + leg


def _grafico_clientes(p):
    """Quem pesa na diferença: quanto cada cliente 'promete a mais' na planilha do que deve entrar."""
    top = sorted(p["clientes"], key=lambda c: -c["diferenca"])[:8]
    W, H, L, T = 640, 280, 230, 8
    h = (H - T - 6) / max(len(top), 1)
    mx = max((c["diferenca"] for c in top), default=1) or 1
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Quanto cada cliente promete a mais na planilha do que deve entrar">' % (W, H)]
    for i, c in enumerate(top):
        y = T + h * i
        w = (W - L - 110) * c["diferenca"] / mx
        cls = "b-crit" if c["r"]["pag"].get("piora") else "b-aten"
        nome = c["cliente"]["nome"]
        out.append('<text x="%d" y="%.1f" text-anchor="end">%s</text>' % (L - 8, y + h * 0.55, escape(nome if len(nome) <= 26 else nome[:25].rstrip() + "…")))
        out.append('<rect class="%s" x="%d" y="%.1f" width="%.1f" height="%.1f" rx="3"/>' % (cls, L, y + h * 0.2, max(w, 2), h * 0.55))
        out.append('<text class="rot" x="%.1f" y="%.1f">%s</text>' % (L + w + 8, y + h * 0.55, reais_int(pv.est(c["diferenca"]))))
    out.append("</svg>")
    leg = '<div class="leg"><span><i class="sw" style="background:rgba(255,117,144,.75)"></i>piorou</span><span><i class="sw" style="background:rgba(255,201,102,.75)"></i>os demais</span></div>'
    return "".join(out) + leg


def pagina(ref, rs, prev):
    p = prev
    plan, esp = p["total_planilha"], p["total_esp"]
    dif = p["diferenca"]
    pct = round(100 * dif / plan) if plan else 0
    ven_esp = sum(l["esperado"] for l in p["linhas"] if l["categoria"] == "projetado" and l["semanas"]["esp"] and l["dias_atraso"] > 0)
    avencer_esp = esp - ven_esp
    sem_ven = plan - p["vencidos_na_planilha"]
    d = p["dec"]
    partes = pv.arredonda_partes([d["adiado"], d["sem_data"], d["probabilidade"], d["antecipado"]])
    fmt = reais_int
    fim = p["semanas"][-1][1]
    ini = p["semanas"][0][0]
    cum = p["cum"]
    esp_sem = pv.arredonda_partes(p["cen"]["esp"])

    painel = """<section class="painel prev vidro brilho" aria-label="Resumo da previsão">
<div class="esq"><span class="eyebrow">diferença: quanto a planilha promete a mais do que deve entrar</span>
<span class="grande" data-conta="%d">%s</span>
<p class="apoio" style="margin-top:.4rem">%d%% do que a planilha aponta não entra nas quatro semanas, ou não dá para dizer quando entra.</p>
<div class="duo"><div><b>%s</b>O que a planilha aponta: soma dos vencimentos até %s</div><div><b>%s</b>O que espero, lendo como cada cliente paga de verdade</div></div></div>
<div><span class="eyebrow">De onde vem a diferença</span>%s</div></section>""" % (
        (dif + 50) // 100, E(dif), pct, E(plan), fim.strftime("%d/%m"), E(esp), _cascata(pv.est(plan), partes, pv.est(esp)))

    dec = """<div class="decomp">
<div><b>%s</b>Adiado: títulos que vencem nas quatro semanas, mas que o cliente só costuma pagar depois de %s.</div>
<div><b>%s</b>Sem data: vencido que já passou de todo atraso que o cliente teve, ou sem histórico. A planilha conta; eu não consigo datar.</div>
<div><b>%s</b>Chance de não entrar: desconto pelo risco do cliente e pela idade do título, nos que entram no prazo.</div>
<div><b>%s</b>Antecipado: títulos que vencem depois da janela, mas que o cliente costuma pagar dentro dela.</div></div>""" % (
        fmt(partes[0]), fim.strftime("%d/%m"), fmt(partes[1]), fmt(partes[2]), fmt(partes[3]))

    nota_ven = ("<p>Um cuidado: a planilha põe na semana 1 todo título já vencido (%s). Se ela ignorasse os vencidos, somaria %s, "
                "número que parece perto do esperado. É coincidência: desses %s a vencer eu espero %s, e dos vencidos espero %s.</p>"
                % (envolve_dinheiro(escape(reais(p["vencidos_na_planilha"]))), envolve_dinheiro(escape(reais(sem_ven))),
                   envolve_dinheiro(escape(reais(sem_ven))), E(avencer_esp), E(ven_esp)))

    cons_c = [pv.est(x) for x in cum["cons"]]
    esp_c = [pv.est(x) for x in cum["esp"]]
    otim_c = [pv.est(x) for x in cum["otim"]]
    lin = ""
    acum_plan = 0
    for i, (a, b) in enumerate(p["semanas"]):
        acum_plan += p["planilha"][i]
        lin += ("<tr><td data-l=''><b>Semana %d</b> · %s a %s</td><td class='n' data-l='Planilha na semana'>%s</td><td class='n' data-l='Esperado na semana'>%s</td>"
                "<td class='n' data-l='Planilha acumulada'>%s</td><td class='n' data-l='Conservador acumulado'>%s</td><td class='n' data-l='Esperado acumulado'><b>%s</b></td>"
                "<td class='n' data-l='Otimista acumulado'>%s</td></tr>" % (
                    i + 1, a.strftime("%d/%m"), b.strftime("%d/%m"), reais(p["planilha"][i]), fmt(esp_sem[i]), reais(acum_plan),
                    fmt(cons_c[i]), fmt(esp_c[i]), fmt(otim_c[i])))
    cruza = next(((i, p["cen"]["cons"][i], p["cen"]["otim"][i]) for i in range(pv.SEMANAS) if p["cen"]["cons"][i] > p["cen"]["otim"][i]), None)
    ex = ("Neste caso real: na semana %d o cenário conservador recebe %s e o otimista só %s. O conservador ficou à frente porque o "
          "dinheiro que o otimista já recebeu nas semanas anteriores não conta de novo." % (
              cruza[0] + 1, E(cruza[1]), E(cruza[2]))) if cruza else ""
    faixa_txt = ("<p><b>Por que a faixa é no acumulado.</b> Atrasar não faz o dinheiro sumir, só empurra para a semana seguinte. "
                 "Semana a semana, o cenário conservador às vezes recebe mais que o otimista, porque o otimista já recebeu antes o que o conservador "
                 "só recebe depois, e a faixa ficaria invertida. Somando semana após semana isso se desfaz: em nenhum ponto o conservador passa do "
                 "esperado, nem este do otimista. %s</p>" % ex)

    linhas_c = "".join(
        "<tr><td data-l=''><span class='nome'><a href='/risco/%d'>%s</a></span>%s</td><td class='n' data-l='Planilha'>%s</td><td class='n' data-l='Esperado'>%s</td>"
        "<td class='n' data-l='Diferença'><span class='din'>%s</span></td><td data-l=''>%s</td></tr>" % (
            c["cliente"]["codigo"], escape(c["cliente"]["nome"]),
            ' <span class="chip ruim">piorou</span>' if c["r"]["pag"].get("piora") else "",
            reais(c["planilha"]), E(c["previsao"]), fmt(pv.est(c["diferenca"])), envolve_dinheiro(escape(c["frase"])))
        for c in p["clientes"])

    nomes = {r["cliente"]["codigo"]: r["cliente"]["nome"] for r in rs}
    tl = ""
    for l in sorted(p["linhas"], key=lambda l: (nomes[l["cliente"]], l["vencimento"])):
        if l["categoria"] == "projetado":
            dt = l["datas"]
            datas = "%s (%s a %s)" % (dt["esp"].strftime("%d/%m"), dt["otim"].strftime("%d/%m"), dt["cons"].strftime("%d/%m"))
            sit = ("semana %d" % l["semanas"]["esp"]) if l["semanas"]["esp"] else "depois de %s" % fim.strftime("%d/%m")
            chance, esperado = "%d%%" % round(l["prob_bp"] / 100), E(l["esperado"])
        else:
            datas, chance, esperado = "—", "—", "—"
            sit = "sem data: " + ("passou de todo atraso que ele já teve" if l["categoria"] == "sem_precedente" else "sem histórico")
        tl += ("<tr><td>%s</td><td>%s</td><td class='n'>%s</td><td>%s</td><td class='n'>%s</td><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td>%s</td></tr>" % (
            escape(l["numero"]), escape(nomes[l["cliente"]]), reais(l["valor"]), _d(l["vencimento"]),
            ("%d" % l["dias_atraso"]) if l["dias_atraso"] else "—", datas, chance, esperado, sit))

    prem = """<ul>
<li><b>Data esperada</b> = vencimento + o atraso que o cliente pratica (o típico, o do meio). Para quem a tela de risco marca como "piorou", vale o comportamento recente (os últimos pagamentos), não o de todo o histórico. Meses sazonais do cliente usam o atraso daquele mês. É a mesma leitura da tela Risco por cliente.</li>
<li><b>Dia bom e dia ruim:</b> o conservador usa o atraso do pior 10%% dos pagamentos do cliente; o otimista, o do melhor 10%%. Nos três cenários a chance de entrar é a mesma; só a data muda.</li>
<li><b>Título já vencido:</b> vale só o que o cliente fez depois de ter chegado àquele atraso. Se menos de %d pagamentos dele levaram tanto tempo, não projeto data (aparece como "sem data").</li>
<li><b>Chance de entrar</b> = (1 − %d%% × índice de risco do cliente) × (1 − %d%% × posição do atraso atual no histórico dele, só para vencidos). Não há nenhum título perdido no histórico da base, então essas duas taxas são premissas, não medidas; quem mantém a Central pode ajustá-las.</li>
<li><b>Planilha:</b> todo título em aberto que vence até %s, e todo título já vencido, que ela põe na semana 1. Valores de título exatos; o que é estimativa está arredondado em reais.</li>
<li>As quatro semanas começam em %s, o dia seguinte à data de referência da base (%s). Se o cliente costuma pagar antes do vencimento, o dinheiro entra a partir desse primeiro dia, nunca antes.</li></ul>""" % (
        pv.MIN_CONDICIONAL, round(100 * pv.K_RISCO), round(100 * pv.K_IDADE), fim.strftime("%d/%m"), ini.strftime("%d/%m"), _d(ref))

    corpo = """<h1 class="sr">Previsão de caixa</h1>
<p class="pill-aviso">Próximas quatro semanas, de %s a %s · <b>Só a carteira que já existe.</b> Considera %s em aberto hoje e nenhuma venda nova. Não é projeção comercial.</p>
%s
<div class="graficos2">
<div class="cx vidro"><h3>Acumulado de caixa</h3><p class="por">Quanto do dinheiro já terá entrado ao fim de cada semana; a faixa é a margem entre um cenário ruim e um bom.</p>%s
<div class="leg"><span>Linha cheia: esperado.</span><span>Pontilhada: planilha.</span><span>Faixa: do conservador ao otimista.</span></div></div>
<div class="cx vidro"><h3>Quanto entra em cada semana</h3><p class="por">A planilha põe todo o vencido na semana 1; o esperado distribui como cada cliente costuma pagar.</p>%s</div>
<div class="cx vidro"><h3>Quem pesa na diferença</h3><p class="por">Os clientes que a planilha mais promete além do que deve entrar.</p>%s</div>
<div class="cx vidro"><h3>O que cada parte da diferença quer dizer</h3>%s</div></div>
<details class="dobra vidro"><summary>Um cuidado com os vencidos da planilha</summary><div class="corpo">%s</div></details>
<details class="dobra vidro" style="margin-top:.6rem"><summary>Por que a faixa é no acumulado</summary><div class="corpo">%s</div></details>
<details class="dobra vidro" style="margin-top:.6rem"><summary>Semana a semana</summary><div class="corpo"><div class="tabela-wrap"><table class="tabela cartoes"><thead><tr><th>Semana</th><th class="n">Planilha na semana</th><th class="n">Esperado na semana</th><th class="n">Planilha acumulada</th><th class="n">Conservador acumulado</th><th class="n">Esperado acumulado</th><th class="n">Otimista acumulado</th></tr></thead><tbody>%s</tbody></table></div></div></details>
<details class="dobra vidro" style="margin-top:.6rem"><summary>Cliente por cliente</summary><div class="corpo"><div class="tabela-wrap"><table class="tabela cartoes"><thead><tr><th>Cliente</th><th class="n">Planilha</th><th class="n">Esperado</th><th class="n">Diferença</th><th>Por quê</th></tr></thead><tbody>%s</tbody></table></div></div></details>
<details class="dobra vidro" style="margin-top:.6rem"><summary>Título a título (%s)</summary><div class="corpo"><div class="tabela-wrap"><table class="tabela"><thead><tr><th>Título</th><th>Cliente</th><th class="n">Valor</th><th>Vencimento</th><th class="n">Dias de atraso</th><th>Data esperada (otimista a conservador)</th><th class="n">Chance</th><th class="n">Esperado</th><th>Onde cai</th></tr></thead><tbody>%s</tbody></table></div></div></details>
<details class="dobra vidro" style="margin-top:.6rem"><summary>Como foi calculado</summary><div class="corpo"><p>Posição em %s.</p>%s</div></details>""" % (
        ini.strftime("%d/%m"), fim.strftime("%d/%m"), pl(len(p["linhas"]), "título", "títulos"), painel,
        _grafico(p), _grafico_semanas(p, esp_sem), _grafico_clientes(p), dec, nota_ven, faixa_txt, lin, linhas_c,
        pl(len(p["linhas"]), "título", "títulos"), tl, _d(ref), prem)
    return _casca("Previsão de caixa", corpo, "previsao", ref)
