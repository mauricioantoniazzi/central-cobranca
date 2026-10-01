"""Varredura de escrita: concordância, pontuação, centavo em estimativa, jargão, marcas sem preencher, em TODO texto que
a Central mostra (as telas e os textos de cobrança de todos os tons, canais e clientes).
Uso: python escrita.py PORTA   (com a Central no ar). Sai com código 1 se achar algo."""
import html as H
import json
import re
import sys
import urllib.parse
import urllib.request

APP = "http://127.0.0.1:%s" % (sys.argv[1] if len(sys.argv) > 1 else "8200")
NBSP = chr(160)


def pega(c):
    return urllib.request.urlopen(APP + c).read().decode("utf-8")


def texto(h):
    h = re.sub(r"<style.*?</style>|<script.*?</script>|<svg.*?</svg>", "", h, flags=re.S)
    h = re.sub(r'<span class="c" aria-hidden="true">.*?</span>', "", h)  # rótulo curto da doca no celular: repete o nome inteiro, nunca aparece junto
    h = re.sub(r"<(br|/p|/li|/tr|/h[1-6]|/div|/section|/table|/td|/th)[^>]*>", chr(10), h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = H.unescape(h)
    h = re.sub(r"[ \t]+", " ", h)            # só espaço comum: o NBSP (entre R$ e o valor) precisa sobreviver
    return re.sub(r" ([,.;:!?])", r"\1", h)  # espaço que as tags inline deixam antes de pontuação é artefato da extração


paginas = ["/", "/regua", "/cobrancas", "/risco", "/previsao", "/relatorio"] + ["/risco/%d" % i for i in range(1, 13)]
corpus = {p: texto(pega(p)) for p in paginas}
tons = ["lembrete_leve", "lembrete_prazo", "primeiro_aviso", "grande_primeira", "conversa_piora", "comercial", "objetiva", "formal"]
regua_html = pega("/regua")
n_paineis = 0
for cod in re.findall(r'<section class="regua-painel[^>]*data-cod="(\d+)"', regua_html):
    n_paineis += 1
    sec = re.search(r'<section class="regua-painel[^>]*data-cod="%s".*?</section>' % cod, regua_html, flags=re.S).group(0)
    tits = re.findall(r'class="tit" value="([^"]+)"', sec)
    for tom in tons:
        for canal in ("WhatsApp", "E-mail", "Telefone"):
            q = urllib.parse.urlencode({"cliente": cod, "tom": tom, "canal": canal, "titulos": ",".join(tits)})
            j = json.loads(pega("/regua/texto?" + q))
            corpus["texto[%s|%s|%s]" % (cod, tom, canal)] = j["texto"]
            corpus["porque[%s|%s]" % (cod, tom)] = texto(j["porque_html"])

# trava contra varredura que "não vê" nada: cada cliente da Régua tem de ter gerado 8 tons x 3 canais
esperados = 24 * n_paineis
gerados = sum(1 for k in corpus if k.startswith("texto["))
if gerados != esperados or (n_paineis == 0 and "Nenhum cliente tem título vencido" not in regua_html):
    print("FALHA: a varredura esperava %d textos de cobrança (8 tons x 3 canais x %d clientes) e gerou %d: a marcação da Régua mudou?" % (esperados, n_paineis, gerados))
    sys.exit(1)
regras = [
    ("1 + substantivo no plural", r"(?<![\d,.])1 (títulos|dias|contatos|clientes|registros|pagamentos|meses|semanas|horas|vezes)\b"),
    ("0/2+ + substantivo no singular", r"\b(?:0|[2-9]|\d\d+) (título|dia|contato|cliente|registro|pagamento|mês|semana|hora)(?![a-zê])"),
    ("'os 1' / 'as 1'", r"\b(os|as) 1 "),
    ("espaço antes de pontuação", r" [,.;:!?](?!\d)"),
    ("duas pontuações", r"[,;:]\s*[,;:.]|\.\."),
    ("centavo em estimativa (R$ x,yy com yy!=00)", r"R\$" + NBSP + r"[\d.]+,(?!00)\d\d"),
    ("decimal com ponto", r"\b\d+\.\d(?!\d)(?=\s*(%|vezes|dias))"),
    ("marca sem preencher", r"\bNone\b|\bnan\b|[{}]|%[sd]\b"),
    ("R$ com espaço comum (pode quebrar linha)", r"R\$ \d"),
    ("jargão", r"\b(mediana|percentil|quantil|sigma|desvio|outlier|regime|heur[ií]stic|censur|p10|p90|MAD|IQR|baseline|DSO|score|ticket)\b"),
    ("primeira pessoa em tela de análise", r"\b(premissas minhas|meu cálculo|eu acho)\b"),
    ("nome de arquivo técnico na tela", r"\b\w+\.py\b"),
    ("mesma palavra repetida", r"\b(\w{3,}) \1\b"),
]
achados = {}
for pag, t in corpus.items():
    for nome, rx in regras:
        for m in re.finditer(rx, t):
            trecho = t[max(0, m.start() - 35): m.end() + 35].replace(chr(10), " ")
            achados.setdefault((nome, m.group(0).lower()), []).append((pag, trecho))
for (nome, g), ocorr in sorted(achados.items()):
    pags = sorted({p for p, _ in ocorr})
    print("[%s] %r  x%d  em %s\n      ex: ...%s..." % (nome, g, len(ocorr), ", ".join(pags[:4]) + ("..." if len(pags) > 4 else ""), ocorr[0][1]))
print("varridos %d textos; achados: %d" % (len(corpus), len(achados)))
sys.exit(1 if achados else 0)
