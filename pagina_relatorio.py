"""Tela do Relatório da semana: três números no alto, o texto da diretoria numa folha centralizada (todo valor em reais na cor do dinheiro) e o download em Word."""
from html import escape

from frases import envolve_dinheiro, reais_est
from visual import _d, pagina as _casca


def _din(texto):
    return envolve_dinheiro(escape(texto))


def pagina(ref, blocos, painel=None, prev=None):
    partes = []
    for b in blocos:
        t = b[0]
        if t == "titulo":
            continue
        if t == "sub":
            partes.append('<p class="mut" style="margin-top:0">%s</p>' % _din(b[1]))
        elif t == "secao":
            partes.append("<h2>%s</h2>" % _din(b[1]))
        elif t == "par":
            partes.append("<p>%s</p>" % _din(b[1]))
        elif t == "decisao":
            partes.append('<p class="decisao"><b>%s. %s</b> %s</p>' % (b[1], _din(b[2]), _din(b[3])))
    resumo = ""
    if painel is not None and prev is not None:
        R = painel["resumo"]
        st = lambda v, r: '<div class="stat"><span class="v">%s</span><span class="r">%s</span></div>' % (v, r)
        resumo = '<section class="painel vidro brilho rel-resumo" style="grid-template-columns:repeat(3,minmax(0,1fr))" aria-label="A semana em três números">%s%s%s</section>' % (
            st(reais_est(R["entrou_7d"]), "entrou na semana"), st(reais_est(R["vencido"]), "está vencido"),
            st(reais_est(prev["total_esp"]), "esperado nas próximas quatro semanas"))
    corpo = """<h1 class="sr">Relatório da semana</h1><div class="rel-wrap">%s
<div class="rel-topo"><p class="sub" style="flex:1 1 20rem;font-size:.88rem">Texto para a diretoria, em quatro minutos de leitura. Não refaz nenhuma conta: lê os mesmos números das telas Hoje, Risco por cliente e Previsão de caixa, na posição de %s.</p>
<a class="btn principal" href="/relatorio.docx">Baixar o relatório em Word (.docx)</a></div>
<article class="papel vidro">%s</article></div>""" % (resumo, _d(ref), "\n".join(partes))
    return _casca("Relatório da semana", corpo, "relatorio", ref)
