"""Casca comum das telas (tema "Aurora"): fundo, cabeçalho, doca de navegação, script. Todas as páginas passam por `pagina()`.

Regras do visual estão no topo de estatico/tema.css. Aqui ficam só as peças repetidas: ícones, selo de gravidade, aviso da planilha.
O arquivo único (gerar_arquivo_unico.py) troca o <link> do CSS e o <script> pelos próprios conteúdos embutidos.
"""
from html import escape

from frases import faixa_risco
from navegacao import nav

DEFS = ("""<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>
<linearGradient id="gradAnel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff7590"/><stop offset="1" stop-color="#e04fd3"/></linearGradient>
<linearGradient id="gradSpark" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b4c0ff" stop-opacity=".45"/><stop offset="1" stop-color="#b4c0ff" stop-opacity="0"/></linearGradient>
<linearGradient id="gradBarra" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9a8cff"/><stop offset="1" stop-color="#3cc8f0"/></linearGradient>
<linearGradient id="gradCrit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff7590" stop-opacity=".75"/><stop offset="1" stop-color="#e04fd3" stop-opacity=".45"/></linearGradient>
</defs></svg>""")


def _d(d):
    return d.strftime("%d/%m/%Y")


def pagina(titulo, corpo, ativa, ref=None, classe=""):
    data = ('<div class="data">Base de %s</div>' % _d(ref)) if ref else ""
    return """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>%s — Central de Crédito e Cobrança</title>
<link rel="stylesheet" href="/estatico/tema.css"></head><body data-tela="%s">
<div class="fundo" aria-hidden="true"><i class="a"></i><i class="b"></i><i class="c"></i></div>%s
<aside class="lateral"><div class="marca"><span class="sel"></span><span>Distribuidora Aurora</span></div>%s%s</aside>
<main class="pagina %s" id="conteudo">%s</main>
<div class="toast vidro" id="toast" role="status" aria-live="polite"></div>
<script src="/estatico/app.js" defer></script></body></html>""" % (escape(titulo), ativa, DEFS, nav(ativa), data, classe, corpo)


def caixa_avisos(avisos):
    """Quadro âmbar com o que a validação da planilha achou estranho (vazio quando não há nada)."""
    if not avisos:
        return ""
    return '<div class="avisos"><b>Avisos sobre a planilha</b><ul>%s</ul></div>' % "".join("<li>%s</li>" % escape(a) for a in avisos)


def chip_risco(indice):
    """Selo de gravidade: forma + palavra + cor, nunca só cor. A faixa é a do índice de risco (mesma conta em todas as telas)."""
    k, palavra = faixa_risco(indice)
    return '<span class="chip risco-%s"><i class="f"></i>%s</span>' % (k, palavra)
