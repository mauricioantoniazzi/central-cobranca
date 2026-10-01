"""Tela "Hoje" (tema Aurora): UM painel de abertura, uma linha de ferramentas e a fila, quatro fileiras por cartão.

Sem nada escrito à mão: cada número e cada frase vêm de motor.py, risco.py e frases.py. O que está aqui é só desenho.
O que não cabe nas quatro fileiras do cartão fica atrás de "Por que está aqui" (o inventário de inventario_telas.py e a parte 7
da conferência cobram que nada some da página).
"""
from html import escape

from frases import (arred, contexto_curto, envolve_dinheiro, faixa_risco, frase, motivo_curto, pl, reais, reais_est, ultimo_contato)
from motor import FATOR_COBRADO_RECENTE, HORAS_SEM_INSISTIR, PESO_RISCO, PESO_VALOR
from visual import _d, caixa_avisos, chip_risco, pagina as _casca

SETA = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" style="stroke:currentColor;fill:none;stroke-width:2.3;stroke-linecap:round;stroke-linejoin:round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
LUPA = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/></svg>'
ICONE_DESC = {
    "crit": '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.2"/>',
    "ok": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
    "aten": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.5l3 2"/>',
}
CHEIOS = 3  # os três primeiros cartões têm a frase em duas linhas e botões; do quarto para baixo, uma linha e só links


def anel(pct):
    circ = 314.16
    return ('<div class="anel" role="img" aria-label="%d%% do que está em aberto já venceu"><svg viewBox="0 0 120 120">'
            '<circle class="trilho" cx="60" cy="60" r="50"/><circle class="arco" cx="60" cy="60" r="50" stroke-dasharray="%.1f %.1f"/></svg>'
            '<div class="centro"><b>%d%%</b></div></div>' % (pct, circ * pct / 100, circ, pct))


def descobertas(lista, titulo="A lista por data não mostra"):
    if not lista:
        return ""
    itens = "".join(
        '<a class="desc k-%s" href="/risco/%d"><span class="selo"><svg viewBox="0 0 24 24" aria-hidden="true">%s</svg></span>'
        '<span style="min-width:0;flex:1"><span class="quem">%s</span> <span class="tipo">· %s</span>'
        '<span class="o-que">%s</span></span></a>' % (
            d["tipo"], d["codigo"], ICONE_DESC[d["tipo"]], escape(d["nome"]), escape(d["rotulo"]), envolve_dinheiro(escape(d["o_que"])))
        for d in lista)
    return '<aside class="achados-curtos" aria-label="%s"><div class="cab"><span class="eyebrow">%s</span></div>%s</aside>' % (
        escape(titulo), escape(titulo), itens)


def _titulos(f):
    linhas = "".join("<tr><td>%s</td><td class='n'>%s</td><td>%s</td><td class='n'>%d</td></tr>" % (
        escape(t["numero"]), reais(t["valor"]), _d(t["vencimento"]), t["dias_atraso"]) for t in f["titulos"])
    return ('<table><tr><th>Título</th><th class="n">Valor</th><th>Vencimento</th><th class="n">Dias em atraso</th></tr>%s</table>' % linhas)


def _quem(c):
    """Fileira 2: quem é o cliente e com quem (e em que telefone) se fala."""
    partes = ["%s · %s" % (escape(c["categoria"]), escape(c["regiao"]))]
    contato = c.get("contato") or "sem contato no cadastro"
    partes.append("falar com <b>%s</b>%s" % (escape(contato), (" · " + escape(c["telefone"])) if c.get("telefone") else ""))
    return " · ".join(partes)


def _cartao(f, i):
    c, cod = f["cliente"], f["cliente"]["codigo"]
    chave, _ = faixa_risco(f["indice"])
    recente = f["cobrado_recente"]
    cheio = i < CHEIOS
    chips = chip_risco(f["indice"]).replace("</span>", " · %d</span>" % f["indice"], 1)
    if recente:
        chips += '<span class="chip ruim">cobrado nas últimas %dh — desceu na fila</span>' % HORAS_SEM_INSISTIR
    risco_txt = ("índice de risco %d de 100%s, o mesmo da tela <a href='/risco/%d'>Risco por cliente</a>"
                 % (f["indice"], " (parcial: faltou dado em alguma conta)" if f["leitura"]["parcial"] else "", cod))
    rel = ("cobrado há menos de %dh, pontuação multiplicada por %s" % (HORAS_SEM_INSISTIR, FATOR_COBRADO_RECENTE)
           if recente else "sem cobrança nas últimas %dh, sem redução" % HORAS_SEM_INSISTIR)
    ctx = contexto_curto(f)
    detalhe = (
        '<div class="detalhe"><p class="frase">%s</p><p class="ult">%s</p><p class="ult">%s</p>'
        '<p class="ult">Como chegou nessa posição (pontuação %d): valor vencido em %d%% do maior vencido da fila (peso %d%% da pontuação); '
        'risco: %s (peso %d%% da pontuação); relacionamento: %s.</p>%s</div>' % (
            envolve_dinheiro(escape(frase(f))), envolve_dinheiro(escape(ultimo_contato(f))), escape(ctx), arred(f["score"]),
            round(100 * f["valor_rel"]), round(100 * PESO_VALOR), risco_txt, round(100 * PESO_RISCO), rel, _titulos(f)))
    l2 = "%s vencidos, o mais antigo há %s." % (pl(f["n"], "título", "títulos"), "%d dia%s" % (f["mais_antigo"], "" if f["mais_antigo"] == 1 else "s"))
    return """<article class="cartao vidro%s%s%s" data-cod="%d" data-risco="%s" data-pos="%d" data-valor="%d" data-dias="%d" data-indice="%d" data-recente="%d" data-base="%.6f" data-nome="%s" data-l2="%s">
<div class="r1"><span class="pos">%d</span><span class="nome">%s</span>%s<span class="valor"><span class="din">%s</span><small>vencidos</small></span></div>
<div class="r2">%s</div>
<p class="r3"><span class="l1 motivo">%s</span><span class="l2">%s</span></p>
<div class="r4"><div class="acoes"><a class="btn principal" href="/regua#c%d">Redigir a cobrança %s</a><button class="btn suave so-operacao js-liguei" type="button" data-nome="%s">Já liguei</button><a class="btn suave" href="/risco/%d">Ficha</a></div>
<details class="mais"><summary>Por que está aqui</summary>%s</details></div>
</article>""" % (
        " primeiro" if i == 0 else "", " ligado" if recente else "", "" if cheio else " simples", cod, chave, f["posicao"], f["vencido"],
        f["mais_antigo"], f["indice"], 1 if recente else 0, f["score_base"], escape(c["nome"].lower()), escape(l2),
        f["posicao"], escape(c["nome"]), chips, reais(f["vencido"]), _quem(c),
        envolve_dinheiro(escape(motivo_curto(f))), escape(l2) if cheio else "", cod, SETA, escape(c["nome"]), cod, detalhe)


def _ferramentas(fila):
    n = len(fila)
    quant = sum(1 for f in fila if faixa_risco(f["indice"])[0] == "alto")
    livres = sum(1 for f in fila if not f["cobrado_recente"])
    filtros = ('<button type="button" data-filtro="todos" aria-pressed="true">Todos<span class="q">%d</span></button>'
               '<button type="button" data-filtro="alto" aria-pressed="false">Só os mais graves<span class="q">%d</span></button>'
               '<button type="button" data-filtro="livre" aria-pressed="false">Ainda não cobrados<span class="q">%d</span></button>' % (n, quant, livres))
    return ("""<div class="ferramentas" role="search"><h2>Quem ligar primeiro</h2>
<label class="busca"><span class="sr">Buscar cliente</span>%s<input type="search" id="busca" placeholder="Buscar cliente" autocomplete="off"></label>
<div class="filtros" role="group" aria-label="Filtrar a fila">%s</div>
<label class="ordem">Ordem <select id="ordem"><option value="fila">A da fila</option><option value="valor">Maior valor vencido</option>
<option value="dias">Mais dias de atraso</option><option value="indice">Maior índice de risco</option><option value="nome">Nome</option></select></label>
<span class="contagem" id="contagem" aria-live="polite"></span></div>""" % (LUPA, filtros))


def hoje(resumo, fila, avisos=None, rs=None, n_lista=None):
    import risco as _risco
    aberto, venc = resumo["aberto"], resumo["vencido"]
    pct = arred(100 * venc / aberto) if aberto else 0
    achados = _risco.descobertas(rs, n_lista) if rs else []
    stat = lambda v, r: '<div class="stat"><span class="v">%s</span><span class="r">%s</span></div>' % (v, r)
    painel = """<section class="painel vidro brilho" aria-label="Resumo do dia">
<div class="esq"><span class="eyebrow">já vencido</span>
<span class="grande" data-conta="%d">%s</span>
<div class="linha-num" style="margin-top:.5rem">%s<p class="apoio">%s de %s · %d%% do que está em aberto já venceu</p></div></div>
%s
<div class="stats">%s%s%s%s</div>
<details class="mais dobra-int"><summary>Detalhes da semana</summary><div class="detalhe">
<p>Em aberto: %s. A vencer: ainda dentro do prazo.</p>
<p>Entrou nos últimos 7 dias: %s de %s; média das 8 semanas anteriores: %s.</p>
<p>Venceu nos últimos 7 dias e não entrou: %s, de %s que venceram.</p></div></details>
</section>""" % (
        (venc + 50) // 100, reais_est(venc), anel(pct), pl(resumo["n_vencidos"], "título", "títulos"), pl(resumo["n_clientes_vencido"], "cliente", "clientes"),
        pct, descobertas(achados),
        stat(reais_est(aberto), "em aberto"), stat(reais_est(resumo["a_vencer"]), "a vencer"),
        stat(reais_est(resumo["entrou_7d"]), "entrou nos últimos 7 dias"), stat(reais_est(resumo["venceu_7d_aberto"]), "venceu nos últimos 7 dias e não entrou"),
        pl(resumo["n_abertos"], "título", "títulos"),
        pl(resumo["n_entrou_7d"], "título", "títulos"), pl(resumo["n_clientes_entrou_7d"], "cliente", "clientes"), reais_est(resumo["entrou_media_8s"]),
        pl(resumo["n_venceu_7d_aberto"], "título", "títulos"), reais_est(resumo["venceu_7d"]))
    cartoes = "\n".join(_cartao(f, i) for i, f in enumerate(fila)) or '<p class="nenhum vidro">Nenhum cliente tem título vencido na data de referência.</p>'
    corpo = """<h1 class="sr">Hoje</h1>%s%s
%s
<div class="fila" id="fila" data-fator="%s">%s</div>
<p class="nenhum vidro escondido" id="vazio">Nenhum cliente combina com a busca ou com o filtro.</p>
<details class="dobra vidro"><summary>Como a fila é montada</summary><div class="corpo">
<p>Distribuidora Aurora · posição em %s. %s de %s, emitidos de %s a %s.</p>
<p>A ordem não é por vencimento nem por valor: combina o valor vencido, o risco calculado sobre o histórico de pagamento do próprio cliente e o relacionamento (quem foi cobrado nas últimas %d horas desce). Clientes sem nada vencido não entram na fila.</p></div></details>""" % (
        caixa_avisos(avisos), painel, _ferramentas(fila) if fila else "", FATOR_COBRADO_RECENTE, cartoes,
        _d(resumo["data_ref"]), pl(resumo["n_titulos"], "título", "títulos"), pl(resumo["n_clientes"], "cliente", "clientes"),
        _d(resumo["primeira_emissao"]), _d(resumo["ultima_emissao"]), HORAS_SEM_INSISTIR)
    return _casca("Hoje", corpo, "hoje", resumo["data_ref"])
