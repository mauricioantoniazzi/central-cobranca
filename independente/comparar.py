"""Compara o que está NA TELA (HTML servido) com a recontagem independente (independente.py) e de tela para tela.
Uso: python comparar.py PORTA   (com a Central no ar). Sai com código 1 se houver divergência."""
import html as H
import re
import sys
import urllib.request

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from independente import arred
from independente2 import indice_e_previsao

APP = "http://127.0.0.1:%s" % (sys.argv[1] if len(sys.argv) > 1 else "8200")
R = indice_e_previsao()
C, IND = R["C"], R["ind"]
achados = []
ok_n = [0]


def pega(caminho):
    return urllib.request.urlopen(APP + caminho).read().decode("utf-8").replace(" ", " ")


def texto(h):
    h = re.sub(r"<style.*?</style>|<script.*?</script>", "", h, flags=re.S)
    h = re.sub(r"<(br|/p|/li|/tr|/h\d|/div|/section|/table)[^>]*>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"[ \t\u00a0]+", " ", H.unescape(h))


def reais_num(s):
    """'R$ 1.234,56' -> float"""
    s = s.replace("R$", "").strip().replace(".", "").replace(",", ".")
    return float(s)


def confere(rotulo, tela, esperado, tol=0.0051):
    if tela is None or abs(tela - esperado) > tol:
        achados.append("%s: tela=%s independente=%s" % (rotulo, tela, esperado))
    else:
        ok_n[0] += 1


def por_nome(nome):
    return next(c for c, x in C.items() if x["nome"] == nome)


# ------------------------------------------------------------------ Hoje
h = pega("/")
t = texto(h)
kpis = re.findall(r'class="v">([^<]+)</span><span class="r">([^<]+)</span>', h)
hero_v = re.search(r'class="grande" data-conta="(\d+)">([^<]+)<', h)  # o número grande do alto: já vencido
kpis.append((hero_v.group(2), "já vencido"))
confere("Hoje número grande (data-conta) = texto do número grande", int(hero_v.group(1)), reais_num(hero_v.group(2).replace("\u00a0", " ")), 0.01)
mapa = {"em aberto": R["aberto"], "já vencido": R["vencido"], "a vencer": R["a_vencer"],
        "entrou nos últimos 7 dias": R["entrou_7d"], "venceu nos últimos 7 dias e não entrou": R["venceu_7d_aberto"]}
for val, rot in kpis:
    for k, v in mapa.items():
        if rot.startswith(k):
            confere("Hoje KPI '%s'" % k, reais_num(val.replace("\u00a0", " ")), v)
m = re.search(r"média das 8 semanas anteriores: (R\$ [\d.]+)", H.unescape(h).replace("\u00a0", " "))
confere("Hoje KPI média 8 semanas (estimativa, em reais inteiros)", reais_num(m.group(1)), arred(R["media_8s"]), 0.01)
for sec in re.findall(r'<article class="cartao.*?</article>', h, flags=re.S):
    nome = H.unescape(re.search(r'class="nome">([^<]+)', sec).group(1))
    c = por_nome(nome)
    x = C[c]
    venc = reais_num(re.search(r'class="valor"><span class="din">([^<]+)</span>', sec).group(1))
    confere("Hoje %s vencido" % nome, venc, x["vencido"])
    mctx = re.search(r"(\d+) títulos? · mais antigo há (\d+) dias?", sec)
    n = int(mctx.group(1))
    confere("Hoje %s n títulos vencidos" % nome, n, x["n_vencido"])
    mais = int(mctx.group(2))
    confere("Hoje %s mais antigo" % nome, mais, x["mais_antigo"])
    fr = re.search(r'<p class="frase">(.*?)</p>', sec, flags=re.S).group(1)
    fr = H.unescape(re.sub(r"<[^>]+>", "", fr))
    curto = H.unescape(re.sub(r"<[^>]+>", "", re.search(r'class="l1 motivo">(.*?)</span>', sec, flags=re.S).group(1)))
    for num in re.findall(r"\d+", curto):  # o motivo curto só pode usar números que a frase completa também traz
        if not re.search(r"(?<!\d)%s(?!\d)" % num, fr):
            achados.append("Hoje %s: o motivo curto traz o número %s, que a frase completa não traz" % (nome, num))
    pct = int(re.search(r"ocupa (\d+)% do limite", fr).group(1))
    confere("Hoje %s 'ocupa N%% do limite' = saldo em aberto / limite (a mesma conta da tela Risco)" % nome, pct, round(100 * x["ocupacao"]), 0.6)
    mm = re.search(r"em (\d+) títulos pagos o maior atraso foi de (\d+) dias", fr)
    if mm:
        confere("Hoje %s n pagos" % nome, int(mm.group(1)), x["n_pagos"])
        confere("Hoje %s maior atraso" % nome, int(mm.group(2)), x["max"])
    mm = re.search(r"costuma pagar com cerca de (\d+) dias", fr)
    if mm:
        confere("Hoje %s atraso habitual" % nome, int(mm.group(1)), arred(x["med_ns"]), 0.6)
    mm = re.search(r"pagava com cerca de (\d+) dias de atraso e nos últimos 6 pagamentos está em cerca de (\d+) dias", fr)
    if mm:
        confere("Hoje %s 'pagava' (antes)" % nome, int(mm.group(1)), x["base_med"], 0.6)
        confere("Hoje %s 'está em' (agora)" % nome, int(mm.group(2)), x["rec_med_pagos"], 0.6)
    mm = re.search(r"de cerca de (\d+) dias para cerca de (\d+) dias nos últimos 6", fr)
    if mm:
        if "base_med" not in x:
            achados.append("Hoje %s diz que o ritmo vem piorando (%s -> %s dias), mas a leitura de risco não tem como medir piora "
                           "(só %d pagamentos antes da janela recente; mínimo 20)" % (nome, mm.group(1), mm.group(2), x["n_base"]))
    # bloco 'como chegou': risco resultante
    mm = re.search(r"risco resultante (\d+)%", sec)
    if mm:
        confere("Hoje %s 'risco resultante' vs índice de risco da tela Risco" % nome, int(mm.group(1)), IND[c]["indice"], 0.5)

# ------------------------------------------------------------------ Risco (lista)
h = pega("/risco")
linhas = re.findall(r"<tr data-risco='[^']*'[^>]*><td class='pos' data-l=''>(\d+)</td><td data-l=''><span class='nome'><a href='/risco/(\d+)'>([^<]+)</a>(.*?)</tr>", h, flags=re.S)
for pos, cod, nome, resto in linhas:
    c = int(cod)
    x = C[c]
    cel = re.findall(r"<td[^>]*>(.*?)</td>", "<td>" + resto, flags=re.S)
    saldo = reais_num(re.search(r"R\$ [\d.,]+", resto).group(0))
    confere("Risco lista %s saldo" % H.unescape(nome), saldo, x["saldo"])
    oc = int(re.search(r"(\d+)% do limite", resto).group(1))
    confere("Risco lista %s ocupação" % H.unescape(nome), oc, round(100 * x["ocupacao"]), 0.6)
    idx = int(re.search(r"<b>(\d+)</b>", resto).group(1))
    confere("Risco lista %s índice" % H.unescape(nome), idx, IND[c]["indice"], 0.5)
    vr = reais_num(re.search(r"class='din'>(R\$ [\d.,]+)<", resto).group(1))
    confere("Risco lista %s valor em risco (estimativa, em reais inteiros)" % H.unescape(nome), vr, arred(IND[c]["valor_em_risco"]), 0.01)
    pf = float(re.search(r"([\d,]+)%<div class='sub-linha'>em 12 meses", resto).group(1).replace(",", "."))
    confere("Risco lista %s peso faturamento" % H.unescape(nome), pf, round(100 * x["pct_fat"], 1), 0.06)
ordem = [int(c) for _, c, _, _ in linhas]
esperada = sorted(C, key=lambda c: (-IND[c]["valor_em_risco"], -IND[c]["indice"]))
if ordem != esperada:
    achados.append("Risco lista: ordem na tela %s != independente %s" % (ordem, esperada))
else:
    ok_n[0] += 1
tot_vr = sum(s["valor_em_risco"] for s in IND.values())
m = re.search(r"Saldo total em aberto R\$ [\d.]+, valor em risco (R\$ [\d.,]+)", H.unescape(h).replace(" ", " "))
confere("Risco lista total valor em risco (estimativa, em reais inteiros)", reais_num(m.group(1)), arred(tot_vr), 0.01)

# ------------------------------------------------------------------ fichas
for c, x in C.items():
    h = pega("/risco/%d" % c)
    t = texto(h)
    nome = x["nome"]
    mm = re.search(r"([\d]+)\s*/ 100", t)
    confere("Ficha %s índice" % nome, int(mm.group(1)), IND[c]["indice"], 0.5)
    mm = re.search(r"Faturamento 12 meses\s*(R\$ [\d.,]+)\s*\(([\d.,]+)% da carteira", t)
    confere("Ficha %s faturamento 12m" % nome, reais_num(mm.group(1)), x["fat12"])
    confere("Ficha %s peso faturamento" % nome, float(mm.group(2).replace(",", ".")), round(100 * x["pct_fat"], 1), 0.06)
    mm = re.search(r"Limite ocupado\s*(\d+)% de (R\$ [\d.,]+)", t)
    confere("Ficha %s limite ocupado" % nome, int(mm.group(1)), round(100 * x["ocupacao"]), 0.6)
    confere("Ficha %s limite" % nome, reais_num(mm.group(2)), x["limite"])
    mm = re.search(r"Último pedido\s*há (\d+) dias? \((\d\d/\d\d/\d{4})\)", t)
    confere("Ficha %s dias sem comprar" % nome, int(mm.group(1)), x["dias_sem_comprar"])
    mm = re.search(r"Paga, em geral, com\s*(\d+) dias de atraso", t)
    if mm:
        confere("Ficha %s atraso habitual (mediana)" % nome, int(mm.group(1)), arred(x["med_ns"]), 0.6)
        mm2 = re.search(r"80% dos pagamentos\s*entre (-?\d+) e (-?\d+) dias", t)
        confere("Ficha %s 80%% p10" % nome, int(mm2.group(1)), arred(x["p10_ns"]), 0.6)
        confere("Ficha %s 80%% p90" % nome, int(mm2.group(2)), arred(x["p90_ns"]), 0.6)
        mm3 = re.search(r"Maior atraso\s*(\d+) dias", t)
        confere("Ficha %s maior atraso" % nome, int(mm3.group(1)), x["max"])
        # legenda do gráfico x texto do fator 'Imprevisibilidade' x números da ficha
        leg = re.search(r"padrão histórico \(80% dos pagamentos entre (-?\d+) e (-?\d+) dias\)", t)
        if leg:
            if (int(leg.group(1)), int(leg.group(2))) != (int(mm2.group(1)), int(mm2.group(2))):
                achados.append("Ficha %s: o gráfico diz que 80%% dos pagamentos ficam entre %s e %s dias; o quadro da mesma ficha diz entre %s e %s"
                               % (nome, leg.group(1), leg.group(2), mm2.group(1), mm2.group(2)))
            else:
                ok_n[0] += 1
    mm = re.search(r"Saldo em aberto\s*R\$ ([\d.,]+)", t)
    confere("Ficha %s saldo" % nome, reais_num(mm.group(1)), x["saldo"])
    mm = re.search(r"Valor em risco\s*(R\$ [\d.,]+)", t)
    confere("Ficha %s valor em risco (estimativa, em reais inteiros)" % nome, reais_num(mm.group(1)), arred(IND[c]["valor_em_risco"]), 0.01)
    if x["n_vencido"]:
        mm = re.search(r"Tem (R\$ [\d.,]+) vencidos", t)
        if mm:  # cliente sem histórico não tem a frase do fator "vencido fora do padrão": aparece "Sem dados suficientes"
            confere("Ficha %s vencido" % nome, reais_num(mm.group(1)), x["vencido"])
    mm = re.search(r"mediana de (\d+) títulos pagos", t)
    if mm:
        confere("Ficha %s n de títulos pagos no fator habitual" % nome, int(mm.group(1)), x["n_ns"])
    mm = re.search(r"(\d+) dos (\d+) fins de mês", t)
    if mm:
        confere("Ficha %s fins de mês na lista" % nome, int(mm.group(1)), x["fins_vencido"])
        confere("Ficha %s fins de mês (total)" % nome, int(mm.group(2)), x["fins"])

# ------------------------------------------------------------------ Previsão
h = pega("/previsao")
t = texto(h)
mm = re.search(r"(R\$ [\d.,]+)\s*O que a planilha aponta: soma dos vencimentos até", t)
confere("Previsão planilha", reais_num(mm.group(1)), R["planilha_total"])
mm = re.search(r"(R\$ [\d.]+)\s*O que espero, lendo como cada cliente paga de verdade", t)
esp_total = sum(R["prev_sem"]["esp"]) / 100
confere("Previsão esperado", reais_num(mm.group(1)), round(esp_total), 0.51)
mm = re.search(r"diferença: quanto a planilha promete a mais do que deve entrar\s*(R\$ [\d.]+)", t)
confere("Previsão diferença", reais_num(mm.group(1)), R["planilha_total"] - round(esp_total), 0.51)
for rot, k in (("conservador", "cons"), ("otimista", "otim")):
    mm = re.search(rot + r" (R\$ [\d.]+)", t)
    confere("Previsão acumulado %s" % rot, reais_num(mm.group(1)), round(sum(R["prev_sem"][k]) / 100), 0.51)
for linha in re.findall(r"<tr><td><a class='cli' href='/risco/(\d+)'>.*?</tr>", h, flags=re.S)[:0]:
    pass
for cod, resto in re.findall(r"<tr><td data-l=''><span class='nome'><a href='/risco/(\d+)'>[^<]+</a></span>(.*?)</tr>", h, flags=re.S):
    c = int(cod)
    vals = re.findall(r"<td class='n' data-l='[^']*'>(R\$ [\d.,]+)", resto)
    plan_cli = sum(t_["valor"] for t_ in R["tit"] if t_["cli"] == c and t_["pago"] is None and (t_["venc"] - R["ref"]).days <= 28)
    confere("Previsão %s planilha" % C[c]["nome"], reais_num(vals[0]), plan_cli)
    confere("Previsão %s esperado" % C[c]["nome"], reais_num(vals[1]), round(R["prev_cli"][c] / 100), 0.51)

# ------------------------------------------------------------------ Relatório
t = texto(pega("/relatorio"))
for rot, v in (("entraram", R["entrou_7d"]), ("vencidos e não pagos", R["vencido"]), ("a vencer", R["a_vencer"])):
    m_ = "R$ {:,.2f}".format(v).replace(",", "X").replace(".", ",").replace("X", ".")
    if m_ not in t:
        achados.append("Relatório não traz %s = %s" % (rot, m_))
    else:
        ok_n[0] += 1

print("conferências que bateram:", ok_n[0])
print("divergências:", len(achados))
for a in achados:
    print(" -", a)


# ================================================== acréscimos: fila de Hoje, Régua, relatório, tela a tela
import json, math, urllib.parse
achados.clear()
ok2 = [0]


def c2(rotulo, tela, esperado, tol=0.0051):
    if tela is None or abs(tela - esperado) > tol:
        achados.append("%s: tela=%s independente=%s" % (rotulo, tela, esperado))
    else:
        ok2[0] += 1


# fila de Hoje pela conta independente (valor relativo = raiz do vencido / maior; 40% valor + 60% índice; x0,35 se cobrado < 48h)
import datetime as dt
cobrados = {}
for cb in R["cobrancas"]:
    cobrados[cb["cli"]] = max(cobrados.get(cb["cli"], dt.datetime.min), cb["quando"])
hh, mm_ = (int(x) for x in os.environ.get("CENTRAL_HORA", "10:00").split(":"))
agora = dt.datetime.combine(R["ref"], dt.time(hh, mm_))
comvenc = [c for c, x in C.items() if x["vencido"] > 0]
maior = max((C[c]["vencido"] for c in comvenc), default=1)  # nada vencido: a fila esperada é vazia
score = {}
for c in comvenc:
    base = 100 * (0.4 * math.sqrt(C[c]["vencido"] / maior) + 0.6 * IND[c]["indice"] / 100)
    recente = c in cobrados and (agora - cobrados[c]).total_seconds() / 3600 < 48
    score[c] = base * (0.35 if recente else 1)
ordem_ind = sorted(comvenc, key=lambda c: (-score[c], -C[c]["vencido"]))
hoje = pega("/")
nomes_hoje = [H.unescape(n) for n in re.findall(r'class="nome">([^<]+)', hoje)]
esperado_nomes = [C[c]["nome"] for c in ordem_ind]
if nomes_hoje != esperado_nomes:
    achados.append("Hoje: ordem da fila na tela %s != independente %s" % (nomes_hoje, esperado_nomes))
else:
    ok2[0] += 1
pont = [int(x) for x in re.findall(r"\(pontuação (\d+)\)", hoje)]
for c, pt in zip(ordem_ind, pont):
    c2("Hoje %s pontuação" % C[c]["nome"], pt, round(score[c]), 0.51)
# a Hoje usa o índice da tela Risco
for sec in re.findall(r'<article class="cartao.*?</article>', hoje, flags=re.S):
    nome = H.unescape(re.search(r'class="nome">([^<]+)', sec).group(1))
    c = next(k for k, x in C.items() if x["nome"] == nome)
    mm = re.search(r"índice de risco (\d+) de 100", sec)
    c2("Hoje %s usa o índice de risco da tela Risco" % nome, int(mm.group(1)), IND[c]["indice"], 0.5)
# Régua: mesma ordem, mesmo vencido, mesmos dias; textos com o valor certo
reg = pega("/regua")
nomes_reg = [H.unescape(n) for n in re.findall(r'class="nm">([^<]+)', reg)]
if nomes_reg != esperado_nomes:
    achados.append("Régua: ordem %s != ordem de Hoje %s" % (nomes_reg, esperado_nomes))
else:
    ok2[0] += 1
for sec in re.findall(r'<section class="regua-painel.*?</section>', reg, flags=re.S):
    nome = H.unescape(re.search(r"<h2>([^<]+)</h2>", sec).group(1))
    c = next(k for k, x in C.items() if x["nome"] == nome)
    c2("Régua %s vencido" % nome, reais_num(re.search(r'class="valor">([^<]+)', sec).group(1)), C[c]["vencido"])
    dias = sorted(int(d) for d in re.findall(r"R\$ [\d.,]+ · (\d+) dia", sec))
    esp = sorted((R["ref"] - t["venc"]).days for t in R["tit"] if t["cli"] == c and t["pago"] is None and t["venc"] < R["ref"])
    if dias != esp:
        achados.append("Régua %s dias de atraso dos títulos: tela %s independente %s" % (nome, dias, esp))
    else:
        ok2[0] += 1
    ta = H.unescape(re.search(r"<textarea[^>]*>(.*?)</textarea>", sec, flags=re.S).group(1))
    for t in R["tit"]:
        if t["cli"] == c and t["pago"] is None and t["venc"] < R["ref"]:
            v = "R$ {:,.2f}".format(t["valor"]).replace(",", "X").replace(".", ",").replace("X", ".")
            if t["num"] not in ta.replace("\u00a0", " ") and "conversa comercial" not in sec.lower():
                if "Mudou alguma coisa no movimento" not in ta:
                    achados.append("Régua %s: texto não traz o título %s" % (nome, t["num"]))
                    continue
            ok2[0] += 1
# Serra Azul: números do texto da cobrança batem com a recontagem
# todo cartão da Régua cujo texto sugere acertar o prazo (tom "Lembrete leve e acerto de prazo"): os números do texto batem com a recontagem
for sec in re.findall(r'<section class="regua-painel.*?</section>', reg, flags=re.S):
    ta = H.unescape(re.search(r"<textarea[^>]*>(.*?)</textarea>", sec, flags=re.S).group(1)).replace("\u00a0", " ")
    mm = re.search(r"uns (\d+) dias depois do vencimento.*?uns (\d+) dias, e não os (\d+) do contrato", ta, flags=re.S)
    if not mm:
        continue
    nome_c = H.unescape(re.search(r"<h2>([^<]+)</h2>", sec).group(1))
    cod_c = next(k for k, x in C.items() if x["nome"] == nome_c)
    c2("Régua %s texto: atraso típico" % nome_c, int(mm.group(1)), arred(C[cod_c]["med_ns"]), 0.01)
    c2("Régua %s texto: prazo real" % nome_c, int(mm.group(2)), C[cod_c]["prazo"] + arred(C[cod_c]["med_ns"]), 0.01)
    c2("Régua %s texto: prazo do contrato" % nome_c, int(mm.group(3)), C[cod_c]["prazo"], 0.01)
# relatório: cada decisão com o valor em risco e vencido certos, na ordem certa
rel = pega("/relatorio")
dec = [(n, re.sub(r"<[^>]+>", "", cab), re.sub(r"<[^>]+>", "", corpo))
       for n, cab, corpo in re.findall(r'<p class="decisao"><b>(\d+)\. (.*?)</b> (.*?)</p>', rel, flags=re.S)]
ordem_vr = [c for c in sorted(C, key=lambda c: (-IND[c]["valor_em_risco"], -IND[c]["indice"])) if C[c]["vencido"] > 0 or False]
ns = [(n, cab, corpo) for n, cab, corpo in dec]
nomes_dec = [next(x["nome"] for x in C.values() if cab.startswith(x["nome"])) for _, cab, _ in ns]
vr_dec = [next(IND[c]["valor_em_risco"] for c, x in C.items() if x["nome"] == nome) for nome in nomes_dec]
if vr_dec != sorted(vr_dec, reverse=True):
    achados.append("Relatório: decisões fora da ordem de valor em risco: %s" % vr_dec)
else:
    ok2[0] += 1
for n, cab, corpo in ns:
    nome = next(x["nome"] for x in C.values() if cab.startswith(x["nome"]))
    c = next(k for k, x in C.items() if x["nome"] == nome)
    m_ = re.search(r"(?:São|Valor em risco:) R\$ ([\d.]+)", corpo.replace("\u00a0", " "))
    c2("Relatório decisão %s valor em risco" % nome, float(m_.group(1).replace(".", "")), arred(IND[c]["valor_em_risco"]), 0.01)
# tela a tela: o mesmo cliente com o mesmo atraso típico em Risco, Previsão, Régua (motivo) e Relatório
prev = texto(pega("/previsao")).replace("\u00a0", " ")
for c, x in C.items():
    if x["n_vencido"] == 0 and x["saldo"] == 0:
        continue
    nome = x["nome"]
    if x.get("piora"):
        mm = re.search(re.escape(nome) + r".{0,80}?Piorou: hoje paga com cerca de (\d+) dias", prev, flags=re.S)
        if mm:
            c2("Previsão %s atraso recente (piorou)" % nome, int(mm.group(1)), x["rec_med_pagos"], 0.51)
        mm = re.search(r"Piorou: hoje paga com cerca de (\d+) dias.*?não os (\d+) dias", prev, flags=re.S)
        if mm:
            c2("Previsão %s atraso antes" % nome, int(mm.group(2)), arred(x["base_med"]), 0.51)
print("\nacréscimos — bateram:", ok2[0], " divergências:", len(achados))
for a in achados:
    print(" -", a)

sys.exit(1 if achados else 0)
