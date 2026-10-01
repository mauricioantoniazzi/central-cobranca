"""Abre o arquivo único via file:// num Edge de verdade e fotografa cada rota. Uso: python fotos_arquivo.py CAMINHO.html LARGURAxALTURA ROTAS"""
import base64, json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from cdp import Browser
arq, dim, rotas = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
larg, alt = [int(x) for x in dim.split("x")]
saida = os.path.join(os.environ["TEMP"], "fotos_arquivo"); os.makedirs(saida, exist_ok=True)
b = Browser(porta=9950 + larg % 37, largura=larg, altura=alt, movel=larg < 500)
url0 = "file:///" + os.path.abspath(arq).replace("\\", "/")
try:
    for r in rotas:
        b.ir(url0 + "#" + r, espera=1.5)
        b.js("location.reload()") if False else None
        nome = (r.strip("/").replace("/", "_") or "hoje") + "_%dx%d.png" % (larg, alt)
        res = b.cmd("Page.captureScreenshot", format="png", clip={"x": 0, "y": 0, "width": larg, "height": alt, "scale": 1})
        open(os.path.join(saida, nome), "wb").write(base64.b64decode(res["data"]))
        info = b.js("JSON.stringify({t:document.title,tela:document.body.dataset.tela,h1:(document.querySelector('h1')||{}).textContent,sw:document.documentElement.scrollWidth,ativo:(document.querySelector('.doca [aria-current]')||{}).textContent})")
        print(r, info)
finally:
    b.fechar()
print(saida)
