"""Conferência da Central. Uso:  python conferir.py

Dois modos, escolhidos sozinhos pelo conteúdo da planilha em uso (Base_bruta.xlsx, ou o arquivo de CENTRAL_BASE):
  REFERÊNCIA  a planilha é idêntica à de fixtures/Base_2026-08.xlsx: roda TUDO, inclusive a comparação das telas com o
              retrato conferencia_base.json. É o modo para provar que uma mudança de tela/código não mexeu em número.
  BASE NOVA   qualquer outra planilha: a comparação com o retrato não se aplica (os números mudaram de verdade), e
              roda o resto: as contas fecham, as telas não se contradizem, recontagem independente, formato e escrita.
Para rodar o modo referência depois de trocar a planilha:  CENTRAL_BASE=fixtures/Base_2026-08.xlsx python conferir.py

1. Roda as verificações internas (os assert de motor.py e risco.py) sobre a planilha.
2. Confere que as telas Hoje e Risco por cliente continuam dizendo o que diziam: compara com
   conferencia_base.json, gravado ANTES de a tela de Previsão existir (python conferir.py --gravar).
3. Confere que as telas não se contradizem (mesmo vencido, mesmo saldo, por cliente).
4. Confere a Previsão de caixa: fecha em centavos, faixa monotônica no acumulado, decomposição da diferença.
5. Confere a Régua de cobrança e o registro (tom, texto, hora da base, persistência, planilha intocada, fila mexe),
   a tela Cobranças feitas e o Relatório da semana (mesmos números das telas, .docx válido), e que nenhuma das duas
   partes chama serviço externo nem escreve texto fora de redacao.py.

Se uma verificação quebrar, o conserto é no código, não aqui.
"""
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import motor
import pagina
import pagina_risco
import risco
import servico

PASTA = os.path.dirname(os.path.abspath(__file__))
BASE = servico.caminho_base()
ARQ_BASE = os.path.join(PASTA, "conferencia_base.json")
REFERENCIA = os.path.join(PASTA, "fixtures", "Base_2026-08.xlsx")


def _sha(caminho):
    return hashlib.sha256(open(caminho, "rb").read()).hexdigest()


def _e_a_base_de_referencia():
    return os.path.exists(REFERENCIA) and _sha(BASE) == _sha(REFERENCIA)


def _sem_nav(html):
    return re.sub(r"<nav.*?</nav>", "", html, flags=re.S)


def _hash(html):
    return hashlib.sha256(_sem_nav(html).encode("utf-8")).hexdigest()


def instantaneo():
    """Números e textos das telas Hoje e Risco, sem o menu de navegação."""
    ref, rs, n_lista = risco.analisar(BASE)
    resumo, fila = motor.calcular(BASE, leitura={r["cliente"]["codigo"]: r for r in rs})
    snap = {
        "hoje": {
            "resumo": {k: str(v) for k, v in resumo.items()},
            "fila": [[f["posicao"], f["cliente"]["codigo"], f["vencido"], round(f["score"], 6)] for f in fila],
            "html": _hash(pagina.hoje(resumo, fila)),
        },
        "risco": {
            "ordem": [r["cliente"]["codigo"] for r in rs],
            "clientes": {str(r["cliente"]["codigo"]): {
                "indice": r["indice"], "valor_em_risco": r["valor_em_risco"], "saldo": r["saldo"],
                "tags": r["tags"], "alerta": r["alerta"],
                "fatores": [[f["chave"], None if f["pontos"] is None else round(f["pontos"], 6), f["frase"]]
                            for f in r["fatores"]],
                "html": _hash(pagina_risco.ficha(ref, r)),
            } for r in rs},
            "html_lista": _hash(pagina_risco.lista(ref, rs, n_lista)),
        },
    }
    return snap, resumo, fila, ref, rs


# Mudanças declaradas nas telas antigas em relação ao retrato original (conferencia_base.json, de antes da Previsão).
# Cada uma tem um motivo escrito; o que não está aqui continua sendo checado como "não pode mudar".
#  3ª rodada (autorizada pelo dono): o atraso "atual" de quem piorou vem só dos títulos já pagos (26 dias, não 22).
#  4ª rodada: o relatório precisou dos números da semana; eles passaram a morar em motor.calcular e a Hoje os mostra.
#  5ª rodada (auditoria): a Hoje passou a usar o índice de risco da tela Risco (antes tinha um "risco" próprio, com o mesmo
#  nome e outro número), as estimativas perderam o centavo, o "R$" não se separa mais do valor, vírgula decimal,
#  palavras de analista trocadas por palavras do financeiro, e o motivo do dado que faltou passou a ser dito.
_NOVOS_HOJE = ("entrou_7d", "n_entrou_7d", "n_clientes_entrou_7d", "entrou_media_8s", "janela_ini", "venceu_7d", "n_venceu_7d",
               "venceu_7d_aberto", "n_venceu_7d_aberto")
DECLARADAS = [
    (r"^/hoje/html$", "Hoje: quadros novos, link da Régua, risco = índice da tela Risco, R$ sem quebra, estimativa sem centavo"),
    (r"^/hoje/fila$", "Hoje: a pontuação da fila passou a usar o índice de risco da tela Risco (a ordem pode mudar)"),
    (r"^/hoje/resumo/(%s)$" % "|".join(_NOVOS_HOJE), "número da semana, novo em motor.calcular"),
    (r"^/risco/clientes/\d+/(alerta|fatores|html)$", "textos da ficha: 'atraso típico', sem 'ruptura', vírgula decimal, estimativa sem centavo, R$ sem quebra"),
    (r"^/risco/clientes/(5|6)/tags$", "tag 'historico_curto' virou 'falta_dado' (dizia histórico curto para quem tem 37 pagamentos)"),
    (r"^/risco/html_lista$", "lista de Risco: valor em risco sem centavo, vírgula decimal, cabeçalho sem quebra, cartões no celular"),
]


def _declarada(caminho):
    return any(re.match(rx, caminho) for rx, _ in DECLARADAS)


def _diff(a, b, caminho=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            yield from _diff(a.get(k), b.get(k), "%s/%s" % (caminho, k))
    elif a != b:
        yield caminho


def _sem_marcas(texto):
    return not any(m in texto for m in ("{", "}", "%s", "%d", "None", "Traceback", "[seu", "XXX"))


def rodada4(ok, ref, resumo, fila, rs, prev, pasta_dados):
    import docx_min
    import pagina_cobranca
    import pagina_relatorio
    import pagina_previsao
    import previsao
    import redacao
    import regua
    import registro
    import relatorio
    import servico
    from frases import reais, reais_est
    from relogio import agora

    print("5. Régua de cobrança, registro e relatório")
    hash_antes = hashlib.sha256(open(BASE, "rb").read()).hexdigest()
    p0 = servico.painel()
    por_cli = p0["risco_por_cliente"]
    venc = [f for f in p0["fila"]]
    if not venc:
        print("  (pulado: nenhum cliente tem título vencido nesta planilha; régua e registro não têm o que testar. "
              "O relatório e as telas seguem sendo verificados na parte 6.)")
        return

    # --- tons
    escolhidos = {}
    for f in venc:
        cod = f["cliente"]["codigo"]
        r = por_cli[cod]
        escolhidos[cod] = regua.escolher(ref, r, regua.contatos_do_cliente(p0["cobrancas"], cod))
    ok(all(ch in regua.TONS and len(raz) >= 1 for ch, raz in escolhidos.values()),
       "todo cliente com vencido recebe um tom, com ao menos uma frase que explica a escolha (%d clientes)" % len(escolhidos))
    coerente = True
    for cod, (ch, _) in escolhidos.items():
        t = por_cli[cod]["tags"]
        if "parou" in t:
            coerente &= ch == "comercial"
        elif "piorou" in t:
            coerente &= ch == "conversa_piora"
        elif "atrasa_igual" in t and not risco.fora_do_padrao(por_cli[cod]):
            coerente &= ch == "lembrete_prazo"
    ok(coerente, "parou de comprar -> conversa comercial; piorou -> conversa; atrasa sempre igual -> lembrete com prazo")
    print("        tons desta planilha: %s" % ", ".join(sorted({regua.nome_tom(ch) for ch, _ in escolhidos.values()})))

    # --- textos: todos os tons, todos os canais, todos os clientes
    tudo_ok, lista_ok, total_ok, n_textos = True, True, True, 0
    for f in venc:
        cod = f["cliente"]["codigo"]
        r = por_cli[cod]
        nums = [t["numero"] for t in r["vencidos"]]
        for chave in regua.TONS:
            for canal in registro.CANAIS:
                ctx = regua.contexto(ref, r, chave, canal, nums, regua.contatos_do_cliente(p0["cobrancas"], cod), "Maria")
                txt = redacao.REDATOR.cobranca(ctx)["texto"]
                n_textos += 1
                tudo_ok &= _sem_marcas(txt) and len(txt) > 200 and (canal == "Telefone" or "Olá" in txt)
                if chave != "comercial":
                    lista_ok &= all(n in txt for n in nums)
                    if len(nums) > 1:
                        total_ok &= reais(sum(t["valor"] for t in r["vencidos"])) in txt
                else:
                    lista_ok &= reais(r["vencido"]) in txt  # a conversa comercial cita o total, não lista título
    ok(tudo_ok, "%d textos (8 tons x 3 canais x %d clientes) sem marca de modelo não preenchida, sem 'None'" % (n_textos, len(venc)))
    ok(lista_ok, "todo texto lista os títulos um a um (a conversa comercial cita só o total)")
    ok(total_ok, "quando há mais de um título, o texto traz o total certo")
    so_um = regua.contexto(ref, por_cli[venc[0]["cliente"]["codigo"]], "objetiva", "WhatsApp",
                           [por_cli[venc[0]["cliente"]["codigo"]]["vencidos"][0]["numero"]], [], "")
    txt_um = redacao.REDATOR.cobranca(so_um)["texto"]
    ok(so_um["total"] == por_cli[venc[0]["cliente"]["codigo"]]["vencidos"][0]["valor"] and "Total:" not in txt_um,
       "escolher só um título reescreve o texto só com ele")
    ok("Sou" not in redacao.REDATOR.cobranca(regua.contexto(ref, por_cli[venc[0]["cliente"]["codigo"]], "primeiro_aviso", "WhatsApp",
                                                                [por_cli[venc[0]["cliente"]["codigo"]]["vencidos"][0]["numero"]], [], "Maria"))["texto"]
       and "Aqui é Maria" in redacao.REDATOR.cobranca(regua.contexto(ref, por_cli[venc[0]["cliente"]["codigo"]], "primeiro_aviso", "WhatsApp",
                                                                      [por_cli[venc[0]["cliente"]["codigo"]]["vencidos"][0]["numero"]], [], "Maria"))["texto"],
       "a assinatura configurada entra no texto")

    # --- registro: hora da base, persistência, planilha intocada, fila mexe
    arq = registro.arquivo()
    ok(os.path.dirname(arq) != os.path.dirname(BASE) or os.path.basename(arq) != "Base_bruta.xlsx",
       "o registro mora em arquivo próprio (%s), nunca na planilha" % os.path.relpath(arq, PASTA) if not arq.startswith(tempfile.gettempdir()) else
       "o registro mora em arquivo próprio, fora da planilha")
    ok(registro.listar() == [], "partindo de registro vazio")
    cod = venc[min(2, len(venc) - 1)]["cliente"]["codigo"]  # terceiro da fila (ou o último, se a fila for menor)
    f0 = next(f for f in p0["fila"] if f["cliente"]["codigo"] == cod)
    r = por_cli[cod]
    nums = [t["numero"] for t in r["vencidos"]][:1]
    valor = sum(t["valor"] for t in r["vencidos"] if t["numero"] in nums)
    rid, quando = registro.registrar(ref, cod, "WhatsApp", "objetiva", regua.nome_tom("objetiva"), valor, nums, "texto enviado")
    ok(quando.date() == ref and quando.date() != datetime.now().date(),
       "o registro nasce na data da base (%s), não na data do computador" % quando.date().strftime("%d/%m/%Y"))
    ok(quando == agora(ref), "a hora do registro é a do relógio da base (%s)" % quando.strftime("%H:%M"))
    p1 = servico.painel()
    f1 = next(f for f in p1["fila"] if f["cliente"]["codigo"] == cod)
    ok(f1["cobrado_recente"] and f1["cobranca"]["origem"] == "Central" and f1["cobranca"]["valor"] == valor,
       "a tela Hoje passa a ver a cobrança registrada (origem Central, valor %s)" % reais(valor))
    ok(f1["posicao"] > f0["posicao"] and abs(f1["score"] - f1["score_base"] * motor.FATOR_COBRADO_RECENTE) < 1e-9,
       "quem foi cobrado desce na fila (posição %d -> %d) e o score é multiplicado pelo fator da regra das 48h" % (f0["posicao"], f1["posicao"]))
    ok(sum(f["vencido"] for f in p1["fila"]) == resumo["vencido"] and len(p1["fila"]) == len(p0["fila"]),
       "registrar não muda quanto está vencido nem quem está na fila")
    _, fila_tarde = motor.calcular(BASE, extras=registro.como_cobrancas(), leitura={r_["cliente"]["codigo"]: r_ for r_ in rs}, agora=quando + timedelta(hours=48, minutes=1))
    ft = next(f for f in fila_tarde if f["cliente"]["codigo"] == cod)
    _, fila_cedo = motor.calcular(BASE, extras=registro.como_cobrancas(), leitura={r_["cliente"]["codigo"]: r_ for r_ in rs}, agora=quando + timedelta(hours=47, minutes=59))
    fc = next(f for f in fila_cedo if f["cliente"]["codigo"] == cod)
    ok(fc["cobrado_recente"] and not ft["cobrado_recente"], "a regra das 48 horas vale até 47h59 e solta depois disso")
    ok(len(registro.listar()) == 1 and registro.listar()[0]["mensagem"] == "texto enviado"
       and registro.listar()[0]["quando"] == quando, "o registro é lido de volta do arquivo, com a mensagem e a hora")
    reg_json = json.load(open(arq, encoding="utf-8"))
    ok(reg_json["registros"][0]["quando"].startswith(ref.isoformat()), "o arquivo guarda a data da base")
    html_hist = pagina_cobranca.historico_pagina(p1, agora(ref))
    ok("Registrada na Central" in html_hist and "Planilha da empresa" in html_hist and "dados/cobrancas_registradas.json" in html_hist
       and "Base_bruta.xlsx" in html_hist and reais(valor) in html_hist,
       "a tela Cobranças feitas mostra as duas fontes, diz de onde vem cada uma e traz o valor registrado")
    ok(ultimo_registrado_aparece(pagina, p1), "a tela Hoje diz que a última cobrança foi registrada na Central")
    ok(registro.remover(rid) and registro.listar() == [], "desfazer apaga só o registro da Central")
    p2 = servico.painel()
    ok([(f["posicao"], f["cliente"]["codigo"], round(f["score"], 9)) for f in p2["fila"]]
       == [(f["posicao"], f["cliente"]["codigo"], round(f["score"], 9)) for f in p0["fila"]],
       "sem registro, a fila volta exatamente ao que era")
    ok(hashlib.sha256(open(BASE, "rb").read()).hexdigest() == hash_antes, "Base_bruta.xlsx continua byte a byte igual")
    registro.salvar_assinatura("Maria")
    ok(registro.assinatura() == "Maria", "a assinatura é guardada em configuração própria")

    # --- números novos da semana, conta independente
    _, _, titulos, _ = motor.carregar(BASE)
    ini = ref - timedelta(days=6)
    ok(resumo["entrou_7d"] == sum(t["valor"] for t in titulos if t["pagamento"] and ini <= t["pagamento"] <= ref),
       "entrou na semana: bate com conta independente nos títulos (%s)" % reais(resumo["entrou_7d"]))
    ok(resumo["venceu_7d_aberto"] == sum(t["valor"] for t in titulos if ini <= t["vencimento"] <= ref and not t["pagamento"]),
       "venceu na semana e não entrou: bate com conta independente (%s)" % reais(resumo["venceu_7d_aberto"]))
    html_hoje = pagina.hoje(resumo, fila)
    ok(reais_est(resumo["entrou_7d"]) in html_hoje and reais_est(resumo["venceu_7d_aberto"]) in html_hoje,
       "a tela Hoje mostra os mesmos números da semana (nos indicadores do topo, sem centavo)")

    # --- relatório
    agora_ = agora(ref)
    ctx = relatorio.contexto(p0, prev, agora_)
    blocos = relatorio.blocos(p0, prev, agora_)
    texto = "\n".join(" ".join(str(x) for x in b[1:]) for b in blocos)
    est = previsao.reais_est
    tot = risco.totais(rs)
    esperados = [reais(resumo["entrou_7d"]), reais(resumo["vencido"]), reais(resumo["a_vencer"]), reais(resumo["venceu_7d_aberto"]),
                 reais(tot["saldo"]), est(tot["valor_em_risco"]), est(prev["total_esp"]), est(prev["total_otim"]),
                 est(prev["total_cons"]), est(prev["diferenca"]), reais(prev["total_planilha"]), est(resumo["entrou_media_8s"])]
    ok(all(e in texto for e in esperados), "o relatório traz, nas frases, os números que as telas mostram (%d conferidos)" % len(esperados))
    html_risco = pagina_risco.lista(ref, rs, p0["n_lista"])
    ok(est(tot["valor_em_risco"]) in html_risco and reais_est(tot["saldo"]) in html_risco
       and est(tot["valor_em_risco"]) in texto and reais(tot["saldo"]) in texto,
       "valor em risco e saldo do relatório saem do mesmo total que a tela Risco mostra (o relatório só arredonda a estimativa)")
    ok(est(prev["total_esp"]) in pagina_previsao.pagina(ref, rs, prev) and est(prev["diferenca"]) in pagina_previsao.pagina(ref, rs, prev),
       "esperado e diferença do relatório são os da tela Previsão")
    acoes = [b for b in blocos if b[0] == "decisao"]
    vr = {c["nome"]: c["valor_em_risco"] for c in ctx["clientes"]}
    ordem = [vr[next(n for n in vr if b[2].startswith(n))] for b in acoes]
    ok(ordem == sorted(ordem, reverse=True),
       "as decisões vêm em ordem de valor em risco, a mesma da tela Risco (%d decisões)" % len(acoes))
    ok(blocos[-1][0] == "par" and "ação esta semana" in blocos[-1][1] and (not acoes or blocos[-2][0] == "decisao"),
       "o relatório termina nas decisões")
    palavras = len(texto.split())
    ok(150 <= palavras <= 1800, "texto de %d palavras: cabe em uns quatro a cinco minutos de leitura" % palavras)
    ok(_sem_marcas(texto), "sem marca de modelo não preenchida no relatório")
    import io
    buf = io.BytesIO()
    docx_min.salvar(blocos, buf)
    z = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    partes = {n: z.read(n) for n in z.namelist()}
    ok(all(ET.fromstring(v) is not None for v in partes.values()), ".docx é um zip com XML bem formado (%s)" % ", ".join(sorted(partes)))
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    doc = ET.fromstring(partes["word/document.xml"])
    texto_docx = "".join(t.text or "" for t in doc.iter(ns + "t"))
    ok(all(e in texto_docx for e in esperados), "os números do relatório estão no arquivo .docx")
    ok("Content_Types" in "".join(z.namelist()) and "word/styles.xml" in z.namelist(), ".docx traz tipos e estilos")
    _ = pagina_relatorio.pagina(ref, blocos)
    ok(reais(resumo["entrou_7d"]) in _, "a tela Relatório mostra o mesmo texto")

    # --- sem IA, sem rede, texto em um lugar só
    proibidos = ("urllib.request", "http.client", "import requests", "import socket", "anthropic", "openai", "smtplib", "ftplib",
                 "imaplib", "poplib", "urlopen", "xmlrpc", "websocket")
    achou = []
    for nome in sorted(os.listdir(PASTA)):
        if nome.endswith(".py") and nome not in ("conferir.py",):
            src = open(os.path.join(PASTA, nome), encoding="utf-8").read()
            for pr in proibidos:
                if pr in src:
                    achou.append("%s:%s" % (nome, pr))
    ok(not achou, "nenhum módulo importa biblioteca de rede, e-mail ou IA%s" % ("" if not achou else " (" + ", ".join(achou) + ")"))
    sai_do_lugar = []
    for nome in ("regua.py", "relatorio.py", "pagina_cobranca.py", "pagina_relatorio.py", "servico.py", "registro.py", "central.py"):
        src = open(os.path.join(PASTA, nome), encoding="utf-8").read()
        for frase_cliente in ("Olá,", "Fico no aguardo", "Um abraço", "Preciso que você"):
            if frase_cliente in src:
                sai_do_lugar.append("%s:%s" % (nome, frase_cliente))
    ok(not sai_do_lugar, "o texto para o cliente e para a diretoria só é escrito em redacao.py (troca do redator num lugar só)")
    ok(isinstance(redacao.REDATOR, redacao.RedatorPorRegras) and callable(getattr(redacao.REDATOR, "cobranca", None))
       and callable(getattr(redacao.REDATOR, "relatorio", None)), "REDATOR expõe cobranca() e relatorio(), o contrato de troca")


def auditoria(ok, ref, resumo, rs, prev):
    """6ª parte, nascida da auditoria: números refeitos por outro caminho, de tela para tela, e escrita/formato."""
    import subprocess
    import threading
    from http.server import ThreadingHTTPServer

    import central
    import pagina_previsao
    import pagina_risco
    import previsao
    import regua
    import relatorio
    import risco as risco_
    import servico
    from frases import _dias, arred, pct1, reais, reais_est
    from pagina_risco import _indices_rotulados
    from relogio import agora

    print("6. Auditoria: de tela para tela, formato e recontagem independente")
    p0 = servico.painel()
    por_cli = p0["risco_por_cliente"]

    # --- uma só conta de risco, com um só nome
    ok(all(f["indice"] == por_cli[f["cliente"]["codigo"]]["indice"] and abs(f["risco"] * 100 - f["indice"]) < 1e-9 for f in p0["fila"]),
       "o 'risco' da fila de Hoje é exatamente o índice de risco da tela Risco, cliente por cliente")
    import inspect
    import motor as motor_
    ok("perfil_pagamento" not in inspect.getsource(motor_) and "atipico" not in inspect.getsource(motor_),
       "motor.py não tem mais um cálculo de risco próprio")

    # --- o mesmo cliente com o mesmo número em telas diferentes
    import pagina as pagina_
    iguais = True
    detalhes = []
    for f in p0["fila"]:
        r = por_cli[f["cliente"]["codigo"]]
        p = r["pag"]
        hoje_txt = pagina_.frase(f) if hasattr(pagina_, "frase") else ""
        if "piorou" in r["tags"]:
            antes, agora_ = _dias(p["base_med"]), _dias(p["rec_med"])
            ficha = pagina_risco.ficha(ref, r).replace(" ", " ")
            for nome_tela, txt in (("Hoje", hoje_txt), ("ficha de Risco", ficha)):
                if agora_ not in txt or antes not in txt:
                    iguais = False
                    detalhes.append("%s não traz %s / %s" % (nome_tela, agora_, antes))
            prev_txt = [c["frase"] for c in prev["clientes"] if c["cliente"]["codigo"] == r["cliente"]["codigo"]][0]
            if agora_ not in prev_txt or antes not in prev_txt:
                iguais = False
                detalhes.append("Previsão não traz %s / %s" % (agora_, antes))
            _, razoes = regua.escolher(ref, r, regua.contatos_do_cliente(p0["cobrancas"], r["cliente"]["codigo"]))
            if agora_ not in razoes[0] or antes not in razoes[0]:
                iguais = False
                detalhes.append("Régua não traz %s / %s" % (agora_, antes))
    ok(iguais, "quem piorou é descrito com o mesmo atraso (antes e agora) em Hoje, Risco, Previsão e Régua%s"
       % ("" if iguais else ": " + "; ".join(detalhes)))

    # --- faixa do gráfico = número do quadro, em toda ficha
    faixa_ok = True
    for r in rs:
        h = pagina_risco.ficha(ref, r).replace(" ", " ")
        leg = re.search(r"padrão histórico \(80% dos pagamentos entre (-?\d+) e (-?\d+) dias\)", h)
        kpi = re.search(r"80% dos pagamentos</span><b[^>]*>entre (-?\d+) e (-?\d+) dias", h)
        if leg and kpi and leg.groups() != kpi.groups():
            faixa_ok = False
    ok(faixa_ok, "em toda ficha, a faixa '80% dos pagamentos' do gráfico é a mesma do quadro de números")
    ok(all(("%d pagamentos" % r["pag"]["n_ns"]) in pagina_risco.ficha(ref, r) for r in rs if r["pag"]["ok"]),
       "a contagem de pagamentos escrita em 'atraso habitual' é a dos pagamentos que entraram na conta")

    # --- "limite": uma só conta (saldo em aberto / limite), com o mesmo número em Hoje e na ficha
    lim_ok = True
    for f in p0["fila"]:
        r = por_cli[f["cliente"]["codigo"]]
        n = round(100 * r["ocupacao"])
        lim_ok &= ("ocupa %d%% do limite" % n) in pagina_.hoje(resumo, [f]) and ("%d%% de" % n) in pagina_risco.ficha(ref, r)
    ok(lim_ok, "o '% do limite' de cada cliente é o mesmo em Hoje e na ficha de Risco (saldo em aberto / limite)")
    # --- "há quanto tempo" com a mesma régua de tempo em Hoje e em Cobranças feitas
    import pagina_cobranca as pc_
    from frases import _tempo
    tempo_ok = True
    for f in p0["fila"]:
        if f["cobranca"]:
            tempo_ok &= ("há %s" % _tempo(f["horas_desde_cobranca"])) in pc_.historico_pagina(p0, agora(ref)) or f["horas_desde_cobranca"] is None
    ok(tempo_ok, "o 'há quanto tempo' da última cobrança usa a mesma régua (horas até 48h, depois dias) em Hoje e em Cobranças feitas")
    # --- indicadores do topo sem centavo
    kpi_hoje = re.findall(r'<span class="(?:grande|v)"[^>]*>([^<]+)</span>', pagina_.hoje(resumo, p0["fila"]))
    ok(kpi_hoje and all("," not in k for k in kpi_hoje), "indicadores do topo de Hoje sem centavo (%s)" % ", ".join(k.replace("\u00a0", " ") for k in kpi_hoje))
    top_ficha = all("," not in re.search(r'Saldo em aberto</span><b>([^<]+)</b>', pagina_risco.ficha(ref, r)).group(1) for r in rs)
    ok(top_ficha, "indicadores do topo da ficha de Risco sem centavo")
    hero = [a or b for a, b in re.findall(r'<span class="grande"[^>]*>([^<]+)</span>|<div><b>(R\$[^<]+)</b>', pagina_previsao.pagina(ref, rs, prev))]
    ok(hero and all("," not in h_ for h_ in hero), "indicadores do topo da Previsão sem centavo (%s)" % ", ".join(h_.replace("\u00a0", " ") for h_ in hero))

    # --- estimativa sem centavo, valor fechado com centavo
    tot = risco_.totais(rs)
    html_risco = pagina_risco.lista(ref, rs, p0["n_lista"])
    ok(all(reais_est(r["valor_em_risco"]) in html_risco for r in rs) and reais_est(tot["valor_em_risco"]) in html_risco,
       "valor em risco (estimativa) aparece sem centavo na lista de Risco, igual ao do relatório")
    ok(not re.search(r"R\$ [\d.]+,(?!00)\d\d", html_risco + pagina_previsao.pagina(ref, rs, prev)),
       "nenhum centavo quebrado (não-zero) em número que é estimativa, nas telas Risco e Previsão")
    ok(reais_est(resumo["entrou_media_8s"]) in pagina_.hoje(resumo, p0["fila"]), "a média das 8 semanas (estimativa) aparece sem centavo em Hoje")

    # --- formato: nada de 'R$' separado do valor, nada de ponto decimal, nada de botão dentro de link
    paginas = {"hoje": pagina_.hoje(resumo, p0["fila"]), "risco": html_risco, "previsao": pagina_previsao.pagina(ref, rs, prev)}
    paginas.update({"ficha %d" % r["cliente"]["codigo"]: pagina_risco.ficha(ref, r) for r in rs})
    import pagina_cobranca
    import pagina_relatorio
    paginas["regua"] = pagina_cobranca.regua_pagina(p0, "")
    paginas["cobrancas"] = pagina_cobranca.historico_pagina(p0, agora(ref))
    paginas["relatorio"] = pagina_relatorio.pagina(ref, relatorio.blocos(p0, prev, agora(ref)))
    corpo = {k: re.sub(r"<style.*?</style>|<script.*?</script>", "", v, flags=re.S) for k, v in paginas.items()}
    ok(not [k for k, v in corpo.items() if re.search(r"R\$ \d", re.sub(r"<[^>]+>", " ", v))],
       "em nenhuma tela o 'R$' fica separado do valor por espaço que quebra linha")
    ok(not [k for k, v in corpo.items() if re.search(r"\b\d+\.\d(?!\d)\s*(%|vezes)", re.sub(r"<[^>]+>", " ", v))],
       "percentuais e razões usam vírgula decimal, nunca ponto")
    ok(not [k for k, v in paginas.items() if re.search(r"<a [^>]*>\s*<button", v)], "nenhum botão dentro de link")
    plur = [k for k, v in corpo.items() if re.search(r"(?<![\d,.])1 (dias|títulos|contatos|clientes|registros|pagamentos)\b|\b(?:[2-9]|\d\d) (dia|título|contato|cliente|registro|pagamento)\b(?!s)", re.sub(r"<[^>]+>", " ", v))]
    ok(not plur, "concordância de número: nenhum '1 dias' nem '2 título' em nenhuma tela%s" % ("" if not plur else " (" + ", ".join(plur) + ")"))
    jarg = [k for k, v in corpo.items() if re.search(r"\b(mediana|score|previsao\.py|premissas minhas)\b", re.sub(r"<[^>]+>", " ", v))]
    ok(not jarg, "nenhuma tela usa 'mediana', 'score', nome de arquivo ou primeira pessoa de analista%s" % ("" if not jarg else " (" + ", ".join(jarg) + ")"))
    solto = [k for k in ("previsao", "cobrancas", "risco") if len(re.findall(r"<table", corpo[k]))
             != len(re.findall(r'<div class="tabela-wrap[ "][^>]*>\s*<table', corpo[k])) + len(re.findall(r'<table class="linhas"', corpo[k]))]
    ok(not solto, "toda tabela de Previsão, Cobranças e Risco está dentro de quadro que rola ou vira cartão no celular")
    ok(all(all(b - a >= 2 for a, b in zip(ix, ix[1:])) for ix in (_indices_rotulados([(2024 + (m0 + i) // 12, (m0 + i) % 12 + 1) for i in range(n)])
                                                                   for m0 in range(12) for n in range(8, 26))),
       "rótulos do eixo dos gráficos nunca ficam colados (em nenhuma combinação de mês inicial e tamanho)")
    ok(all(len(set(ix)) == len(ix) for ix in (_indices_rotulados([(2024, m) for m in range(1, 13)]),)), "rótulos do eixo sem repetição")

    # --- recontagem independente (precisa do pacote openpyxl só para conferir; a Central em si não precisa)
    try:
        import openpyxl  # noqa: F401
        tem_openpyxl = True
    except ImportError:
        tem_openpyxl = False
    if not tem_openpyxl:
        print("  (pulada)  recontagem independente: pacote openpyxl não instalado; a Central não precisa dele, só esta conferência")
        return
    os.environ["CENTRAL_HORA"] = "10:00"
    srv = ThreadingHTTPServer(("127.0.0.1", 0), central.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    porta = str(srv.server_address[1])
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for nome, desc in (("comparar.py", "recontagem independente direto na planilha (openpyxl) bate com o que está na tela, e as telas batem entre si"),
                       ("escrita.py", "varredura de escrita em todas as telas e em 192 textos de cobrança (concordância, pontuação, centavo, jargão)")):
        r_ = subprocess.run([sys.executable, os.path.join(PASTA, "independente", nome), porta], capture_output=True, text=True,
                            encoding="utf-8", env=env, timeout=300)
        saida = (r_.stdout or "").strip().splitlines()
        erro = (r_.stderr or "").strip().splitlines()
        ok(r_.returncode == 0, desc + (" — " + saida[-1] if saida else "")
           + ("" if r_.returncode == 0 else "\n        " + "\n        ".join(saida[-6:] + erro[-6:])))
    srv.shutdown()


def nada_sumiu(ok, ref, resumo, rs, prev):
    """7ª parte: o INVENTÁRIO do que não pode sumir de cada tela (inventario_telas.py). Nasceu do pedido de refazer o visual
    sem perder informação: encurtar, juntar e guardar atrás de um clique pode; sumir alerta, link, frase ou número, não."""
    import inventario_telas as inv
    import pagina as pagina_
    import pagina_cobranca
    import pagina_previsao
    import pagina_relatorio
    import pagina_risco
    import regua
    import registro
    import relatorio
    import servico
    from relogio import agora

    print("7. Nada sumiu: o inventário do que não pode sumir de cada tela")
    p = servico.painel()
    blocos = relatorio.blocos(p, prev, agora(p["ref"]))
    base = {"painel": p, "prev": prev, "blocos": blocos, "resumo_contatos": registro.resumo_contatos(p["cobrancas"], agora(p["ref"])),
            "rotulos": {k: v[0] for k, v in pagina_risco.ROTULOS.items()}}

    def texto_padrao(cod):
        r = p["risco_por_cliente"][cod]
        sug = regua.escolher(p["ref"], r, regua.contatos_do_cliente(p["cobrancas"], cod))[0]
        return pagina_cobranca.texto_da_cobranca(p["ref"], p, cod, sug, "WhatsApp", [t["numero"] for t in r["vencidos"]], "")[0]["texto"]
    base["texto_padrao"] = texto_padrao
    paginas = {
        "hoje": pagina_.hoje(p["resumo"], p["fila"], p["avisos"]),
        "regua": pagina_cobranca.regua_pagina(p, ""),
        "cobrancas": pagina_cobranca.historico_pagina(p, agora(p["ref"])),
        "risco": pagina_risco.lista(p["ref"], p["rs"], p["n_lista"], p["avisos"]),
        "previsao": pagina_previsao.pagina(p["ref"], p["rs"], prev),
        "relatorio": pagina_relatorio.pagina(p["ref"], blocos),
    }
    for tela, html in paginas.items():
        falt = inv.faltando(tela, html, base)
        n = len(inv.exigidos(tela, base))
        ok(not falt, "tela %s: os %d itens do inventário estão na página%s" % (
            tela, n, "" if not falt else ". SUMIU: " + "; ".join("%s (%s)" % (d, c) for c, d, _ in falt[:5])))
    falt_fichas, n_fichas = [], 0
    for r in p["rs"]:
        c = dict(base, r=r)
        n_fichas += len(inv.exigidos("ficha", c))
        falt_fichas += [(r["cliente"]["nome"],) + f for f in inv.faltando("ficha", pagina_risco.ficha(p["ref"], r), c)]
    ok(not falt_fichas, "as %d fichas de cliente: os %d itens do inventário estão na página%s" % (
        len(p["rs"]), n_fichas, "" if not falt_fichas else ". SUMIU: " + "; ".join("%s: %s" % (n, d) for n, _, d, _ in falt_fichas[:5])))


def _lum(hexa):
    h = hexa.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contraste(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def visual_e_arquivo(ok, ref, resumo, rs, prev):
    """8ª parte: as regras do visual Aurora que dá para provar só com o HTML, e o ARQUIVO ÚNICO (gerar_arquivo_unico.py).
    O que depende de um navegador de verdade (cabe sem rolar, nada em cima de nada) está em ferramentas/navegador/conferir_visual.py."""
    import base64
    import inventario_telas as inv
    import gerar_arquivo_unico as gau
    import pagina as pagina_
    import pagina_relatorio
    import regua
    import registro
    import relatorio
    import risco as risco_
    import servico
    from frases import arred, faixa_risco, reais, reais_est
    from relogio import agora

    print("8. Visual (regras do tema Aurora) e arquivo único")
    p = servico.painel()
    hoje = pagina_.hoje(p["resumo"], p["fila"], p["avisos"], p["rs"], p["n_lista"])
    # --- Hoje
    pct = arred(100 * resumo["vencido"] / resumo["aberto"]) if resumo["aberto"] else 0
    ok(('%d%%</b>' % pct) in hoje and ('%d%% do que está em aberto já venceu' % pct) in hoje, "Hoje: o anel diz %d%% (vencido / em aberto), derivado dos dois números do próprio resumo" % pct)
    cartoes = re.findall(r'<article class="cartao[^"]*".*?</article>', hoje, flags=re.S)
    ok(len(cartoes) == len(p["fila"]) and all('class="l1 motivo"' in c and 'class="r2"' in c and all('class="r%d"' % k in c or 'class="r%d ' % k in c for k in (1, 3, 4)) for c in cartoes),
       "Hoje: cada cliente da fila tem as quatro fileiras (nome/valor, quem e telefone, a frase, botões) (%d cartões)" % len(cartoes))
    ok(len(re.findall(r'class="cartao vidro primeiro', hoje)) == (1 if cartoes else 0), "Hoje: só o 1º da fila tem o destaque de 'primeiro'")
    ok(all(re.search(r"Risco (alto|médio|baixo)", c) for c in cartoes), "Hoje: a cor de gravidade de cada cliente vem sempre com a palavra (Risco alto/médio/baixo)")
    ok(all(("Risco %s" % faixa_risco(f["indice"])[1].split()[1]) in c for f, c in zip(p["fila"], cartoes)),
       "Hoje: a palavra de gravidade de cada cliente é a da faixa do índice (60+ alto, 30 a 59 médio, abaixo disso baixo)")
    desc = risco_.descobertas(p["rs"], p["n_lista"])
    ok(len(desc) <= 3 and all(('href="/risco/%d"' % d["codigo"]) in hoje for d in desc), "Hoje: até 3 descobertas no alto, cada uma com link para a ficha (%d nesta base)" % len(desc))
    ok(all(n in hoje for n in (reais_est(resumo["vencido"]), reais_est(resumo["aberto"]))), "Hoje: o número grande e o de 'em aberto' são os do resumo")
    # --- Relatório: todo valor em reais na cor do dinheiro
    rel = pagina_relatorio.pagina(ref, relatorio.blocos(p, prev, agora(ref)))
    papel = re.search(r'<article class="papel vidro">(.*?)</article>', rel, flags=re.S).group(1)
    sem_span = re.sub(r'<span class="din">.*?</span>', "", papel)
    ok("R$" not in sem_span and "R$" in papel, "Relatório: todos os valores em reais estão na cor do dinheiro (%d valores)" % papel.count('class="din"'))
    # --- contraste de cor (WCAG): texto e cores de sinal sobre o fundo mais claro que o tema produz
    css = open(os.path.join(PASTA, "estatico", "tema.css"), encoding="utf-8").read()
    tok = dict(re.findall(r"--([a-z0-9]+):(#[0-9a-fA-F]{6})", css))
    fundos = ["#05071a", "#150c3b", "#211f52"]  # fundo escuro, fundo roxo do degradê, vidro sobre a mancha de luz mais forte
    ruins = ["%s %.1f" % (k, min(_contraste(tok[k], f) for f in fundos)) for k in ("tx", "tx2", "tx3", "crit", "aten", "ok", "din", "link")
             if min(_contraste(tok[k], f) for f in fundos) < 4.5]
    ok(not ruins, "contraste: texto e cores de sinal passam de 4,5:1 sobre o fundo mais claro do tema%s" % ("" if not ruins else " (abaixo: " + ", ".join(ruins) + ")"))
    ok("prefers-reduced-motion" in css and "backdrop-filter" in css and "@supports" in css, "tema: respeita 'reduzir movimento' e tem saída para vidro sem suporte")
    # --- arquivo único
    final, ref2, paginas, p2, prev2, blocos2 = gau.gerar()
    ok(len(final.encode("utf-8")) < 5 * 1024 * 1024, "arquivo único: um arquivo só, %.0f KB" % (len(final.encode("utf-8")) / 1024))
    ok(not re.findall(r"""(?:src|href)=["']https?://|url\(\s*["']?https?:|@import""", final), "arquivo único: nenhum endereço de internet, nada carregado de fora")
    ok(all("/estatico/" not in final for _ in [0]), "arquivo único: CSS, JavaScript e fontes estão dentro do arquivo (nenhum /estatico/)")
    ok(len(final.split("</template>")) - 1 == len(paginas), "arquivo único: as %d telas (6 + %d fichas) estão dentro" % (len(paginas), len(p["rs"])))
    casca = re.sub(r"<template.*?</template>", "", final, flags=re.S)
    tpl = {m.group(1): m.group(2) for m in re.finditer(r'<template id="([^"]+)" data-tela="[^"]*">(.*?)</template>', final, flags=re.S)}
    blocos = relatorio.blocos(p2, prev2, agora(ref2))
    base = {"painel": p2, "prev": prev2, "blocos": blocos, "resumo_contatos": registro.resumo_contatos(p2["cobrancas"], agora(ref2)),
            "rotulos": {k: v[0] for k, v in __import__("pagina_risco").ROTULOS.items()}}

    def texto_padrao(cod):
        r = p2["risco_por_cliente"][cod]
        sug = regua.escolher(p2["ref"], r, regua.contatos_do_cliente(p2["cobrancas"], cod))[0]
        return __import__("pagina_cobranca").texto_da_cobranca(p2["ref"], p2, cod, sug, "WhatsApp", [t["numero"] for t in r["vencidos"]], registro.assinatura())[0]["texto"]
    base["texto_padrao"] = texto_padrao
    sumiu = []
    for tela, tid in (("hoje", "p-hoje"), ("regua", "p-regua"), ("cobrancas", "p-cobrancas"), ("risco", "p-risco"), ("previsao", "p-previsao"), ("relatorio", "p-relatorio")):
        falt = [f for f in inv.faltando(tela, casca + tpl[tid], base, link=gau.href_arquivo) if f[1] not in ("botão desfazer", "baixar o Word")]
        sumiu += ["%s: %s" % (tela, f[1]) for f in falt]
    for r in p2["rs"]:
        falt = inv.faltando("ficha", casca + tpl["p-risco-%d" % r["cliente"]["codigo"]], dict(base, r=r), link=gau.href_arquivo)
        sumiu += ["ficha %s: %s" % (r["cliente"]["nome"], f[1]) for f in falt]
    ok(not sumiu, "arquivo único: tudo o que o inventário exige de cada tela continua nela%s" % ("" if not sumiu else ". SUMIU: " + "; ".join(sumiu[:5])))
    m = re.search(r"window\.CENTRAL_TEXTOS = (\{.*?\});\n", final, flags=re.S)
    textos = json.loads(m.group(1).replace("<\\/", "</"))
    ok(len(textos) == len(p2["fila"]) and all(len(v) == len(regua.TONS) and all(len(c) == 3 for c in v.values()) for v in textos.values()),
       "arquivo único: os textos de cobrança de todos os tons e canais de todos os clientes estão dentro (%d textos)" % sum(len(c) for v in textos.values() for c in v.values()))
    desl = tpl["p-regua"]
    ok(desl.count("Desligado neste arquivo") >= 2 and "disabled" in desl, "arquivo único: o que não funciona sem a Central está desligado e escrito na tela por quê")
    docx = re.search(r'href="data:application/vnd\.openxmlformats-officedocument\.wordprocessingml\.document;base64,([^"]+)"', tpl["p-relatorio"])
    ok(docx and base64.b64decode(docx.group(1))[:2] == b"PK", "arquivo único: o relatório em Word vai dentro, como arquivo de verdade")
    ok("Ele não se atualiza sozinho" in final and "Retrato de" in final, "arquivo único: diz na tela que é um retrato e que não se atualiza sozinho")


def ultimo_registrado_aparece(pagina, p):
    return "Registrada na Central" in pagina.hoje(p["resumo"], p["fila"])


def main():
    os.environ["CENTRAL_HORA"] = "00:00"  # o retrato gravado foi tirado à meia-noite da data da base
    pasta_dados = tempfile.mkdtemp(prefix="central_conferencia_")
    os.environ["CENTRAL_DADOS"] = pasta_dados  # a conferência nunca toca nos registros de verdade
    falhas = []

    def ok(cond, msg):
        print(("  ok    " if cond else "  FALHOU ") + msg)
        if not cond:
            falhas.append(msg)

    snap, resumo, fila, ref, rs = instantaneo()
    if "--gravar" in sys.argv:
        if not _e_a_base_de_referencia():
            sys.exit("Recusado: o retrato só se grava com a planilha de referência (fixtures/Base_2026-08.xlsx). "
                     "Regravar com outra planilha apagaria a prova de que as telas não mudaram de número.")
        with open(ARQ_BASE, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=1, sort_keys=True)
        print("Base gravada em conferencia_base.json")
        return

    print("1. Verificações internas (assert de motor.py e risco.py): passaram, pois o cálculo terminou.")

    modo_ref = _e_a_base_de_referencia()
    print("(modo %s: planilha %s)" % ("REFERÊNCIA" if modo_ref else "BASE NOVA", os.path.relpath(BASE, PASTA) if BASE.startswith(PASTA) else BASE))
    print("2. Telas Hoje e Risco contra a base gravada")
    if not modo_ref:
        print("  (não se aplica: esta planilha não é a de referência, então os números mudaram de verdade. Para provar que uma "
              "mudança de tela não mexeu em número: CENTRAL_BASE=fixtures/Base_2026-08.xlsx python conferir.py)")
    elif os.path.exists(ARQ_BASE):
        base = json.load(open(ARQ_BASE, encoding="utf-8"))
        atual = json.loads(json.dumps(snap, sort_keys=True))
        dif = list(_diff(base, atual))
        nao_declaradas = [d for d in dif if not _declarada(d)]
        ok(not nao_declaradas, "Hoje e Risco idênticos à base gravada, salvo as %d mudanças declaradas"
           % len([d for d in dif if _declarada(d)]) + ("" if not nao_declaradas else ": mudou sem declarar " + ", ".join(nao_declaradas[:6])))
        ok(all(any(re.match(rx, d) for d in dif) for rx, _ in DECLARADAS), "cada mudança declarada de fato aconteceu (nenhuma declaração sobrando)")
        bc, ac = base["risco"]["clientes"], atual["risco"]["clientes"]
        ok(all(bc[k][f] == ac[k][f] for k in bc for f in ("indice", "valor_em_risco", "saldo")) and base["risco"]["ordem"] == atual["risco"]["ordem"],
           "Risco: índice, valor em risco, saldo e ordem de cada cliente são exatamente os do retrato original")
        ok(all([x[:2] for x in bc[k]["fatores"]] == [x[:2] for x in ac[k]["fatores"]] for k in bc),
           "Risco: os pontos de todos os fatores de todos os clientes são os mesmos; só as frases mudaram")
        ok(sorted((p[1], p[2]) for p in base["hoje"]["fila"]) == sorted((p[1], p[2]) for p in atual["hoje"]["fila"]),
           "Hoje: os mesmos clientes com o mesmo valor vencido de antes (só a ordem pode ter mudado)")
        ok({k: v for k, v in base["hoje"]["resumo"].items()} == {k: atual["hoje"]["resumo"][k] for k in base["hoje"]["resumo"]},
           "Hoje: todos os números do resumo que já existiam continuam iguais")
    else:
        ok(False, "conferencia_base.json não existe")

    print("3. Telas não se contradizem")
    por_cli = {r["cliente"]["codigo"]: r for r in rs}
    ok(sum(r["saldo"] for r in rs) == resumo["aberto"], "saldo em aberto: soma por cliente (Risco) = total (Hoje)")
    ok(sum(r["vencido"] for r in rs) == resumo["vencido"], "vencido: soma por cliente (Risco) = total (Hoje)")
    ok(all(por_cli[f["cliente"]["codigo"]]["vencido"] == f["vencido"] for f in fila), "vencido de cada cliente igual nas duas telas")
    ok(all(isinstance(r["saldo"], int) and isinstance(r["valor_em_risco"], int) for r in rs), "valores em centavos são inteiros")

    print("4. Previsão de caixa")
    try:
        import previsao
    except ImportError:
        print("  (previsao.py ainda não existe)")
    else:
        prev = previsao.prever(ref, rs)
        for msg, cond in previsao.conferencias(ref, rs, prev, resumo):
            ok(cond, msg)

    if not sys.argv[1:]:
        import previsao as _pv
        os.environ["CENTRAL_HORA"] = "10:00"  # hora de trabalho, para o teste do registro
        prev_ = _pv.prever(ref, rs)
        rodada4(ok, ref, resumo, fila, rs, prev_, pasta_dados)
        auditoria(ok, ref, resumo, rs, prev_)
        nada_sumiu(ok, ref, resumo, rs, prev_)
        visual_e_arquivo(ok, ref, resumo, rs, prev_)

    print()
    if falhas:
        print("%d verificação(ões) falharam." % len(falhas))
        sys.exit(1)
    print("Todas as verificações passaram.")


if __name__ == "__main__":
    main()
