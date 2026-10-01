"""Abre a Central num Edge de verdade (sem janela), tira foto de cada tela e mede o que está desenhado.

Uso (com a Central já no ar, de preferência numa porta de teste e com hora fixa):
    set PORTA=8250 & set SEM_NAVEGADOR=1 & set CENTRAL_HORA=10:00 & python central.py
    python ferramentas/navegador/olhar_telas.py 8250 [larguras]      larguras: ex. 1280,390 (padrão) ou 1280,768,390,360,320

Saída: ferramentas/navegador/saida/fotos_<largura>/<tela>.png e, no terminal, o que a sonda achou por tela.
A sonda (sonda.js) procura: página com rolagem horizontal, elemento fora da tela, texto cortado, botão que quebrou de linha,
coluna espremida, rótulo de gráfico por cima de outro ou fora do quadro. O apertado.js procura texto colado na borda de quadro.
Falsos positivos conhecidos: tabelas dentro de ".tbl" rolam de propósito (o apertado.js mostra esses textos "fora do quadro").
Exige o Microsoft Edge instalado (caminho em cdp.py) e Python; não instala nada.
"""
import itertools
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from cdp import Browser  # noqa: E402

app = sys.argv[1]
larguras = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "1280,390").split(",")]
SONDA = open(os.path.join(AQUI, "sonda.js"), encoding="utf-8").read()
APERTADO = open(os.path.join(AQUI, "apertado.js"), encoding="utf-8").read()
paginas = ["/", "/regua", "/cobrancas", "/risco", "/previsao", "/relatorio"]
if len(sys.argv) > 3 and sys.argv[3] == "--fichas":
    paginas += ["/risco/%d" % i for i in range(1, 13)]
else:
    paginas += ["/risco/3", "/risco/5"]
porta = itertools.count(9700)
for larg in larguras:
    pasta = os.path.join(AQUI, "saida", "fotos_%d" % larg)
    os.makedirs(pasta, exist_ok=True)
    b = Browser(porta=next(porta), largura=larg, altura=900, movel=larg < 500)
    try:
        for p in paginas:
            b.ir("http://127.0.0.1:%s%s" % (app, p))
            nome = p.strip("/").replace("/", "_") or "hoje"
            w, h = b.foto(os.path.join(pasta, nome + ".png"))
            r = json.loads(b.js(SONDA))
            ap = [x for x in json.loads(b.js(APERTADO)) if not x["cartao"].startswith(("DIV.tbl", "SECTION.lin"))]
            print("%4d %-11s altura=%5d rolagem_horizontal=%s problemas=%d apertados=%d" % (
                larg, p, h, "SIM" if r["scrollWidth"] > r["largura"] + 1 else "não", len(r["problemas"]), len(ap)))
            vistos = set()
            for pr in r["problemas"] + [{"tipo": "texto-colado-na-borda", "el": a["cartao"], "detalhe": "%r esq=%s dir=%s" % (a["texto"], a["esq"], a["dir"])} for a in ap]:
                k = (pr["tipo"], pr["el"][:50])
                if k not in vistos:
                    vistos.add(k)
                    print("        -", pr["tipo"], "|", pr["el"][:70], "|", pr["detalhe"])
    finally:
        b.fechar()
print("fotos em", os.path.join(AQUI, "saida"))
