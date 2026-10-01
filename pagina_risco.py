"""Telas "Risco por cliente" (lista) e ficha do cliente, no tema Aurora. HTML puro, gráficos em SVG inline.

Os textos longos (alerta por extenso, fatores do índice, histórico completo, os dois achados por extenso) continuam na página, atrás de dobra.
"""
import re
import statistics
from html import escape

import risco
from frases import _dias, arred, envolve_dinheiro, faixa_risco, pct1, pl, reais, reais_est
from pagina import LUPA
from risco import MESES_ABREV, MESES_NOME
from visual import _d, caixa_avisos, chip_risco, pagina as _casca

ROTULOS = {
    "atrasa_igual": ("Atrasa sempre igual: não é risco", "ok"),
    "sazonal": ("Atraso sazonal: não é risco", "ok"),
    "piorou": ("Piorou", "ruim"),
    "parou": ("Parou de comprar", "ruim"),
    "compra_menos": ("Comprando menos", "ruim"),
    "silencioso": ("Piora sem aparecer em lista", "ruim"),
    "falta_dado": ("Falta dado em alguma conta", ""),
}
COM_ALERTA = {"piorou", "parou", "compra_menos", "silencioso"}
SPARK_MIN_DIAS = 8  # a linha de atraso só aparece se o atraso típico variou ao menos isto (em dias) nos 12 meses
VOLTAR = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" style="stroke:currentColor;fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round"><path d="M15 6l-6 6 6 6"/></svg>'


def _chips(r):
    return "".join('<span class="chip %s">%s</span>' % (ROTULOS[t][1], escape(ROTULOS[t][0])) for t in r["tags"] if t in ROTULOS)


def _casos(ref, rs, n_lista):
    """Os dois achados por extenso (o texto vem de risco.casos; a tela só desenha)."""
    caixas = []
    for caso in risco.casos(rs, n_lista):
        ps = []
        for it in caso["itens"]:
            if it.get("frase"):  # "o mais parecido é <cliente>": o nome vira link dentro da frase
                nome = it["nome"]
                corpo = escape(it["frase"]).replace(escape(nome), '<a href="/risco/%d">%s</a>' % (it["codigo"], escape(nome)), 1)
                ps.append("<p>%s</p>" % envolve_dinheiro(corpo))
                continue
            nome = ('<a href="/risco/%d">%s</a>' % (it["codigo"], escape(it["nome"]))) if it["codigo"] else ""
            destaque = ("<b>%s</b>" % escape(it["destaque"])) if it["destaque"] else ""
            ps.append("<p>%s%s%s%s</p>" % (nome, envolve_dinheiro(escape(it["antes"])), destaque, envolve_dinheiro(escape(it["depois"]))))
        caixas.append('<div class="achado"><h3>%s</h3>%s</div>' % (escape(caso["titulo"]), "".join(ps)))
    return "".join(caixas)


def _spark(r, ref, topo):
    """Linha miúda do atraso típico mês a mês (últimos 12 meses). Só aparece quando a linha TEM forma (variou 6 dias ou mais):
    quem sempre atrasou os mesmos dias teria uma reta, que não diz nada."""
    k1 = (ref.year, ref.month)
    meses, y, m = [], k1[0], k1[1]
    for _ in range(12):
        meses.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    meses.reverse()
    pts = [(i, statistics.median(r["serie"][k])) for i, k in enumerate(meses) if k in r["serie"]]
    if len(pts) < 3:
        return '<span class="mut">sem histórico</span>'
    lo, hi = min(v for _, v in pts), max(v for _, v in pts)
    if hi - lo < SPARK_MIN_DIAS:
        return '<span class="mut">estável</span>'
    W, H = 112, 28
    xy = [(3 + (W - 6) * i / 11.0, H - 4 - (H - 9) * max(v, 0) / topo) for i, v in pts]  # escala única para todos: reta é reta
    linha = " ".join("%.1f,%.1f" % p for p in xy)
    area = "%s %.1f,%d %.1f,%d" % (linha, xy[-1][0], H, xy[0][0], H)
    cor = {"alto": "var(--crit)", "medio": "var(--aten)", "baixo": "var(--ok)"}[faixa_risco(r["indice"])[0]]
    resumo = "atraso típico por mês: %s no mês mais antigo, %s no último" % (_dias(pts[0][1]), _dias(pts[-1][1]))
    return ('<svg class="spark" viewBox="0 0 %d %d" role="img" aria-label="%s"><polygon class="a" points="%s"/><polyline class="l" points="%s"/>'
            '<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/></svg><span class="sr">%s</span>' % (
                W, H, resumo, area, linha, xy[-1][0], xy[-1][1], cor, resumo))


def _curto(nome, n=24):
    return nome if len(nome) <= n else nome[:n - 1].rstrip() + "…"


def _grafico_bolhas(rs):
    """Quem deve muito e quem está arriscado, de uma vez: saldo em aberto (para cima) × índice de risco (para a direita); o tamanho da bolha é
    o valor em risco; anel tracejado = piorando. O canto de cima à direita é onde olhar primeiro."""
    W, H, L, R_, T, B = 640, 300, 76, 16, 26, 38
    topo = max(r["saldo"] for r in rs) or 1
    passo = next(s for s in (50000, 100000, 200000, 250000, 500000, 1000000) if topo / 100 / s <= 5)
    ymax = -(-topo // (passo * 100)) * passo * 100
    xs = lambda i: L + (W - L - R_) * i / 100.0
    ys = lambda v: T + (H - T - B) * (1 - v / ymax)
    mx = max(r["valor_em_risco"] for r in rs) or 1
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Cada cliente: índice de risco na horizontal, saldo em aberto na vertical, bolha pelo valor em risco">' % (W, H)]
    for a, b, rot, cor in ((0, 30, "baixo", "79,227,166"), (30, 60, "médio", "255,201,102"), (60, 100, "alto", "255,117,144")):
        out.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="rgba(%s,.07)"/><text x="%.1f" y="%d" text-anchor="middle">risco %s</text>' % (
            xs(a), T, xs(b) - xs(a), H - T - B, cor, (xs(a) + xs(b)) / 2, T - 8, rot))
    v = 0
    while v <= ymax:
        out.append('<line class="grid" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/><text x="%d" y="%.1f" text-anchor="end">%s</text>' % (
            L, W - R_, ys(v), ys(v), L - 6, ys(v) + 4, _rotulo_mil(v)))
        v += passo * 100
    for x in (0, 30, 60, 100):
        out.append('<text x="%.1f" y="%d" text-anchor="middle">%d</text>' % (xs(x), H - B + 16, x))
    out.append('<text x="%.1f" y="%d" text-anchor="middle">índice de risco</text>' % ((L + W - R_) / 2, H - 6))
    ordem = sorted(rs, key=lambda r: -r["valor_em_risco"])
    rotulados = {r["cliente"]["codigo"] for r in ordem[:5]}
    usados = []
    for r in sorted(rs, key=lambda r: -r["valor_em_risco"]):  # as maiores primeiro; as menores ficam por cima
        k = faixa_risco(r["indice"])[0]
        cls = {"alto": "b-crit", "medio": "b-aten", "baixo": "b-ok"}[k]
        rad = 5 + 15 * (r["valor_em_risco"] / mx) ** 0.5
        cx, cy = xs(r["indice"]), ys(r["saldo"])
        out.append('<circle class="bolha %s" cx="%.1f" cy="%.1f" r="%.1f"><title>%s: índice %d, saldo %s, valor em risco %s</title></circle>' % (
            cls, cx, cy, rad, escape(r["cliente"]["nome"]), r["indice"], reais_est(r["saldo"]), reais_est(r["valor_em_risco"])))
        if {"piorou", "silencioso", "compra_menos"} & set(r["tags"]):
            out.append('<circle class="piora" cx="%.1f" cy="%.1f" r="%.1f"/>' % (cx, cy, rad + 4))
        if r["cliente"]["codigo"] in rotulados:
            lado = "end" if cx > W - 170 else "start"
            dx = -(rad + 7) if lado == "end" else rad + 7
            ly = cy + 4
            while any(abs(ly - oy) < 14 and abs((cx + dx) - ox) < 120 for ox, oy in usados):  # não deixa um nome em cima do outro
                ly += 14
            usados.append((cx + dx, ly))
            out.append('<text x="%.1f" y="%.1f" text-anchor="%s">%s</text>' % (cx + dx, ly, lado, escape(_curto(r["cliente"]["nome"], 20))))
    out.append("</svg>")
    leg = ('<div class="leg"><span>Tamanho da bolha: valor em risco.</span>'
           '<span><i class="sw" style="border:2px dashed #fff;border-radius:50%;height:.7rem;width:.7rem"></i>piorando</span></div>')
    return "".join(out) + leg


def _rotulo_mil(v):
    r = v // 100
    return "0" if r == 0 else ("R$ %d milh%s" % (r // 1000000, "ão" if r == 1000000 else "ões") if r % 1000000 == 0 else "R$ %d mil" % (r // 1000))


def _grafico_concentracao(rs):
    """Onde está o valor em risco: as barras maiores são onde o dinheiro está."""
    tot = risco.totais(rs)["valor_em_risco"] or 1
    top = sorted(rs, key=lambda r: -r["valor_em_risco"])[:8]
    W, H, L, T = 640, 300, 230, 8
    h = (H - T - 6) / len(top)
    mx = top[0]["valor_em_risco"] or 1
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Valor em risco por cliente, dos maiores para os menores">' % (W, H)]
    for i, r in enumerate(top):
        y = T + h * i
        cls = {"alto": "b-crit", "medio": "b-aten", "baixo": "b-ok"}[faixa_risco(r["indice"])[0]]
        w = (W - L - 120) * r["valor_em_risco"] / mx
        out.append('<text x="%d" y="%.1f" text-anchor="end">%s</text>' % (L - 8, y + h * 0.55, escape(_curto(r["cliente"]["nome"], 26))))
        out.append('<rect class="%s" x="%d" y="%.1f" width="%.1f" height="%.1f" rx="3"/>' % (cls, L, y + h * 0.2, max(w, 2), h * 0.55))
        out.append('<text class="rot" x="%.1f" y="%.1f">%s · %d%%</text>' % (L + w + 8, y + h * 0.55, reais_est(r["valor_em_risco"]), arred(100 * r["valor_em_risco"] / tot)))
    out.append("</svg>")
    tres = arred(100 * sum(r["valor_em_risco"] for r in top[:3]) / tot)
    return "".join(out), tres


def lista(ref, rs, n_lista, avisos=None):
    for r in rs:
        r["_n_lista"] = n_lista
    maior = max(r["valor_em_risco"] for r in rs) or 1
    topo_atraso = max([1] + [max(statistics.median(v) for v in r["serie"].values()) for r in rs if r["serie"]])
    linhas = []
    for i, r in enumerate(rs, 1):
        c = r["cliente"]
        chave, _ = faixa_risco(r["indice"])
        tem_alerta = 1 if COM_ALERTA & set(r["tags"]) else 0
        linhas.append(
            "<tr data-risco='%s' data-alerta='%d' data-valor='%d' data-indice='%d' data-saldo='%d' data-nome='%s' data-pos='%d'>"
            "<td class='pos' data-l=''>%d</td>"
            "<td data-l=''><span class='nome'><a href='/risco/%d'>%s</a></span><div class='sub-linha'>%s · %s</div><div>%s</div></td>"
            "<td class='n' data-l='Saldo em aberto'>%s<div class='sub-linha'>%d%% do limite</div></td>"
            "<td data-l='Índice de risco'><b>%d</b> %s%s</td>"
            "<td class='n' data-l='Valor em risco'><span class='din'>%s</span><div class='barra'><i style='width:%d%%'></i></div></td>"
            "<td class='n' data-l='Peso no faturamento'>%s%%<div class='sub-linha'>em 12 meses</div></td>"
            "<td data-l='Atraso típico, mês a mês'>%s</td></tr>" % (
                chave, tem_alerta, r["valor_em_risco"], r["indice"], r["saldo"], escape(c["nome"].lower()), i,
                i, c["codigo"], escape(c["nome"]), escape(c["categoria"]), escape(c["regiao"]), _chips(r),
                reais(r["saldo"]), arred(100 * r["ocupacao"]), r["indice"], chip_risco(r["indice"]),
                ' <span class="mut" title="faltou dado em alguma conta; o índice usa só as contas com dado">parcial</span>' if r["parcial"] else "",
                reais_est(r["valor_em_risco"]), round(100 * r["valor_em_risco"] / maior), pct1(100 * r["pct_fat"]), _spark(r, ref, topo_atraso)))
    tot = risco.totais(rs)
    tot_saldo, tot_risco = tot["saldo"], tot["valor_em_risco"]
    pct_risco = arred(100 * tot["pct_em_risco"])
    criticos = sum(1 for r in rs if faixa_risco(r["indice"])[0] == "alto")
    piorando = sum(1 for r in rs if {"piorou", "silencioso", "compra_menos"} & set(r["tags"]))
    parados = sum(1 for r in rs if "parou" in r["tags"])
    stat = lambda v, r_: '<div class="stat"><span class="v">%s</span><span class="r">%s</span></div>' % (v, r_)
    painel = """<section class="painel vidro brilho" style="grid-template-columns:1fr" aria-label="Resumo do risco"><div class="stats" style="border-top:0;padding-top:0">%s%s%s%s</div></section>""" % (
        stat("%d" % criticos, "cliente de risco alto" if criticos == 1 else "clientes de risco alto"),
        stat(reais_est(tot_risco), "em risco, de %s em aberto (%d%%)" % (reais_est(tot_saldo), pct_risco)),
        stat("%d" % piorando, "cliente piorando ou comprando menos" if piorando == 1 else "clientes piorando ou comprando menos"),
        stat("%d" % parados, "cliente parou de comprar" if parados == 1 else "clientes pararam de comprar"))
    barras, tres = _grafico_concentracao(rs)
    graficos = """<div class="graficos2">
<div class="cx vidro"><h3>Quem deve muito e quem está arriscado</h3><p class="por">Mostra os dois de uma vez: olhe o canto de cima à direita.</p>%s</div>
<div class="cx vidro"><h3>Onde está o valor em risco</h3><p class="por">Os três maiores concentram %d%% do total.</p>%s</div></div>""" % (_grafico_bolhas(rs), tres, barras)
    casos = "".join(
        '<div class="caso k-%s"><span class="rot">%s</span><span class="tx"><b><a href="/risco/%d">%s</a></b> %s</span></div>' % (
            a["tipo"], escape(a["rotulo"]), a["codigo"], escape(a["nome"]), escape(a["curto"])) for a in risco.achados(rs))
    achados = ('<section class="vidro" style="margin-top:.9rem;padding:.7rem 1.1rem"><span class="eyebrow">Onde a lista de vencidos engana ou esconde (%d casos)</span>%s</section>'
               % (len(risco.achados(rs)), casos))
    quant = {k: sum(1 for r in rs if faixa_risco(r["indice"])[0] == k) for k in ("alto", "medio", "baixo")}
    filtros = ('<button type="button" data-filtro="todos" aria-pressed="true">Todos<span class="q">%d</span></button>'
               '<button type="button" data-filtro="alto" aria-pressed="false">Risco alto<span class="q">%d</span></button>'
               '<button type="button" data-filtro="medio" aria-pressed="false">Risco médio<span class="q">%d</span></button>'
               '<button type="button" data-filtro="alerta" aria-pressed="false">Com alerta<span class="q">%d</span></button>' % (
                   len(rs), quant["alto"], quant["medio"], sum(1 for r in rs if COM_ALERTA & set(r["tags"]))))
    ferramentas = ("""<div class="ferramentas" role="search"><h2>Os %d clientes</h2><label class="busca"><span class="sr">Buscar cliente</span>%s<input type="search" id="busca" placeholder="Buscar cliente" autocomplete="off"></label>
<div class="filtros" role="group" aria-label="Filtrar">%s</div>
<label class="ordem">Ordem <select id="ordem"><option value="valor">Valor em risco</option><option value="indice">Índice de risco</option>
<option value="saldo">Saldo em aberto</option><option value="nome">Nome</option></select></label><span class="contagem" id="contagem" aria-live="polite"></span></div>""" % (len(rs), LUPA, filtros))
    corpo = """<h1 class="sr">Risco por cliente</h1>%s%s%s%s%s
<div class="tabela-wrap vidro"><table class="tabela risco cartoes" id="tabela-risco"><thead><tr><th>#</th><th>Cliente</th><th class="n">Saldo em aberto</th><th>Índice (0–100)</th><th class="n">Valor em risco</th><th class="n">Peso no faturamento</th><th>Atraso típico, mês a mês</th></tr></thead>
<tbody>%s</tbody></table></div>
<p class="nenhum vidro escondido" id="vazio">Nenhum cliente combina com a busca ou com o filtro.</p>
<details class="dobra vidro"><summary>Os dois achados por extenso</summary><div class="corpo">%s</div></details>
<details class="dobra vidro" style="margin-top:.6rem"><summary>Como ler esta tela</summary><div class="corpo">
<p>Posição em %s · ordenado por valor em risco (saldo em aberto × índice de risco), não pelo índice. Clique no cliente para ver a ficha: fatores do índice, gráfico de pagamento e alerta. O índice soma seis fatores, cada um com peso e frase própria; quando falta histórico para um fator, ele sai da conta e o índice é marcado como "parcial". O peso no faturamento é informação de contexto e não entra no índice, porque o saldo em aberto, que já multiplica o risco, carrega o tamanho do cliente.</p>
<p>A linha miúda de cada cliente mostra o atraso típico no pagamento, mês a mês, nos últimos 12 meses: subindo quer dizer pagando cada vez mais tarde. Só aparece quando a linha tem forma; quem sempre atrasou os mesmos dias aparece como "estável".</p>
<p>Saldo total em aberto %s, valor em risco %s.</p></div></details>""" % (
        caixa_avisos(avisos), painel, graficos, achados, ferramentas, "\n".join(linhas), _casos(ref, rs, n_lista), _d(ref), reais_est(tot_saldo), reais_est(tot_risco))
    return _casca("Risco por cliente", corpo, "risco", ref)


# ------------------------------------------------------------------ ficha

def _indices_rotulados(eixo):
    """Meses que levam rótulo no eixo: os inícios de trimestre, e o primeiro mês só se não ficar colado no seguinte."""
    trimestres = [i for i, (_, m) in enumerate(eixo) if m in (1, 4, 7, 10)]
    if 0 not in trimestres and (not trimestres or trimestres[0] >= 2):
        trimestres.insert(0, 0)
    return trimestres


def _grafico_pagamento(r, ref):
    p = r["pag"]
    if not p["ok"]:
        return '<p class="mut">Sem gráfico: %s.</p>' % escape(p["motivo"])
    serie = r["serie"]
    meses = sorted(set(serie) | set(r["serie_aberta"]))
    k0, k1 = min(meses), (ref.year, ref.month)
    eixo = []
    y, m = k0
    while (y, m) <= k1:
        eixo.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    W, H, L, R_, T, B = 760, 290, 50, 12, 14, 40
    w = (W - L - R_) / len(eixo)
    med = {k: statistics.median(v) for k, v in serie.items()}
    banda = (p["p10"], p["p90"])  # o mesmo "80% dos pagamentos" do quadro da ficha e dos textos
    vals = list(med.values()) + [banda[1]]
    abertos = r["serie_aberta"]
    topo_normal = max(vals)
    cap = None
    if abertos and max(abertos.values()) > 1.7 * topo_normal:
        cap = round(1.7 * topo_normal)
    ymax = max(cap or max(vals + list(abertos.values())), 5)
    ymin = min(0, min(vals))
    passo = next(s for s in (5, 10, 20, 25, 50, 100) if (ymax - ymin) / s <= 6)
    ymax = -(-ymax // passo) * passo
    ymin = -(-ymin // passo) * passo if ymin >= 0 else -((-ymin + passo - 1) // passo) * passo
    ys = lambda v: T + (H - T - B) * (1 - (v - ymin) / (ymax - ymin))
    xs = lambda i: L + w * (i + .5)
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Dias de atraso no pagamento, mês a mês">' % (W, H)]
    v = ymin
    while v <= ymax:
        out.append('<line class="grid" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/><text x="%d" y="%.1f" text-anchor="end">%d</text>'
                   % (L, W - R_, ys(v), ys(v), L - 6, ys(v) + 4, v))
        v += passo
    out.append('<text x="12" y="%d" transform="rotate(-90 12 %d)" text-anchor="middle">dias depois do vencimento</text>' % (
        (T + H - B) // 2, (T + H - B) // 2))
    saz = set(p["sazonais"])
    for i, (a, mm) in enumerate(eixo):
        if mm in saz:
            out.append('<rect class="saz" x="%.1f" y="%d" width="%.1f" height="%d"><title>mês sazonal: %s</title></rect>'
                       % (L + w * i, T, w, H - T - B, MESES_NOME[mm - 1]))
    if r["trecho"]:
        a, b = r["trecho"]
        i0, i1 = eixo.index(a), eixo.index(b)
        out.append('<rect class="fora" x="%.1f" y="%d" width="%.1f" height="%d"/>' % (L + w * i0, T, w * (i1 - i0 + 1), H - T - B))
        out.append('<text x="%.1f" y="%d" text-anchor="middle" style="fill:#ff7590;font-weight:700">fora do padrão</text>' % (
            L + w * (i0 + (i1 - i0 + 1) / 2), T + 12))
    out.append('<rect class="band" x="%d" y="%.1f" width="%d" height="%.1f"><title>padrão histórico: 80%% dos pagamentos entre %d e %d dias</title></rect>'
               % (L, ys(banda[1]), W - L - R_, ys(banda[0]) - ys(banda[1]), arred(banda[0]), arred(banda[1])))
    mediana_base = p["mediana"]  # o "atraso típico" que a ficha escreve
    out.append('<line class="med" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>' % (L, W - R_, ys(mediana_base), ys(mediana_base)))
    pts = [(i, med[k]) for i, k in enumerate(eixo) if k in med]
    seg, segs = [], []
    for i, vv in pts:  # a linha só liga meses consecutivos com dado
        if seg and i != seg[-1][0] + 1:
            segs.append(seg)
            seg = []
        seg.append((i, vv))
    if seg:
        segs.append(seg)
    for s in segs:
        if len(s) > 1:
            out.append('<polyline class="ln" points="%s"/>' % " ".join("%.1f,%.1f" % (xs(i), ys(vv)) for i, vv in s))
    for i, vv in pts:
        k = eixo[i]
        out.append('<circle class="pt" cx="%.1f" cy="%.1f" r="3"><title>%s/%d: atraso típico de %s em %d título%s</title></circle>' % (
            xs(i), ys(vv), MESES_ABREV[k[1] - 1], k[0], _dias(vv), len(serie[k]), "" if len(serie[k]) == 1 else "s"))
    for i, k in enumerate(eixo):
        if k in abertos:
            d = abertos[k]
            y = ys(min(d, ymax))
            out.append('<circle class="ab" cx="%.1f" cy="%.1f" r="5"><title>%s/%d: título ainda em aberto, %s de atraso hoje</title></circle>'
                       % (xs(i), y, MESES_ABREV[k[1] - 1], k[0], _dias(d)))
    for i in _indices_rotulados(eixo):
        a, mm = eixo[i]
        out.append('<text x="%.1f" y="%d" text-anchor="middle">%s/%02d</text>' % (xs(i), H - B + 16, MESES_ABREV[mm - 1], a % 100))
    out.append("</svg>")
    leg = ('<div class="leg"><span><i class="sw" style="background:rgba(122,234,255,.4)"></i>padrão histórico (80%% dos pagamentos entre %d e %d dias)</span>'
           '<span><i class="sw" style="background:rgba(255,201,102,.55)"></i>mês sazonal</span>'
           '<span><i class="sw" style="background:rgba(255,117,144,.5)"></i>fora do padrão</span>'
           '<span><i class="sw" style="border:2px solid #ff7590;border-radius:50%%;height:.6rem;width:.6rem"></i>título em aberto (atraso de hoje)</span>'
           '</div>' % (arred(banda[0]), arred(banda[1])))
    acima = sorted((d for d in abertos.values() if d > ymax), reverse=True)
    if acima:  # marcadores que passam do eixo ficam no topo; os valores reais vão escritos aqui
        leg += '<div class="leg">Passam do limite do gráfico (marcados no topo): %s em aberto há %s.</div>' % (
            "títulos" if len(acima) > 1 else "um título", " e ".join(_dias(d) for d in acima) if len(acima) < 3 else
            ", ".join(_dias(d) for d in acima[:-1]) + " e " + _dias(acima[-1]))
    return '<div class="grafico vidro"><div class="rolagem">%s</div>%s</div>' % ("".join(out), leg)


def _grafico_compras(r, ref):
    cm = r["compras_mes"]
    k0, k1 = min(cm), (ref.year, ref.month)
    eixo = []
    y, m = k0
    while (y, m) <= k1:
        eixo.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    W, H, L, B, T = 560, 250, 50, 30, 14
    w = (W - L - 12) / len(eixo)
    mx = max(cm.values())
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Compras por mês">' % (W, H)]
    out.append('<text x="%d" y="%d" text-anchor="end">%s</text>' % (L - 4, T + 8, "%d mil" % round(mx / 100000)))
    for i, k in enumerate(eixo):
        v = cm.get(k, 0)
        h = (H - T - B) * v / mx
        out.append('<rect class="bl" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2"><title>%s/%d: %s%s</title></rect>' % (
            L + w * i + 2, H - B - h, w - 4, h, MESES_ABREV[k[1] - 1], k[0], reais(v),
            " (mês em andamento)" if k == (ref.year, ref.month) else ""))
    for i in _indices_rotulados(eixo):
        k = eixo[i]
        out.append('<text x="%.1f" y="%d" text-anchor="middle">%s/%02d</text>' % (L + w * (i + .5), H - 10, MESES_ABREV[k[1] - 1], k[0] % 100))
    out.append("</svg>")
    return ('<div class="grafico vidro"><div class="rolagem">%s</div><div class="leg">Compras por mês de emissão. O último mês está incompleto (base até %s).</div></div>'
            % ("".join(out), _d(ref)))


def alerta_curto(r):
    """Do alerta por extenso (risco.alerta), a primeira frase e o "o que fazer". Só fatia o texto que já existe, não escreve fato novo."""
    texto = r["alerta"]
    primeira = re.split(r"(?<=[a-z0-9%)])\.\s", texto, maxsplit=1)[0].rstrip(".") + "."
    fazer = ""
    mf = re.search(r"O que fazer: (.*?)(?: Atenção:|$)", texto)
    if mf:
        fazer = mf.group(1).strip()
    ma = re.search(r"Atenção:.*?\.\s(Ligar agora[^.]*\.)", texto)
    if ma:
        fazer = (fazer + " " + ma.group(1)).strip()
    return primeira, fazer


def ficha(ref, r):
    c, p = r["cliente"], r["pag"]
    chave, _ = faixa_risco(r["indice"])
    fat_rows = "".join(
        "<div class='fator'><span class='nm'>%s</span><span class='pts'>%s<div class='barra'><i style='width:%d%%'></i></div></span><span class='tx'>%s</span></div>" % (
            escape(f["nome"]), ("%.0f de %d" % (f["pontos"], f["peso"])) if f["pontos"] is not None else "fora (peso %d)" % f["peso"],
            round(100 * f["pontos"] / f["peso"]) if f["pontos"] is not None and f["peso"] else 0, envolve_dinheiro(escape(f["frase"])))
        for f in r["fatores"])
    usados = r["peso_usado"]
    parcial = ('<p class="mut">Índice parcial: faltou dado em alguma conta (ver acima o que faltou), que ficou de fora; o total é proporcional aos %d pontos de peso com dado.</p>'
               % usados) if r["parcial"] else ""
    stats = [("Saldo em aberto", reais_est(r["saldo"])), ("Valor em risco", reais_est(r["valor_em_risco"])),
             ("Faturamento 12 meses", "%s (%s%% da carteira)" % (reais_est(r["fat12"]), pct1(100 * r["pct_fat"]))),
             ("Limite ocupado", "%d%% de %s" % (round(100 * r["ocupacao"]), reais_est(c["limite"]))),
             ("Último pedido", "há %s (%s)" % (_dias(r["compras"]["dias_sem_comprar"]), _d(r["ultima_compra"]))),
             ("Prazo contratado", "%d dias" % c["prazo_dias"])]
    if p["ok"]:
        stats += [("Paga, em geral, com", "%s de atraso (o típico)" % _dias(p["mediana"])),
                  ("80% dos pagamentos", "entre %d e %d dias" % (arred(p["p10"]), arred(p["p90"]))),
                  ("Maior atraso", _dias(p["maximo"]))]
    if p.get("sazonais"):
        stats.append(("Meses sazonais", ", ".join(MESES_NOME[m - 1] for m in p["sazonais"])))
    cards = "".join('<div class="numero vidro"><span class="r">%s</span><b class="v">%s</b></div>' % (
        escape(a), envolve_dinheiro(escape(b))) for a, b in stats)
    hist = "".join(
        "<tr><td>%s</td><td>%s</td><td class='n'>%s</td><td>%s</td><td>%s</td><td class='n'>%s</td></tr>" % (
            escape(t["numero"]), _d(t["emissao"]), reais(t["valor"]), _d(t["vencimento"]),
            _d(t["pagamento"]) if t["pagamento"] else "em aberto",
            ("%d" % (t["pagamento"] - t["vencimento"]).days) if t["pagamento"]
            else ("%d (hoje)" % (ref - t["vencimento"]).days if t["vencimento"] < ref else "a vencer"))
        for t in sorted(r["titulos"], key=lambda t: t["vencimento"], reverse=True))
    primeira, fazer = alerta_curto(r)
    corpo = """<nav class="migalha" aria-label="Você está aqui"><a href="/risco">%s Risco por cliente</a></nav>
<section class="ficha-topo vidro brilho">
<div class="ficha-id"><span class="eyebrow">%s · %s · cliente desde %s · posição em %s</span>
<h1 class="nomao">%s</h1><div class="tags">%s</div>
<div class="alerta-curto"><p class="o-que">%s</p>%s</div>
<details class="mais"><summary>Ler o alerta completo</summary><div class="detalhe"><p><b>Alerta.</b> %s</p></div></details></div>
<div class="indice risco-%s ind-box"><span class="n">%d<small> / 100</small></span>
<div class="par"><span class="eyebrow">índice de risco</span>%s
<div class="lin"><span>Valor em risco</span><b>%s</b></div><div class="lin"><span>Saldo em aberto</span><b>%s</b></div></div></div>
</section>
<div class="duas"><section class="secao"><h2>Em quantos dias pagou, mês a mês</h2>
%s<p class="nota2">Cada ponto é o atraso típico dos títulos que venceram no mês: mostra, num olhar, se ele está pagando cada vez mais tarde.</p></section>
<section class="secao"><h2>Compras</h2>%s</section></div>
<details class="dobra vidro"><summary>Números da ficha</summary><div class="corpo"><div class="numeros">%s</div></div></details>
<details class="dobra vidro" style="margin-top:.6rem"><summary>Como o índice foi formado</summary><div class="corpo"><div class="fatores">%s</div>%s</div></details>
<details class="dobra vidro" style="margin-top:.6rem"><summary>Histórico completo (%s)</summary><div class="corpo"><div class="tabela-wrap"><table class="tabela"><thead><tr><th>Título</th><th>Emissão</th><th class="n">Valor</th><th>Vencimento</th><th>Pagamento</th><th class="n">Dias de atraso</th></tr></thead><tbody>%s</tbody></table></div></div></details>
""" % (VOLTAR, escape(c["categoria"]), escape(c["regiao"]), _d(c.get("desde", r["primeira_compra"])), _d(ref), escape(c["nome"]),
       _chips(r), envolve_dinheiro(escape(primeira)),
       ('<p class="fazer"><b>O que fazer:</b> %s</p>' % envolve_dinheiro(escape(fazer))) if fazer else "",
       envolve_dinheiro(escape(r["alerta"])), chave, r["indice"], chip_risco(r["indice"]), reais_est(r["valor_em_risco"]), reais_est(r["saldo"]),
       _grafico_pagamento(r, ref), _grafico_compras(r, ref), cards, fat_rows, parcial, pl(len(r["titulos"]), "título", "títulos"), hist)
    return _casca(c["nome"], corpo, "risco", ref)
