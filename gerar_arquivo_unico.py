"""Gera o ARQUIVO ÚNICO da Central: um .html que se abre com dois cliques, sem instalar nada, para mandar a quem não tem a Central.

Uso:  python gerar_arquivo_unico.py            (cria arquivo_unico/Central_AAAA-MM-DD.html)

É um RETRATO da posição da base no momento de gerar: as seis telas, as 12 fichas, todos os textos de cobrança (8 tons x 3 canais por
cliente) e o relatório em Word vão dentro do arquivo, junto com o visual e as fontes. Nada chama a internet nem a Central.
O que muda em relação à versão que roda no computador (e cada item aparece escrito na tela do arquivo):
  - não atualiza sozinho: para ver números novos, gera-se outro arquivo a partir da planilha nova;
  - "Registrar que cobrei", "Desfazer" e "Salvar assinatura" ficam desligados (não há onde gravar); "Já liguei" funciona, mas só é lembrado neste navegador;
  - escolher quais títulos entram no texto fica desligado (o texto usa todos os vencidos do cliente);
  - a hora do relógio da base é a de quando o arquivo foi gerado.
"""
import base64
import json
import os
import re
import sys
from datetime import datetime

PASTA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PASTA)

import pagina
import pagina_cobranca
import pagina_previsao
import pagina_relatorio
import pagina_risco
import previsao
import regua
import registro
import relatorio
import servico
from frases import reais
from relogio import agora

AVISO_GERAL = ("Este arquivo é um retrato da posição de %s, gerado em %s. Ele não se atualiza sozinho: para ver números novos, gere outro arquivo "
               "a partir da planilha nova.")


def href_arquivo(h):
    """Link da versão local -> link do arquivo único (rota por #). '/regua#c3' vira '#/regua/c3'; '/risco/3' vira '#/risco/3'."""
    m = re.match(r"^/regua#c(\d+)$", h)
    if m:
        return "#/regua/c%s" % m.group(1)
    return "#" + h


def _reescreve_links(html):
    def troca(m):
        h = m.group(2)
        if h.startswith("/relatorio.docx"):
            return m.group(0)
        if h.startswith("/") and not h.startswith("/estatico"):
            return "href=%s%s%s" % (m.group(1), href_arquivo(h), m.group(1))
        return m.group(0)
    return re.sub(r"href=(['\"])([^'\"]*)\1", troca, html)


def _tira_operacao(tela, corpo, aviso_extra):
    """Desliga (e diz por quê na tela) o que não funciona sem a Central."""
    corpo = re.sub(r'<button class="btn suave js-desfazer"[^>]*>Desfazer</button>', "", corpo)
    corpo = corpo.replace('<button class="btn suave js-registrar so-operacao" type="button">Registrar que cobrei</button>',
                          '<button class="btn suave desligado" type="button" disabled title="Desligado neste arquivo">Registrar que cobrei</button>'
                          '<span class="nota2">Desligado neste arquivo: não há onde gravar o registro. Na Central instalada ele funciona.</span>')
    if tela == "regua":
        corpo = corpo.replace('<button class="btn so-operacao" id="salvar-assinatura" type="button">Salvar</button>',
                              '<button class="btn desligado" id="salvar-assinatura" type="button" disabled>Salvar</button> '
                              '<span class="mut">Desligado neste arquivo: os textos já estão escritos com a assinatura de quando o arquivo foi gerado.</span>')
        corpo = corpo.replace('<input type="text" id="assinatura"', '<input type="text" id="assinatura" readonly')
    faixa = '<div class="faixa-arquivo">%s</div>' % aviso_extra if aviso_extra else ""
    return faixa + corpo


def gerar():
    p = servico.painel()
    ref, prev = p["ref"], previsao.prever(p["ref"], p["rs"])
    ag = agora(ref)
    assin = registro.assinatura()
    blocos = relatorio.blocos(p, prev, ag)
    docx = base64.b64encode(relatorio.docx_bytes(p, prev, ag)).decode()
    data_txt = ref.strftime("%d/%m/%Y")
    geracao = datetime.now().strftime("%d/%m/%Y às %H:%M")

    paginas = {  # rota -> (tela, html)
        "/": ("hoje", pagina.hoje(p["resumo"], p["fila"], p["avisos"], p["rs"], p["n_lista"])),
        "/regua": ("regua", pagina_cobranca.regua_pagina(p, assin)),
        "/cobrancas": ("cobrancas", pagina_cobranca.historico_pagina(p, ag)),
        "/risco": ("risco", pagina_risco.lista(ref, p["rs"], p["n_lista"], p["avisos"])),
        "/previsao": ("previsao", pagina_previsao.pagina(ref, p["rs"], prev)),
        "/relatorio": ("relatorio", pagina_relatorio.pagina(ref, blocos, p, prev)),
    }
    for r in p["rs"]:
        paginas["/risco/%d" % r["cliente"]["codigo"]] = ("risco", pagina_risco.ficha(ref, r))

    extras = {
        "regua": "Neste arquivo a Régua serve para LER e COPIAR os textos. Trocar o tom e o canal funciona; registrar a cobrança, salvar a assinatura e escolher títulos estão desligados.",
        "hoje": "Neste arquivo, \"Já liguei\" só é lembrado neste navegador (a fila desce, mas nada é gravado na Central).",
        "cobrancas": "Neste arquivo a lista é só para consulta: não dá para registrar nem desfazer cobranças.",
    }
    templates, titulos = [], {}
    for rota, (tela, html) in paginas.items():
        titulo = re.search(r"<title>(.*?)</title>", html, flags=re.S).group(1)
        corpo = re.search(r'<main class="pagina[^"]*" id="conteudo">(.*?)</main>', html, flags=re.S).group(1)
        corpo = _reescreve_links(_tira_operacao(tela, corpo, extras.get(tela, "")))
        if rota == "/relatorio":
            corpo = corpo.replace('href="#/relatorio.docx"', 'href="#"')
            corpo = re.sub(r'<a class="btn principal" href="[^"]*">Baixar o relatório em Word \(\.docx\)</a>',
                           '<a class="btn principal" download="Relatorio_da_semana_%s.docx" href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,%s">Baixar o relatório em Word (.docx)</a>'
                           % (ref.isoformat(), docx), corpo)
        tid = "p" + rota.replace("/", "-") if rota != "/" else "p-hoje"
        titulos[rota] = titulo
        templates.append('<template id="%s" data-tela="%s">%s</template>' % (tid, tela, corpo))

    # textos de cobrança de todos os clientes, tons e canais (todos os títulos vencidos)
    textos = {}
    for f in p["fila"]:
        cod = f["cliente"]["codigo"]
        r = p["risco_por_cliente"][cod]
        sug, razoes = regua.escolher(ref, r, regua.contatos_do_cliente(p["cobrancas"], cod))
        nums = [t["numero"] for t in r["vencidos"]]
        textos[str(cod)] = {}
        for chave in regua.TONS:
            textos[str(cod)][chave] = {}
            for canal in registro.CANAIS:
                saida, _ = pagina_cobranca.texto_da_cobranca(ref, p, cod, chave, canal, nums, assin)
                textos[str(cod)][chave][canal] = {"texto": saida["texto"], "porque": pagina_cobranca.porque_html(ref, chave, sug, razoes)}

    css = open(os.path.join(PASTA, "estatico", "tema.css"), encoding="utf-8").read()
    for nome in ("Inter-latin", "Manrope-latin"):
        b64 = base64.b64encode(open(os.path.join(PASTA, "estatico", "fontes", nome + ".woff2"), "rb").read()).decode()
        css = css.replace("url(/estatico/fontes/%s.woff2)" % nome, "url(data:font/woff2;base64,%s)" % b64)
    js = open(os.path.join(PASTA, "estatico", "app.js"), encoding="utf-8").read()

    # a casca (topo, fundo, doca, aviso) vem de uma página qualquer: é a mesma em todas
    base = paginas["/"][1]
    base = re.sub(r'<link rel="stylesheet" href="/estatico/tema.css">', "<style>%s</style>" % css, base)
    base = re.sub(r'<main class="pagina[^"]*" id="conteudo">.*?</main>', '<main class="pagina" id="conteudo"></main>', base, flags=re.S)
    base = re.sub(r'<script src="/estatico/app.js" defer></script>', "", base)
    base = _reescreve_links(base)
    base = base.replace('<div class="data">Base de %s</div>' % data_txt, '<div class="data">Retrato de %s</div>' % data_txt)
    base = base.replace("<title>Hoje — Central de Crédito e Cobrança</title>", "<title>Central de Crédito e Cobrança — retrato de %s</title>" % data_txt)
    rotas_js = json.dumps({r: ("p" + r.replace("/", "-") if r != "/" else "p-hoje") for r in paginas})
    roteador = """
window.CENTRAL_ARQUIVO = true;
window.CENTRAL_TEXTOS = %s;
(function () {
  var ROTAS = %s, TITULOS = %s, AVISO = %s;
  function rota() {
    var h = (location.hash || '').replace(/^#/, '') || '/';
    if (/^\\/regua\\/c\\d+$/.test(h)) h = '/regua';
    return ROTAS[h] ? h : '/';
  }
  var atual = null;
  function desenhar() {
    var r = rota(), tpl = document.getElementById(ROTAS[r]);
    if (r === atual && /^\\/regua/.test(r)) return;
    var main = document.getElementById('conteudo');
    main.innerHTML = '';
    main.appendChild(tpl.content.cloneNode(true));
    var aviso = main.querySelector('.faixa-arquivo');
    if (aviso) { aviso.textContent = AVISO + ' ' + aviso.textContent; }
    else { aviso = document.createElement('div'); aviso.className = 'faixa-arquivo'; aviso.textContent = AVISO; main.insertBefore(aviso, main.firstChild); }
    document.body.setAttribute('data-arquivo', '1');
    document.body.setAttribute('data-tela', tpl.getAttribute('data-tela'));
    document.title = TITULOS[r] || document.title;
    Array.prototype.forEach.call(document.querySelectorAll('.doca a'), function (a) {
      var alvo = a.getAttribute('href').replace(/^#/, '');
      var on = alvo === '/' ? r === '/' : (r === alvo || r.indexOf(alvo + '/') === 0);
      if (alvo === '/risco' && r.indexOf('/risco/') === 0) on = true;
      if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
    if (r !== atual) window.scrollTo(0, 0);
    atual = r;
    if (window.CentralIniciar) window.CentralIniciar();
  }
  window.addEventListener('hashchange', desenhar);
  window.__desenhar = desenhar;
})();
""" % (json.dumps(textos, ensure_ascii=False).replace("</", "<\\/"), rotas_js, json.dumps(titulos, ensure_ascii=False), json.dumps(AVISO_GERAL % (data_txt, geracao), ensure_ascii=False))
    partida = "<script>window.__desenhar && window.__desenhar();</script>"
    final = base.replace("</body>", "\n%s\n<script>%s</script>\n<script>%s</script>\n%s\n</body>" % (
        "\n".join(templates), roteador, js.replace("</", "<\\/"), partida))
    return final, ref, paginas, p, prev, blocos


def main():
    final, ref, *_ = gerar()
    saida = os.path.join(PASTA, "arquivo_unico")
    os.makedirs(saida, exist_ok=True)
    caminho = os.path.join(saida, "Central_%s.html" % ref.isoformat())
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(final)
    print("Arquivo único gerado: %s (%.0f KB)" % (caminho, os.path.getsize(caminho) / 1024))
    return caminho


if __name__ == "__main__":
    main()
