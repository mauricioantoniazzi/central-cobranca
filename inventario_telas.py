"""INVENTÁRIO do que não pode sumir de cada tela.

O dono pediu, antes de refazer o visual: "uma lista do que não pode sumir de cada tela (os alertas, os links, a frase que explica cada
cliente, os números) e conferir essa lista a cada rodada". Esta é a lista, escrita como código para a conferência poder cobrá-la.

Como funciona: `exigidos(tela, contexto)` devolve os itens que a tela TEM de conter, tirados dos DADOS (não do HTML antigo).
`faltando(tela, html, contexto)` devolve o que não está no HTML. "Está" quer dizer: aparece no texto da página, visível ou dentro de um bloco
fechado (<details>, painel escondido, textarea), porque o dono aceita encurtar, juntar e guardar atrás de um clique, mas não sumir.
Dinheiro estimado é cobrado pela parte inteira ("898.390"), para a tela poder mostrar com ou sem ",00"; dinheiro fechado (valor de título)
é cobrado inteiro, com centavo.

Categorias: alerta, frase (a explicação de cada cliente), numero, link, texto.
Para ver a lista em português: python inventario_telas.py
"""
import html as _html
import re
from datetime import datetime

import frases
import regua
from frases import arred, pct1, reais, reais_est

TELAS = ["hoje", "regua", "cobrancas", "risco", "ficha", "previsao", "relatorio"]
NAV = [("/", "Hoje"), ("/regua", "Régua de cobrança"), ("/cobrancas", "Cobranças feitas"), ("/risco", "Risco por cliente"),
       ("/previsao", "Previsão de caixa"), ("/relatorio", "Relatório da semana")]


def norm(texto):
    """Texto como a pessoa lê: sem tags, sem entidades, NBSP = espaço, espaços colapsados."""
    t = re.sub(r"<(style|script)\b.*?</\1>", " ", texto, flags=re.S | re.I)
    t = re.sub(r"</?(a|b|i|u|em|strong|span|small|mark|abbr|sup|sub|code|wbr)\b[^>]*>", "", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = _html.unescape(t).replace(" ", " ").replace("‑", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip()


def _int(c):
    """Centavos -> 'parte inteira de reais' como aparece na tela: 89839000 -> '898.390'."""
    return f"{(c + 50) // 100:,}".replace(",", ".")


def _d(d):
    return d.strftime("%d/%m/%Y")


def _dias(n):
    return "%d dia%s" % (n, "" if n == 1 else "s")


# --------------------------------------------------------------------------------------------- por tela
def _nav():
    return [("link", "menu: " + nome, 'href="%s"' % h) for h, nome in NAV] + [("texto", "menu: " + nome, nome) for _, nome in NAV]


def _avisos(p):
    return [("alerta", "aviso sobre a planilha", a) for a in p.get("avisos") or []]


def hoje(c):
    p, R = c["painel"], c["painel"]["resumo"]
    out = _nav() + _avisos(p)
    out += [("texto", "posição na data de referência", "posição em " + _d(R["data_ref"])),
            ("texto", "tamanho da base", "%d título%s de %d cliente%s, emitidos de %s a %s" % (
                R["n_titulos"], "" if R["n_titulos"] == 1 else "s", R["n_clientes"], "" if R["n_clientes"] == 1 else "s",
                _d(R["primeira_emissao"]), _d(R["ultima_emissao"])))]
    # indicadores (rótulo + número)
    for rotulo, valor in (("em aberto", R["aberto"]), ("já vencido", R["vencido"]), ("a vencer", R["a_vencer"]),
                          ("entrou nos últimos 7 dias", R["entrou_7d"]), ("venceu nos últimos 7 dias e não entrou", R["venceu_7d_aberto"])):
        out += [("texto", "indicador: " + rotulo, rotulo), ("numero", "indicador: " + rotulo, _int(valor))]
    out += [("numero", "média das 8 semanas anteriores", _int(R["entrou_media_8s"])),
            ("numero", "total que venceu nos últimos 7 dias", _int(R["venceu_7d"])),
            ("texto", "contagem de títulos em aberto", "%d título" % R["n_abertos"]),
            ("texto", "contagem de clientes com vencido", "%d cliente" % R["n_clientes_vencido"])]
    if not p["fila"]:
        out.append(("texto", "fila vazia", "Nenhum cliente tem título vencido"))
    for f in p["fila"]:
        cli, cod = f["cliente"], f["cliente"]["codigo"]
        nome = cli["nome"]
        out += [("texto", "%s: nome" % nome, nome),
                ("numero", "%s: valor vencido" % nome, reais(f["vencido"])),
                ("texto", "%s: quantos títulos e há quanto tempo" % nome, "%d título" % f["n"]),
                ("texto", "%s: mais antigo" % nome, "mais antigo há %s" % _dias(f["mais_antigo"])),
                ("texto", "%s: categoria e região" % nome, "%s" % cli["categoria"]),
                ("texto", "%s: região" % nome, cli["regiao"]),
                ("frase", "%s: frase que explica a posição" % nome, frases.frase(f)),
                ("texto", "%s: última cobrança" % nome, frases.ultimo_contato(f)),
                ("link", "%s: redigir a cobrança" % nome, 'href="/regua#c%d"' % cod),
                ("link", "%s: ficha de risco" % nome, 'href="/risco/%d"' % cod),
                ("numero", "%s: pontuação" % nome, "pontuação %d" % arred(f["score"])),
                ("numero", "%s: índice de risco usado" % nome, "índice de risco %d" % f["indice"])]
        if f["cobrado_recente"]:
            out.append(("alerta", "%s: cobrado nas últimas 48h (desceu na fila)" % nome, "cobrado nas últimas 48h"))
        for t in f["titulos"]:
            out += [("numero", "%s: título %s" % (nome, t["numero"]), t["numero"]),
                    ("numero", "%s: valor do título %s" % (nome, t["numero"]), reais(t["valor"])),
                    ("numero", "%s: vencimento do título %s" % (nome, t["numero"]), _d(t["vencimento"]))]
    out.append(("texto", "nota do método da fila", "A ordem não é por vencimento nem por valor"))
    return out


def regua_(c):
    p = c["painel"]
    out = _nav() + _avisos(p)
    out += [("texto", "título", "Régua de cobrança"), ("texto", "posição", "Posição em " + _d(p["ref"])),
            ("texto", "assinatura", "Sua assinatura nos textos"), ("texto", "aviso: a Central não manda nada", "a Central não manda nada"),
            ("texto", "onde ficam os registros", "dados/cobrancas_registradas.json"), ("texto", "planilha só lida", "Base_bruta.xlsx"),
            ("link", "ir para Cobranças feitas", 'href="/cobrancas"')]
    if not p["fila"]:
        out.append(("texto", "régua vazia", "Nenhum cliente tem título vencido"))
    for f in p["fila"]:
        cli, cod = f["cliente"], f["cliente"]["codigo"]
        nome = cli["nome"]
        r = p["risco_por_cliente"][cod]
        sug, razoes = regua.escolher(p["ref"], r, regua.contatos_do_cliente(p["cobrancas"], cod))
        out += [("texto", "%s: nome" % nome, nome),
                ("numero", "%s: valor vencido" % nome, reais(f["vencido"])),
                ("texto", "%s: com quem falar" % nome, "falar com " + (cli.get("contato") or "sem contato no cadastro")),
                ("texto", "%s: última cobrança" % nome, frases.ultimo_contato(f)),
                ("texto", "%s: tom sugerido" % nome, regua.nome_tom(sug)),
                ("texto", "botão copiar", "Copiar texto"), ("texto", "botão registrar", "Registrar que cobrei"),
                ("texto", "%s: aviso de reescrita" % nome, "Trocar o tom, o canal ou os títulos reescreve o texto")]
        out += [("frase", "%s: por que este tom" % nome, rz) for rz in razoes]
        out += [("texto", "tom disponível: " + v[0], v[0]) for v in regua.TONS.values()]
        if f["cobrado_recente"]:
            out.append(("alerta", "%s: cobrado nas últimas 48h" % nome, "cobrado nas últimas 48h"))
        for t in r["vencidos"]:
            out += [("numero", "%s: título %s" % (nome, t["numero"]), t["numero"]), ("numero", "%s: valor do título %s" % (nome, t["numero"]), reais(t["valor"])),
                    ("texto", "%s: dias do título %s" % (nome, t["numero"]), _dias(t["dias_atraso"]))]
        if c.get("texto_padrao"):
            out.append(("frase", "%s: texto pronto (WhatsApp)" % nome, c["texto_padrao"](cod)))
    return out


def cobrancas(c):
    p = c["painel"]
    out = _nav() + _avisos(p)
    res = c["resumo_contatos"]
    out += [("texto", "de onde vem cada coisa", "De onde vem cada coisa"), ("texto", "fonte: planilha", "Planilha da empresa"),
            ("texto", "fonte: Central", "Registradas na Central"), ("texto", "hora do registro", "A hora de cada registro na Central"),
            ("texto", "regra das 48h", "alimentam a regra das 48 horas da tela Hoje"),
            ("texto", "últimos 7 dias", "Últimos 7 dias (desde %s): %d contato" % (_d(res["ini"]), res["n"])),
            ("numero", "últimos 7 dias: valor cobrado", _int(res["valor"])),
            ("texto", "último contato por cliente", "Último contato por cliente"), ("texto", "todas as cobranças", "Todas as cobranças")]
    nomes = {r["cliente"]["codigo"]: r["cliente"]["nome"] for r in p["rs"]}
    for r in p["rs"]:
        out += [("link", "%s: ficha" % r["cliente"]["nome"], 'href="/risco/%d"' % r["cliente"]["codigo"]), ("texto", "%s: nome" % r["cliente"]["nome"], r["cliente"]["nome"])]
    for cb in p["cobrancas"]:
        nome = nomes.get(cb["cliente"], "?")
        out += [("texto", "cobrança de %s em %s: quando" % (nome, cb["quando"]), cb["quando"].strftime("%d/%m/%Y %H:%M")),
                ("texto", "cobrança de %s: canal" % nome, cb["canal"]), ("texto", "cobrança de %s: tom" % nome, cb["tom"]),
                ("numero", "cobrança de %s: valor" % nome, reais(cb["valor"]))]
        if cb.get("origem") == "Central":
            out.append(("texto", "botão desfazer", "Desfazer"))
    return out


def risco_(c):
    p, rs = c["painel"], c["painel"]["rs"]
    import risco as risco_mod
    tot = risco_mod.totais(rs)
    out = _nav() + _avisos(p)
    out += [("texto", "título", "Risco por cliente"), ("texto", "ordenação", "ordenado por valor em risco"),
            ("numero", "saldo total em aberto", _int(tot["saldo"])), ("numero", "valor em risco total", _int(tot["valor_em_risco"])),
            ("texto", "nota da ficha", "Clique no cliente para ver a ficha")]
    for caso in risco_mod.casos(rs, p["n_lista"]):
        out.append(("alerta", "achado: " + caso["titulo"], caso["titulo"]))
        for it in caso["itens"]:
            out.append(("alerta", "achado: " + (it["nome"] or caso["titulo"]), it.get("frase") or (((it["nome"] or "") + it["antes"] + it["destaque"] + it["depois"]).strip())))
            if it["codigo"]:
                out.append(("link", "achado: ficha de " + it["nome"], 'href="/risco/%d"' % it["codigo"]))
    for r in rs:
        cli = r["cliente"]
        nome = cli["nome"]
        out += [("link", "%s: ficha" % nome, 'href="/risco/%d"' % cli["codigo"]), ("texto", "%s: nome" % nome, nome),
                ("texto", "%s: categoria" % nome, cli["categoria"]), ("texto", "%s: região" % nome, cli["regiao"]),
                ("numero", "%s: saldo" % nome, _int(r["saldo"])), ("numero", "%s: limite ocupado" % nome, "%d%% do limite" % arred(100 * r["ocupacao"])),
                ("numero", "%s: índice" % nome, str(r["indice"])), ("numero", "%s: valor em risco" % nome, _int(r["valor_em_risco"])),
                ("numero", "%s: peso no faturamento" % nome, pct1(100 * r["pct_fat"]) + "%")]
        if r["parcial"]:
            out.append(("alerta", "%s: índice parcial" % nome, "parcial"))
        out += [("alerta", "%s: etiqueta %s" % (nome, t), c["rotulos"][t]) for t in r["tags"] if t in c["rotulos"]]
    return out


def ficha(c):
    """Uma ficha de cliente (c['r'])."""
    p, r, ref = c["painel"], c["r"], c["painel"]["ref"]
    cli, pg = r["cliente"], r["pag"]
    nome = cli["nome"]
    out = _nav() + [("link", "voltar para Risco por cliente", 'href="/risco"'), ("texto", "nome", nome), ("texto", "categoria", cli["categoria"]),
                    ("texto", "região", cli["regiao"]), ("texto", "cliente desde", "cliente desde " + _d(cli["desde"])),
                    ("texto", "posição", "posição em " + _d(ref)),
                    ("alerta", "alerta por extenso (o que fazer)", r["alerta"]),
                    ("numero", "índice de risco", "%d / 100" % r["indice"]), ("numero", "valor em risco", _int(r["valor_em_risco"])),
                    ("numero", "saldo em aberto", _int(r["saldo"])), ("texto", "como o índice foi formado", "Como o índice foi formado")]
    for f in r["fatores"]:
        out += [("texto", "fator: " + f["nome"], f["nome"]), ("frase", "fator %s: frase" % f["nome"], f["frase"]),
                ("numero", "fator %s: pontos" % f["nome"], ("%.0f de %d" % (f["pontos"], f["peso"])) if f["pontos"] is not None else "fora (peso %d)" % f["peso"])]
    if r["parcial"]:
        out.append(("alerta", "índice parcial", "Índice parcial"))
    out += [("texto", "gráfico de pagamento: título", "Em quantos dias pagou, mês a mês"), ("texto", "gráfico de compras: título", "Compras"),
            ("texto", "legenda das compras", "Compras por mês de emissão")]
    if pg["ok"]:
        out.append(("texto", "legenda: padrão histórico", "padrão histórico (80%% dos pagamentos entre %d e %d dias)" % (arred(pg["p10"]), arred(pg["p90"]))))
    stats = [("Saldo em aberto", _int(r["saldo"])), ("Valor em risco", _int(r["valor_em_risco"])),
             ("Faturamento 12 meses", _int(r["fat12"])), ("Limite ocupado", "%d%% de" % arred(100 * r["ocupacao"])),
             ("Último pedido", "há %s" % _dias(r["compras"]["dias_sem_comprar"])), ("Prazo contratado", "%d dias" % cli["prazo_dias"])]
    if pg["ok"]:
        stats += [("Paga, em geral, com", "%s de atraso" % _dias(arred(pg["mediana"]))),
                  ("80% dos pagamentos", "entre %d e %d dias" % (arred(pg["p10"]), arred(pg["p90"]))), ("Maior atraso", _dias(pg["maximo"]))]
    out += [("numero", "número da ficha: " + k, v) for k, v in stats]
    for t in r["titulos"]:
        out += [("numero", "histórico: título %s" % t["numero"], t["numero"]), ("numero", "histórico: valor de %s" % t["numero"], reais(t["valor"])),
                ("numero", "histórico: vencimento de %s" % t["numero"], _d(t["vencimento"]))]
    out.append(("texto", "histórico completo", "Histórico completo"))
    return out


def previsao_(c):
    p, prev, rs = c["painel"], c["prev"], c["painel"]["rs"]
    import previsao as pv
    out = _nav() + _avisos(p)
    fim = prev["semanas"][-1][1]
    d = prev["dec"]
    partes = pv.arredonda_partes([d["adiado"], d["sem_data"], d["probabilidade"], d["antecipado"]])
    out += [("texto", "título", "Previsão de caixa"),
            ("texto", "período", "de %s a %s" % (prev["semanas"][0][0].strftime("%d/%m"), fim.strftime("%d/%m"))),
            ("alerta", "só a carteira que já existe", "Só a carteira que já existe"), ("texto", "sem venda nova", "nenhuma venda nova"),
            ("texto", "não é projeção comercial", "Não é projeção comercial"),
            ("numero", "planilha (soma dos vencimentos)", _int(prev["total_planilha"])), ("numero", "esperado", _int(prev["total_esp"])),
            ("numero", "diferença", _int(prev["diferenca"])), ("numero", "conservador", _int(prev["total_cons"])),
            ("numero", "otimista", _int(prev["total_otim"])),
            ("numero", "vencidos que a planilha põe na semana 1", _int(prev["vencidos_na_planilha"])),
            ("numero", "soma sem os vencidos", _int(prev["total_planilha"] - prev["vencidos_na_planilha"])),
            ("texto", "de onde vem a diferença", "De onde vem a diferença")]
    for rot, v in zip(("Adiado", "Sem data", "Chance de não entrar", "Antecipado"), partes):
        out += [("texto", "diferença: " + rot, rot), ("numero", "diferença: " + rot, f"{abs(v):,}".replace(",", "."))]
    out += [("texto", "por que a faixa é no acumulado", "Por que a faixa é no acumulado"), ("texto", "acumulado de caixa", "Acumulado de caixa")]
    for i in range(pv.SEMANAS):
        out += [("numero", "semana %d: planilha na semana" % (i + 1), reais(prev["planilha"][i])),
                ("numero", "semana %d: esperado acumulado" % (i + 1), _int(prev["cum"]["esp"][i])),
                ("numero", "semana %d: conservador acumulado" % (i + 1), _int(prev["cum"]["cons"][i])),
                ("numero", "semana %d: otimista acumulado" % (i + 1), _int(prev["cum"]["otim"][i]))]
    out.append(("texto", "cliente por cliente", "Cliente por cliente"))
    for cl in prev["clientes"]:
        nome = cl["cliente"]["nome"]
        out += [("texto", "%s: nome" % nome, nome), ("link", "%s: ficha" % nome, 'href="/risco/%d"' % cl["cliente"]["codigo"]),
                ("frase", "%s: por quê" % nome, cl["frase"]), ("numero", "%s: planilha" % nome, reais(cl["planilha"])),
                ("numero", "%s: esperado" % nome, _int(cl["previsao"]))]
        if cl["r"]["pag"].get("piora"):
            out.append(("alerta", "%s: piorou" % nome, "piorou"))
    out += [("texto", "título a título", "Título a título"), ("texto", "como foi calculado", "Como foi calculado")]
    for l in prev["linhas"]:
        out.append(("numero", "título %s" % l["numero"], l["numero"]))
    for frase_fixa in ("Data esperada", "Dia bom e dia ruim", "Título já vencido", "Chance de entrar", "Planilha:", "As quatro semanas começam em",
                       "premissas, não medidas"):
        out.append(("texto", "como foi calculado: " + frase_fixa, frase_fixa))
    return out


def relatorio_(c):
    p = c["painel"]
    out = _nav() + [("texto", "título", "Relatório da semana"), ("texto", "aviso: não refaz conta", "Não refaz nenhuma conta"),
                    ("link", "baixar o Word", 'href="/relatorio.docx"')]
    for b in c["blocos"]:
        if b[0] in ("titulo",):
            continue
        if b[0] == "decisao":
            out.append(("frase", "decisão %s" % b[1], "%s. %s %s" % (b[1], b[2], b[3])))
        else:
            out.append(("frase", "parágrafo do relatório", b[1]))
    return out


FUNCOES = {"hoje": hoje, "regua": regua_, "cobrancas": cobrancas, "risco": risco_, "ficha": ficha, "previsao": previsao_, "relatorio": relatorio_}


def exigidos(tela, contexto):
    itens = FUNCOES[tela](contexto)
    vistos, unicos = set(), []
    for cat, desc, needle in itens:  # sem repetição do mesmo par
        k = (cat, desc, needle)
        if k not in vistos:
            vistos.add(k)
            unicos.append(k)
    return unicos


def faltando(tela, html, contexto, link=None):
    """Itens exigidos que NÃO estão no HTML. Lista vazia = nada sumiu. `link` (opcional) traduz um endereço da versão local para o do arquivo único."""
    texto, bruto = norm(html), html
    falt = []
    for cat, desc, needle in exigidos(tela, contexto):
        if cat == "link":  # aceita aspas simples ou duplas, e a forma do arquivo único (#/...)
            alvo = re.search(r'href="([^"]*)"', needle).group(1)
            candidatos = {alvo, "#" + alvo} | ({link(alvo)} if link else set())  # `link`: como o arquivo único reescreve o endereço
            ok = any(("href=%s%s%s" % (q, c, q)) in bruto for q in ('"', "'") for c in candidatos)
        else:
            ok = norm(needle) in texto
        if not ok:
            falt.append((cat, desc, needle))
    return falt


def resumo_em_portugues(contexto_por_tela):
    """A lista, por tela e por categoria, com contagens (para o dono conferir o que está sendo cobrado)."""
    linhas = []
    for tela, ctx in contexto_por_tela.items():
        itens = exigidos(tela, ctx)
        por_cat = {}
        for cat, _, _ in itens:
            por_cat[cat] = por_cat.get(cat, 0) + 1
        linhas.append("%-10s %4d itens: %s" % (tela, len(itens), ", ".join("%d %s" % (n, k) for k, n in sorted(por_cat.items()))))
    return "\n".join(linhas)
