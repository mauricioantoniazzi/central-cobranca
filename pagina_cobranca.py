"""Telas "Régua de cobrança" (lista de clientes de um lado, o texto de UM cliente do outro) e "Cobranças feitas"."""
from html import escape

import redacao
import regua
import registro
from frases import _tempo, pl, arred, envolve_dinheiro, faixa_risco, reais, reais_est, ultimo_contato
from motor import HORAS_SEM_INSISTIR
from pagina import LUPA
from visual import _d, caixa_avisos, chip_risco, pagina as _casca


def porque_html(ref, chave, sugerido, razoes_sugerido, razoes_chave=None):
    """Bloco 'por que este tom', fechado (só a primeira linha aparece). Se o tom foi trocado à mão, diz isso e mostra o que o sugerido era."""
    nome, desc = regua.TONS[chave]
    itens = "".join("<li>%s</li>" % envolve_dinheiro(escape(x)) for x in razoes_sugerido)
    if chave == sugerido:
        return ("<details class='porque-d'><summary><b>Tom: %s</b> (escolhido pelos números) · por quê</summary><ul>%s</ul></details>"
                % (escape(nome), itens))
    return ("<details class='porque-d' open><summary><span class='troca'>Você trocou o tom à mão.</span> <b>Tom: %s.</b> · por quê</summary>%s"
            "<p>Os números sugeriam <b>%s</b>:</p><ul>%s</ul></details>") % (escape(nome), escape(desc), escape(regua.nome_tom(sugerido)), itens)


def texto_da_cobranca(ref, painel, cod, chave, canal, titulos, assinatura):
    r = painel["risco_por_cliente"][cod]
    contatos = regua.contatos_do_cliente(painel["cobrancas"], cod)
    ctx = regua.contexto(ref, r, chave, canal, titulos, contatos, assinatura)
    return redacao.REDATOR.cobranca(ctx), ctx


def _painel(ref, painel, f, assinatura):
    cod = f["cliente"]["codigo"]
    r = painel["risco_por_cliente"][cod]
    contatos = regua.contatos_do_cliente(painel["cobrancas"], cod)
    sug, razoes = regua.escolher(ref, r, contatos)
    titulos = [t["numero"] for t in r["vencidos"]]
    saida, _ = texto_da_cobranca(ref, painel, cod, sug, "WhatsApp", titulos, assinatura)
    opcoes_tom = "".join('<option value="%s"%s>%s%s</option>' % (
        k, " selected" if k == sug else "", escape(v[0]), " (sugerido)" if k == sug else "") for k, v in regua.TONS.items())
    opcoes_canal = "".join('<option value="%s">%s</option>' % (c, c) for c in registro.CANAIS)
    tits = "".join('<label><input type="checkbox" class="tit" value="%s" checked> %s · %s · %d dia%s</label>' % (
        escape(t["numero"]), escape(t["numero"]), reais(t["valor"]), t["dias_atraso"], "" if t["dias_atraso"] == 1 else "s")
        for t in r["vencidos"])
    tag = ('<span class="chip ruim">cobrado nas últimas %dh, desceu na fila</span>' % HORAS_SEM_INSISTIR) if f["cobrado_recente"] else ""
    return """<section class="regua-painel vidro" id="c%d" data-cod="%d" data-nome="%s">
<div class="cab"><h2>%s</h2><span class="din"><span class="valor">%s</span> vencidos</span>%s</div>
<p class="mut">falar com %s · %s</p>
<p class="nota2" style="margin:.1rem 0 .5rem">%s</p>
<div class="porque">%s</div>
<div class="ctl"><div><label class="r">Tom</label><select class="tom">%s</select></div>
<div><label class="r">Canal</label><select class="canal">%s</select></div></div>
<div class="tits">%s</div>
<textarea rows="10" aria-label="Texto da cobrança de %s">%s</textarea>
<p class="nota2">Trocar o tom, o canal ou os títulos reescreve o texto; o que você editar à mão se perde ao trocar. Você copia e envia por conta própria; a Central não manda nada.</p>
<div class="rodape"><button class="btn principal js-copiar" type="button">Copiar texto</button>
<button class="btn suave js-registrar so-operacao" type="button">Registrar que cobrei</button></div>
</section>""" % (
        cod, cod, escape(f["cliente"]["nome"]), escape(f["cliente"]["nome"]), reais(f["vencido"]), tag,
        escape(f["cliente"].get("contato") or "sem contato no cadastro"), escape(f["cliente"]["regiao"]), escape(ultimo_contato(f)),
        porque_html(ref, sug, sug, razoes), opcoes_tom, opcoes_canal, tits, escape(f["cliente"]["nome"]), escape(saida["texto"]))


def regua_pagina(painel, assinatura, registrado=None):
    ref, fila = painel["ref"], painel["fila"]
    itens, paineis = [], []
    for f in fila:
        cod = f["cliente"]["codigo"]
        chave, _ = faixa_risco(f["indice"])
        itens.append(
            '<a class="item" href="#c%d" data-cod="%d" data-risco="%s" data-nome="%s"><span class="p">%d</span>'
            '<span><span class="nm">%s</span><span class="sm" style="display:block">%s · %s</span></span>'
            '<span class="vl">%s</span>%s</a>' % (
                cod, cod, chave, escape(f["cliente"]["nome"].lower()), f["posicao"], escape(f["cliente"]["nome"]),
                "%d título%s" % (f["n"], "" if f["n"] == 1 else "s"), "%d dias" % f["mais_antigo"] if f["mais_antigo"] != 1 else "1 dia",
                reais_est(f["vencido"]), ('<span class="ok" style="color:var(--aten)">cobrado nas últimas 48h</span>' if f["cobrado_recente"] else "")))
        paineis.append(_painel(ref, painel, f, assinatura))
    flash = ""
    if registrado is not None:
        reg = next((c for c in painel["da_central"] if c["id"] == registrado), None)
        if reg:
            pos = next((f["posicao"] for f in fila if f["cliente"]["codigo"] == reg["cliente"]), None)
            nome = next(f["cliente"]["nome"] for f in fila if f["cliente"]["codigo"] == reg["cliente"]) if pos else ""
            flash = ('<div class="flash"><b>Cobrança registrada.</b> %s, %s, %s por %s, %s. %s</div>' % (
                reg["quando"].strftime("%d/%m/%Y às %H:%M"), escape(reg["tom"]), envolve_dinheiro(escape(reais(reg["valor"]))), escape(reg["canal"]),
                ("cliente %s" % escape(nome)) if nome else "", ("Ele desceu para a posição %d da fila de Hoje." % pos) if pos else ""))
    if fila:
        area = """<div class="regua" id="regua">
<div class="regua-lista vidro"><label class="busca" style="max-width:none"><span class="sr">Buscar cliente</span>%s<input type="search" id="busca-regua" placeholder="Buscar cliente" autocomplete="off"></label>
<div class="rolar" id="lista-regua">%s</div></div>
<div class="regua-paineis">%s</div></div>""" % (LUPA, "".join(itens), "".join(paineis))
    else:
        area = '<p class="nenhum vidro">Nenhum cliente tem título vencido na data de referência: não há cobrança a redigir.</p>'
    assin = ("""<details class="dobra vidro" id="assinatura-caixa"><summary>Sua assinatura nos textos</summary><div class="corpo">
<p class="mut">Fica guardada em dados/configuracao.json.</p>
<p><input type="text" id="assinatura" value="%s" placeholder="seu nome" size="28"> <button class="btn so-operacao" id="salvar-assinatura" type="button">Salvar</button> <span id="ass-ok" class="mut"></span></p></div></details>""" % escape(assinatura))
    corpo = """<h1 class="sr">Régua de cobrança</h1>%s%s
%s
%s
<details class="dobra vidro" style="margin-top:.6rem"><summary>Onde ficam os registros e como o tom é escolhido</summary><div class="corpo">
<p>Um texto pronto para cada cliente vencido, na ordem de Hoje. Posição em %s.</p>
<p>O tom é escolhido pelos números; você pode trocá-lo e o texto se reescreve na hora.</p>
<p>O registro de cada cobrança fica em dados/cobrancas_registradas.json, à parte da planilha da empresa (Base_bruta.xlsx), que a Central só lê. A hora do registro segue o relógio da base: a data de referência (%s) com a hora do computador. Veja o que já foi registrado em <a href="/cobrancas">Cobranças feitas</a>.</p></div></details>""" % (
        caixa_avisos(painel.get("avisos")), flash, area, assin, _d(ref), _d(ref))
    return _casca("Régua de cobrança", corpo, "regua", ref)


def historico_pagina(painel, agora):
    ref = painel["ref"]
    todas = sorted(painel["cobrancas"], key=lambda c: c["quando"], reverse=True)
    nomes = {c["codigo"]: c["nome"] for c in (r["cliente"] for r in painel["rs"])}
    n_pl, n_ce = len(painel["da_planilha"]), len(painel["da_central"])
    res = registro.resumo_contatos(painel["cobrancas"], agora)
    linhas = []
    for c in todas:
        origem = ('<span class="chip fonte-central">Registrada na Central</span>' if c.get("origem") == "Central"
                  else '<span class="chip">Planilha da empresa</span>')
        acao = ('<button class="btn suave js-desfazer" type="button" data-id="%d">Desfazer</button>' % c["id"]) if c.get("origem") == "Central" else ""
        linhas.append("<tr><td data-l='Quando'>%s</td><td data-l=''><span class='nome'><a href='/risco/%d'>%s</a></span></td><td data-l='Canal'>%s</td><td data-l='Tom'>%s</td>"
                      "<td class='n' data-l='Valor cobrado'><span class='din'>%s</span></td><td class='n' data-l='Títulos'>%d</td><td data-l=''>%s</td><td data-l=''>%s</td></tr>" % (
                          c["quando"].strftime("%d/%m/%Y %H:%M"), c["cliente"], escape(nomes.get(c["cliente"], "?")), escape(c["canal"]),
                          escape(c["tom"]), reais(c["valor"]), c["n_titulos"], origem, acao))
    ultimo = {}
    for c in sorted(painel["cobrancas"], key=lambda c: c["quando"]):
        ultimo[c["cliente"]] = c
    por_cli = []
    for r in painel["rs"]:
        cod = r["cliente"]["codigo"]
        c = ultimo.get(cod)
        if c:
            horas = max(0.0, (agora - c["quando"]).total_seconds() / 3600)
            quando = "%s (há %s)" % (c["quando"].strftime("%d/%m %H:%M"), _tempo(horas))
            semana = "sim" if horas <= 24 * 7 else "não"
            janela = "sim" if horas < 48 else "não"
            orig = "Central" if c.get("origem") == "Central" else "Planilha"
            det = "%s · %s · %s" % (escape(c["canal"]), escape(c["tom"]), reais(c["valor"]))
        else:
            quando, semana, janela, orig, det = "nunca registrado", "não", "não", "—", "—"
        por_cli.append("<tr><td data-l=''><span class='nome'><a href='/risco/%d'>%s</a></span></td><td data-l='Último contato'>%s</td><td data-l='Canal · tom · valor'>%s</td>"
                       "<td data-l='Falei esta semana'>%s</td><td data-l='Nas últimas 48h'>%s</td><td data-l='Fonte'>%s</td></tr>" % (
                           cod, escape(r["cliente"]["nome"]), quando, det, semana, janela, orig))
    heroi = """<section class="painel vidro brilho" style="grid-template-columns:1fr" aria-label="Resumo dos contatos">
<div class="esq"><span class="eyebrow">contatos de cobrança nos últimos 7 dias</span>
<span class="grande">%d</span>
<p class="apoio">Últimos 7 dias (desde %s): %d contato%s de cobrança, %s cobrados, %d cliente%s. Na planilha da empresa: %s; registradas na Central: %s.</p></div></section>""" % (
        res["n"], _d(res["ini"]), res["n"], "" if res["n"] == 1 else "s", envolve_dinheiro(escape(reais(res["valor"]))), res["n_clientes"],
        "" if res["n_clientes"] == 1 else "s", pl(n_pl, "registro", "registros"), pl(n_ce, "registro", "registros"))
    corpo = """<h1 class="sr">Cobranças feitas</h1>%s%s
<h2 class="eyebrow" style="margin:1.1rem 0 .4rem">Último contato por cliente</h2>
<div class="tabela-wrap vidro"><table class="tabela cartoes"><thead><tr><th>Cliente</th><th>Último contato</th><th>Canal · tom · valor</th><th>Falei esta semana?</th><th>Nas últimas 48h?</th><th>Fonte</th></tr></thead><tbody>%s</tbody></table></div>
<h2 class="eyebrow" style="margin:1.1rem 0 .4rem">Todas as cobranças</h2>
<div class="tabela-wrap vidro"><table class="tabela cartoes"><thead><tr><th>Quando</th><th>Cliente</th><th>Canal</th><th>Tom</th><th class="n">Valor cobrado</th><th class="n">Títulos</th><th>Fonte</th><th></th></tr></thead><tbody>%s</tbody></table></div>
<details class="dobra vidro"><summary>De onde vem cada coisa</summary><div class="corpo"><ul>
<li><b>Planilha da empresa</b> (Base_bruta.xlsx, aba Cobranças): %d registro%s.</li>
<li><b>Registradas na Central</b> (dados/cobrancas_registradas.json): %d registro%s.</li>
<li>A hora de cada registro na Central é a data de referência da base (%s) com a hora do computador.</li>
<li>As duas fontes juntas alimentam a regra das 48 horas da tela Hoje.</li></ul><p>Quem foi cobrado, quando, por qual canal, com qual tom e de quanto. Posição em %s.</p></div></details>""" % (
        caixa_avisos(painel.get("avisos")), heroi, "".join(por_cli), "".join(linhas), n_pl, "" if n_pl == 1 else "s", n_ce,
        "" if n_ce == 1 else "s", _d(ref), _d(ref))
    return _casca("Cobranças feitas", corpo, "cobrancas", ref)
