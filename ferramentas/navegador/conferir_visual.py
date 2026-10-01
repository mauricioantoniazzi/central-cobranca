"""Conferência VISUAL num Edge de verdade (o que o HTML sozinho não prova). Uso, com a Central de teste no ar (ver reiniciar_teste.sh):
    python conferir_visual.py PORTA [arquivo_unico.html]

Confere, em 1920x1080, 1366x768 e 390 (celular):
  - nenhuma tela com rolagem para o lado, nenhum erro de JavaScript, a sonda (sonda.js) sem achados;
  - Hoje: o painel de abertura, a linha de ferramentas e o começo do 1º cliente aparecem sem rolar (1920x1080 e 1366x768);
  - o número grande cabe na caixa; o menu mostra as 6 telas e acende a atual; as listas de escolha têm fundo escuro e letra clara;
  - usando de verdade: busca e filtro da fila, "já liguei" (e desfazer), escolher cliente na Régua, trocar o tom reescreve o texto, modo telão liga e desliga.
Com o arquivo único, repete o que faz sentido abrindo por file://. Sai com código 1 se algo falhar; as fotos ficam em %TEMP%/fotos_central."""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from cdp import Browser  # noqa: E402

porta = sys.argv[1]
arquivo = sys.argv[2] if len(sys.argv) > 2 else None
SONDA = open(os.path.join(AQUI, "sonda.js"), encoding="utf-8").read()
falhas = []


def ok(cond, msg):
    print(("  ok    " if cond else "  FALHOU ") + msg)
    if not cond:
        falhas.append(msg)


def erros_js(b):
    return [e for e in b.eventos if e.get("method") == "Runtime.exceptionThrown"]


def abrir(b, rota):
    if arquivo:
        b.ir("file:///" + os.path.abspath(arquivo).replace("\\", "/") + "#" + rota, espera=2.6)
    else:
        b.ir("http://127.0.0.1:%s%s" % (porta, rota), espera=2.6)


ROTAS = ["/", "/regua", "/cobrancas", "/risco", "/previsao", "/relatorio", "/risco/3"]
for larg, alt in ((1920, 1080), (1366, 768), (390, 844)):
    b = Browser(porta=9800 + larg % 89 + (50 if arquivo else 0), largura=larg, altura=alt, movel=larg < 500)
    try:
        print("%dx%d" % (larg, alt))
        for r in ROTAS:
            abrir(b, r)
            s = json.loads(b.js(SONDA))
            s["problemas"] = [q for q in s["problemas"] if not q["el"].startswith(("div.fundo", "i.a", "i.b", "i.c", "span.sr", "h1.sr"))
                          and not (r == "/" and q["el"].startswith("span.o-que"))]  # fundo de luz e texto só-leitor-de-tela não contam; o "o que" das descobertas em tela baixa é cortado de propósito (inteiro na tela Risco)
            ok(s["scrollWidth"] <= s["largura"] + 1, "%s: sem rolagem para o lado" % r)
            ok(not s["problemas"], "%s: a sonda não achou texto cortado, botão quebrado nem coisa fora do quadro%s" % (
                r, "" if not s["problemas"] else " — " + "; ".join("%s %s" % (p["tipo"], p["el"][:40]) for p in s["problemas"][:3])))
            ok(b.js("document.querySelectorAll('.menu a').length") == 6 and b.js("document.querySelectorAll('.menu [aria-current=page]').length") == 1,
               "%s: o menu mostra as 6 telas e acende uma" % r)
            sobra = b.js("Array.prototype.some.call(document.querySelectorAll('.grande'),function(e){return e.scrollWidth>e.clientWidth+1})")
            ok(not sobra, "%s: o número grande cabe na caixa" % r)
        ok(not erros_js(b), "nenhum erro de JavaScript nas telas")
        if larg >= 1100:
            abrir(b, "/")
            r = json.loads(b.js("""(function(){var c=document.querySelector('.cartao'),f=document.querySelector('.ferramentas').getBoundingClientRect(),g=document.querySelector('.grande').getBoundingClientRect(),q=c.getBoundingClientRect();
              return JSON.stringify({ferr:f.bottom,vh:innerHeight,grande:g.bottom,topo:q.top,fim:q.bottom})})()"""))
            ok(r["grande"] < r["ferr"] <= r["vh"] and r["topo"] < r["vh"], "Hoje %dx%d: número grande, ferramentas e o começo do 1º cliente aparecem sem rolar (cliente começa em %d de %d)" % (larg, alt, r["topo"], r["vh"]))
            ok(b.js("Array.prototype.every.call(document.querySelectorAll('select'),function(s){var c=getComputedStyle(s),o=getComputedStyle(s.options[0]);return c.colorScheme.indexOf('dark')>=0&&c.backgroundColor!=='rgba(0, 0, 0, 0)'&&o.backgroundColor!=='rgba(0, 0, 0, 0)'&&o.color!==o.backgroundColor})"), "listas de escolha: fundo escuro opaco e letra clara")
            os.makedirs(os.path.join(os.environ["TEMP"], "fotos_central"), exist_ok=True)
    finally:
        b.fechar()

# ------------------------------------------------------------------ usando de verdade (1920x1080)
b = Browser(porta=9790 + (50 if arquivo else 0), largura=1920, altura=1080)
try:
    print("uso")
    abrir(b, "/")
    n = b.js("document.querySelectorAll('.cartao:not(.escondido)').length")
    b.js("var i=document.getElementById('busca');i.value='vila';i.dispatchEvent(new Event('input'))")
    ok(b.js("document.querySelectorAll('.cartao:not(.escondido)').length") == 1, "Hoje: buscar 'vila' deixa só um cliente (de %d)" % n)
    b.js("var i=document.getElementById('busca');i.value='';i.dispatchEvent(new Event('input'))")
    b.js("document.querySelector('[data-filtro=alto]').click()")
    ok(0 < b.js("document.querySelectorAll('.cartao:not(.escondido)').length") < n, "Hoje: 'Só os mais graves' filtra a fila")
    b.js("document.querySelector('[data-filtro=todos]').click()")
    b.js("var s=document.getElementById('ordem');s.value='nome';s.dispatchEvent(new Event('change'))")
    nomes = json.loads(b.js("JSON.stringify(Array.prototype.map.call(document.querySelectorAll('.cartao .nome'),function(e){return e.textContent}))"))
    ok(nomes == sorted(nomes, key=lambda x: x.lower()) or len(nomes) < 2, "Hoje: ordenar por nome reordena a fila")
    b.js("var s=document.getElementById('ordem');s.value='fila';s.dispatchEvent(new Event('change'))")
    primeiro = b.js("document.querySelector('.cartao .nome').textContent")
    b.js("document.querySelector('.cartao .js-liguei').click()")
    import time
    time.sleep(1.2)
    segundo = b.js("document.querySelector('.cartao .nome').textContent")
    ok(primeiro != segundo and b.js("document.getElementById('toast').classList.contains('on')"), "Hoje: 'Já liguei' desce o cliente na fila e avisa com opção de desfazer")
    b.js("document.querySelector('#toast button').click()")
    time.sleep(1.0)
    ok(b.js("document.querySelector('.cartao .nome').textContent") == primeiro, "Hoje: desfazer devolve o cliente ao lugar")
    abrir(b, "/regua")
    ok(b.js("document.querySelectorAll('.regua-painel.ativo').length") == 1, "Régua: um cliente por vez na tela (lista de um lado, texto do outro)")
    b.js("document.querySelectorAll('.item')[1].click()")
    nome_item = b.js("document.querySelectorAll('.item')[1].querySelector('.nm').textContent")
    ok(b.js("document.querySelector('.regua-painel.ativo h2').textContent") == nome_item, "Régua: clicar num cliente da lista mostra o texto dele")
    antes = b.js("document.querySelector('.regua-painel.ativo textarea').value")
    b.js("var s=document.querySelector('.regua-painel.ativo .tom');s.selectedIndex=(s.selectedIndex+1)%s.options.length;s.dispatchEvent(new Event('change',{bubbles:true}))")
    time.sleep(1.0)
    ok(b.js("document.querySelector('.regua-painel.ativo textarea').value") != antes, "Régua: trocar o tom reescreve o texto")
    abrir(b, "/risco")
    b.js("var i=document.getElementById('busca');i.value='zica';i.dispatchEvent(new Event('input'))")
    ok(b.js("document.querySelectorAll('#tabela-risco tbody tr:not(.escondido)').length") == 1, "Risco: buscar 'zica' deixa só um cliente")
    ok(not erros_js(b), "nenhum erro de JavaScript durante o uso")
finally:
    b.fechar()

print()
if falhas:
    print("%d falha(s) na conferência visual." % len(falhas))
    sys.exit(1)
print("Conferência visual: tudo certo.")
