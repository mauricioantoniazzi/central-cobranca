"""Foto rápida das telas: python fotos.py PORTA LARGURAxALTURA ROTAS [dobra|pagina] [pasta]
ROTAS separadas por vírgula (ex.: /,/regua,/risco/3). 'dobra' = só o que cabe na tela sem rolar (o que o telão mostra); 'pagina' = a página inteira.
Também imprime a altura da página e a medida do 1º cartão de cliente da Hoje, para conferir "cabe sem rolar"."""
import json
import os
import sys
import base64

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from cdp import Browser  # noqa: E402

porta, dim, rotas = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
modo = sys.argv[4] if len(sys.argv) > 4 else "dobra"
saida = sys.argv[5] if len(sys.argv) > 5 else os.path.join(os.environ["TEMP"], "fotos_central")
os.makedirs(saida, exist_ok=True)
larg, alt = [int(x) for x in dim.split("x")]
b = Browser(porta=9900 + larg % 97, largura=larg, altura=alt, movel=larg < 500)
try:
    for r in rotas:
        b.ir("http://127.0.0.1:%s%s" % (porta, r), espera=1.6)
        nome = (r.strip("/").replace("/", "_") or "hoje") + "_%dx%d_%s.png" % (larg, alt, modo)
        if modo == "pagina":
            w, h = b.foto(os.path.join(saida, nome))
        else:
            res = b.cmd("Page.captureScreenshot", format="png", clip={"x": 0, "y": 0, "width": larg, "height": alt, "scale": 1})
            open(os.path.join(saida, nome), "wb").write(base64.b64decode(res["data"]))
            h = b.js("document.documentElement.scrollHeight")
        info = b.js("""(function(){var c=document.querySelector('.cartao');var o={h:document.documentElement.scrollHeight,sw:document.documentElement.scrollWidth};
          if(c){var q=c.getBoundingClientRect();o.cartao1_fim=Math.round(q.bottom)}return JSON.stringify(o)})()""")
        print(nome, info)
finally:
    b.fechar()
print(saida)
