"""Redação: o ÚNICO lugar da Central onde se escreve texto para gente ler.

Tudo o que a Central escreve (o texto da cobrança e o relatório da diretoria) passa por um Redator.
Hoje o Redator é `RedatorPorRegras`: monta cada frase a partir dos números já calculados, sem internet, sem
conta, sem IA. Para trocar a redação por um modelo de linguagem, escreva outra classe com os mesmos dois
métodos (`cobranca` e `relatorio`) e aponte `REDATOR` (no fim do arquivo) para ela. O resto da Central não muda:
ele só entrega fatos (dicionários) e recebe texto.

Contrato:
  cobranca(ctx)  -> {"assunto": str | None, "texto": str}     ctx: ver regua.contexto()
  relatorio(ctx) -> [bloco, ...]                               ctx: ver relatorio.contexto(); bloco: ver abaixo
Bloco do relatório: ("titulo", str) | ("subtitulo", str) | ("par", str) | ("decisao", str)
"""
from frases import arred, reais, reais_int


def _dias(n):
    return "%d dia%s" % (n, "" if n == 1 else "s")


def _data(d):
    return d.strftime("%d/%m")


def _data_completa(d):
    return d.strftime("%d/%m/%Y")


def _periodo(ctx):
    m = ctx["meses_historico"]
    return "nos últimos dois anos" if m >= 22 else "nos últimos %d meses" % m


def _artigo(ctx, singular, plural):
    return singular if len(ctx["titulos"]) == 1 else plural


class RedatorPorRegras:
    # ------------------------------------------------------------ cobrança
    def cobranca(self, ctx):
        tom, canal = ctx["tom"], ctx["canal"]
        partes = _PARTES[tom](ctx)
        if canal == "Telefone":
            return {"assunto": None, "texto": self._roteiro(ctx, partes)}
        return {"assunto": partes["assunto"](ctx) if canal == "E-mail" else None,
                "texto": self._mensagem(ctx, partes, canal)}

    def _quem(self, ctx, canal, casa="do financeiro da Aurora"):
        if canal == "E-mail":
            casa = casa.replace("da Aurora", "da Distribuidora Aurora")
            return ("Sou %s, %s." % (ctx["remetente"], casa)) if ctx["remetente"] else ("Sou %s." % casa)
        return ("Aqui é %s, %s." % (ctx["remetente"], casa)) if ctx["remetente"] else ("Aqui é %s." % casa)

    def _lista(self, ctx):
        firme = ctx["tom"] in ("objetiva", "formal")  # nos tons leves a lista não carrega a contagem de dias
        linhas = ["• %s · %s · venceu em %s%s" % (
            t["numero"], reais(t["valor"]), _data_completa(t["vencimento"]), (" (%s de atraso)" % _dias(t["dias"])) if firme else "")
            for t in ctx["titulos"]]
        if len(ctx["titulos"]) > 1:
            linhas.append("Total: %s" % reais(ctx["total"]))
        return "\n".join(linhas)

    def _saudacao(self, ctx, ponto="?"):
        return ("Olá, %s, tudo bem%s" % (ctx["contato"], ponto)) if ctx["contato"] else "Olá, tudo bem%s" % ponto

    def _mensagem(self, ctx, partes, canal):
        blocos = []
        abertura = partes["abertura"](ctx, canal)
        if canal == "E-mail":
            blocos.append("Assunto: " + partes["assunto"](ctx))
            blocos.append(("Olá, %s," % ctx["contato"]) if ctx["contato"] else "Olá,")
            blocos.append(abertura)
        else:
            blocos.append(self._saudacao(ctx) + " " + abertura)
        for b in partes["corpo"]:
            blocos.append(self._lista(ctx) if b == "{LISTA}" else b)
        blocos.append(partes["fecho"])
        if canal == "E-mail":
            assin = [ctx["remetente"]] if ctx["remetente"] else []
            blocos.append("\n".join(["Um abraço,"] + assin + ["Financeiro | Distribuidora Aurora"]))
        return "\n\n".join(blocos)

    def _roteiro(self, ctx, partes):
        r = partes["roteiro"](ctx)
        nome = ctx["contato"] or "responsável"
        saida = ["Roteiro de ligação: %s (falar com %s)" % (ctx["cliente"], nome) if ctx["contato"] else
                 "Roteiro de ligação: %s" % ctx["cliente"], ""]
        for i, (titulo, linhas) in enumerate(r, 1):
            saida.append("%d. %s" % (i, titulo))
            saida += ["   - " + l for l in linhas]
            saida.append("")
        if ctx["tom"] != "comercial":
            saida.append("Títulos à mão durante a ligação:")
            saida.append(self._lista(ctx))
            saida.append("")
        saida.append("Depois da ligação, registre aqui o contato.")
        return "\n".join(saida)

    # ------------------------------------------------------------ relatório
    def relatorio(self, ctx):
        return _relatorio_por_regras(ctx)


# ---------------------------------------------------------------- textos das cobranças
# Cada tom devolve: assunto(ctx), abertura(ctx, canal), corpo [...] (com "{LISTA}" onde entra a lista), fecho,
# roteiro(ctx) -> [(título, [linhas])]. Sem "Prezado", sem "obrigado": nada que dependa do gênero de quem lê ou escreve.

def _titulos_em_aberto(ctx, sing, plur):
    return sing if len(ctx["titulos"]) == 1 else plur


def _lembrete_leve(ctx):
    um = len(ctx["titulos"]) == 1
    R = RedatorPorRegras()
    return {
        "assunto": lambda c: "Lembrete: %s em aberto" % ("um título" if um else "%d títulos" % len(c["titulos"])),
        "abertura": lambda c, canal: "%s Passando só para lembrar que %s ainda não consta%s como pago%s por aqui:" % (
            R._quem(c, canal), "o título abaixo venceu e" if um else "os títulos abaixo venceram e", "" if um else "m",
            "" if um else "s"),
        "corpo": ["{LISTA}",
                  "Se já foi pago, pode ignorar este aviso e me mandar a data do pagamento que eu confiro aqui. E se faltar "
                  "alguma coisa da nossa parte para o pagamento sair, como segunda via ou nota, é só me falar."],
        "fecho": "Qualquer coisa, estou por aqui.",
        "roteiro": lambda c: [
            ("Abertura", ["Oi, %s, é do financeiro da Aurora. Tudo bem? Não vou tomar seu tempo." % (c["contato"] or "tudo bem")]),
            ("O motivo", ["Estou ligando só para confirmar %s." % (
                "um título que venceu em %s" % _data(c["titulos"][0]["vencimento"]) if um else
                "os títulos em aberto, o mais antigo venceu em %s" % _data(c["titulos"][0]["vencimento"]))]),
            ("O que perguntar", ["Já foi pago? Se sim, em que data, para eu conferir aqui.",
                                 "Se não: quando vai sair? Falta algo de nossa parte (segunda via, nota)?"]),
            ("Fechar", ["Repita a data combinada e diga que vai anotar."]),
        ],
    }


def _lembrete_prazo(ctx):
    um = len(ctx["titulos"]) == 1
    R = RedatorPorRegras()
    hab, real, contrato = ctx["atraso_habitual"], ctx["prazo_real"], ctx["prazo_contrato"]
    sugestao_sem_historico = ("Aproveito para perguntar uma coisa: o prazo de %d dias do contrato funciona bem para vocês? Se não funcionar, "
                              "me fala que eu levo para o comercial ajustar." % contrato)
    sugestao = sugestao_sem_historico if hab is None else ("Aproveito para uma sugestão. Olhando os pagamentos de vocês %s, eles chegam de forma bem regular, "
                "uns %s depois do vencimento. Na prática, o prazo de vocês já é de uns %s, e não os %d do contrato. "
                "Que tal formalizar isso? Assim a gente deixa de trocar lembrete todo mês, que só toma tempo dos dois lados. "
                "Se fizer sentido, me fala que eu levo para o comercial ajustar o contrato." % (
                    _periodo(ctx), _dias(hab), _dias(real), contrato))
    return {
        "assunto": lambda c: "Lembrete de título em aberto e uma sugestão de prazo",
        "abertura": lambda c, canal: "%s Passando para lembrar de %s em aberto:" % (
            R._quem(c, canal), "um título" if um else "%d títulos" % len(c["titulos"])),
        "corpo": ["{LISTA}", sugestao],
        "fecho": "Me diz o que você acha.",
        "roteiro": lambda c: [
            ("Abertura", ["Oi, %s, é do financeiro da Aurora. Tudo bem?" % (c["contato"] or "tudo bem")]),
            ("O motivo", ["Só para lembrar %s." % (
                "do título que venceu em %s" % _data(c["titulos"][0]["vencimento"]) if um else
                "dos títulos em aberto, o mais antigo venceu em %s" % _data(c["titulos"][0]["vencimento"]))]),
            ("A sugestão", (["Os pagamentos de vocês chegam de forma regular, uns %s depois do vencimento." % _dias(hab),
                             "Na prática o prazo é de uns %s; o contrato diz %s." % (_dias(real), _dias(contrato)),
                             "Perguntar se faz sentido formalizar, para parar de gerar lembrete todo mês."]
                            if hab is not None else
                            ["Ainda não há histórico para dizer como eles costumam pagar.",
                             "Perguntar se o prazo de %s do contrato funciona bem para eles." % _dias(contrato)])),
            ("Fechar", ["Se topar, você leva para o comercial ajustar o contrato. Combine a data do pagamento atual."]),
        ],
    }


def _primeiro_aviso(ctx):
    um = len(ctx["titulos"]) == 1
    R = RedatorPorRegras()
    return {
        "assunto": lambda c: "Título em aberto",
        "abertura": lambda c, canal: "%s Estava conferindo a carteira e vi que %s em aberto:" % (
            R._quem(c, canal), "o título abaixo segue" if um else "os títulos abaixo seguem"),
        "corpo": ["{LISTA}",
                  "Pode ter passado batido, ou o pagamento já estar a caminho. Se for o caso, me passa a data que eu acompanho. "
                  "E se faltou alguma coisa da nossa parte (segunda via, nota, algum dado), me avisa que eu resolvo na hora."],
        "fecho": "Fico no aguardo.",
        "roteiro": lambda c: [
            ("Abertura", ["Oi, %s, é do financeiro da Aurora. Tudo bem?" % (c["contato"] or "tudo bem")]),
            ("O motivo", ["Estava conferindo a carteira e %s em aberto, o mais antigo venceu em %s." % (
                "um título está" if um else "alguns títulos estão", _data(c["titulos"][0]["vencimento"]))]),
            ("O que perguntar", ["Isso já foi pago ou está a caminho? Quando?",
                                 "Faltou algo nosso (segunda via, nota, dado)? Se sim, resolva na hora."]),
            ("Fechar", ["Repita a data combinada e diga que vai acompanhar."]),
        ],
    }


def _grande_primeira(ctx):
    um = len(ctx["titulos"]) == 1
    R = RedatorPorRegras()
    foge = ", e isso foge do que a gente costuma ver com vocês" if ctx["bom_historico"] else ""
    desde = ("Vocês são clientes desde %d, então queria resolver do jeito mais simples para os dois lados. " % ctx["desde"]
             if ctx["desde"] else "")
    return {
        "assunto": lambda c: "Uma conferência sobre %s em aberto" % ("um título" if um else "%d títulos" % len(c["titulos"])),
        "abertura": lambda c, canal: "%s Escrevo direto para você porque achei melhor conversar antes de qualquer outra coisa: %s em aberto%s:" % (
            R._quem(c, canal), "o título abaixo está" if um else "os títulos abaixo estão", foge),
        "corpo": ["{LISTA}",
                  desde + "Não quero supor nada. Pode ser algo do nosso lado, como um documento que não chegou à pessoa certa, ou algo "
                  "no fluxo de pagamento aí dentro. Você consegue me ajudar a entender o que aconteceu e me dizer quando o "
                  "pagamento deve sair? Se precisar de segunda via, nota ou qualquer conferência, eu mando agora."],
        "fecho": "Conto com você. Agradeço desde já.",
        "roteiro": lambda c: [
            ("Abertura", ["Oi, %s, é do financeiro da Aurora. Tudo bem? Liguei direto para você porque prefiro conversar antes de "
                          "qualquer outra coisa." % (c["contato"] or "tudo bem")]),
            ("O motivo", ["%s em aberto, o mais antigo venceu em %s (%s de atraso)." % (
                "Um título está" if um else "Alguns títulos estão", _data(c["titulos"][0]["vencimento"]),
                _dias(c["titulos"][0]["dias"]))]),
            ("O que perguntar", ["Você sabe o que aconteceu? Pode ser algo nosso (documento que não chegou, segunda via).",
                                 "Quando o pagamento deve sair?"]),
            ("Fechar", ["Ofereça mandar na hora o que faltar. Repita a data combinada."]),
        ],
    }


def _conversa_piora(ctx):
    R = RedatorPorRegras()
    return {
        "assunto": lambda c: "Uma conversa sobre os pagamentos",
        "abertura": lambda c, canal: "%s Não escrevo para cobrar, escrevo para conversar." % R._quem(c, canal),
        "corpo": ["De uns meses para cá, os pagamentos de vocês têm chegado mais tarde do que vinham chegando. Queria entender se "
                  "mudou alguma coisa aí: o fluxo de aprovação, algum problema com entrega ou com nota, aperto de caixa. "
                  "Seja o que for, prefiro resolver junto a deixar acumular.",
                  "Hoje estão em aberto, só para a gente ter o mesmo número na mão:",
                  "{LISTA}",
                  "Dá para a gente conversar ainda esta semana? Se for questão de prazo ou de organizar os vencimentos, vejo com o "
                  "comercial o que dá para fazer."],
        "fecho": "Fico no aguardo do seu retorno.",
        "roteiro": lambda c: [
            ("Abertura", ["Oi, %s, é do financeiro da Aurora. Tudo bem? Não estou ligando para cobrar, quero conversar." % (
                c["contato"] or "tudo bem")]),
            ("O motivo", ["De uns meses para cá os pagamentos de vocês estão chegando mais tarde do que vinham chegando.",
                          "Diga que quer entender, não que quer cobrar."]),
            ("O que perguntar", ["Mudou algo aí: fluxo de aprovação, entrega, nota, caixa?",
                                 "Há algo do nosso lado atrapalhando?"]),
            ("Fechar", ["Se for questão de prazo ou de organizar os vencimentos, você vê com o comercial o que dá para fazer.",
                        "Combine um retorno ainda esta semana."]),
        ],
    }


def _comercial(ctx):
    R = RedatorPorRegras()
    return {
        "assunto": lambda c: "Como estão as coisas por aí?",
        "abertura": lambda c, canal: (
            "%s Faz um tempo que vocês não fazem pedido com a gente (o último foi em %s) e queria saber como estão as coisas por aí."
            if c["dias_sem_pedido"] >= 30 else
            "%s Queria saber como estão as coisas por aí (o último pedido de vocês foi em %s).") % (
                R._quem(c, canal, "da Aurora"), _data(c["ultimo_pedido"])),
        "corpo": ["Mudou alguma coisa no movimento de vocês, no mix de produtos, em entrega ou em condição que a gente possa "
                  "ajustar? Se puder me contar, mesmo rapidinho, já ajuda.",
                  "Aproveito para mencionar uma pendência financeira em aberto, de %s. Sem pressa de resolver agora: "
                  "a gente vê isso junto, do jeito que for melhor para vocês." % reais(ctx["total_vencido_cliente"])],
        "fecho": "Fico no aguardo do seu retorno.",
        "roteiro": lambda c: [
            ("Abertura", ["Oi, %s, é da Aurora. Tudo bem? Faz um tempo que a gente não fala." % (c["contato"] or "tudo bem")]),
            ("O motivo", ["O último pedido foi em %s; diga que quer saber como estão as coisas por aí." % _data_completa(c["ultimo_pedido"]),
                          "Não abra pela cobrança."]),
            ("O que perguntar", ["Mudou o movimento, o mix, a entrega ou alguma condição?",
                                 "Há algo que a Aurora possa ajustar para voltar a ser a primeira opção?"]),
            ("A pendência", ["Só mencionar, no fim: há %s em aberto, e dá para ver junto, sem pressa." % reais(c["total_vencido_cliente"]),
                             "Não listar título nem cobrar data nesta ligação."]),
        ],
    }


def _objetiva(ctx):
    um = len(ctx["titulos"]) == 1
    R = RedatorPorRegras()
    ant = ctx["contato_anterior"]

    def abertura(c, canal):
        quem = R._quem(c, canal)
        if ant:
            return "%s Retomando nosso contato de %s (%s): %s em aberto%s." % (
                quem, _data(ant["quando"]), ant["canal"].lower() if ant["canal"] != "E-mail" else "e-mail",
                "o título abaixo continua" if um else "os títulos abaixo continuam",
                "" if um else ", o mais antigo há %s" % _dias(c["mais_antigo"]))
        return "%s Escrevo sobre %s, em aberto%s." % (
            quem, "o título abaixo" if um else "os títulos abaixo", "" if um else ", o mais antigo há %s" % _dias(c["mais_antigo"]))
    return {
        "assunto": lambda c: "Título%s em aberto: preciso de uma data de pagamento" % ("" if um else "s"),
        "abertura": abertura,
        "corpo": ["{LISTA}",
                  ("Vocês costumam pagar com poucos dias de atraso, então imagino que tenha sido algo pontual. "
                   if ctx["bom_historico"] else "")
                  + "Preciso que você me confirme a data em que o pagamento vai ser feito. Se houver algum problema com o título "
                  "(valor, nota, entrega), me diz qual que eu ajudo a destravar."],
        "fecho": "Fico no aguardo.",
        "roteiro": lambda c: [
            ("Abertura", ["Oi, %s, é do financeiro da Aurora. Tudo bem?" % (c["contato"] or "tudo bem")]),
            ("O motivo", ([("Retomando nosso contato de %s: " % _data(ant["quando"]) if ant else "")
                           + "%s em aberto, o mais antigo há %s." % ("o título segue" if um else "os títulos seguem",
                                                                     _dias(c["mais_antigo"]))])),
            ("O que perguntar", ["Qual a data em que o pagamento vai ser feito?",
                                 "Há algum problema com o título (valor, nota, entrega) que eu possa ajudar a destravar?"]),
            ("Fechar", ["Repita a data combinada e diga que vai acompanhar."]),
        ],
    }


def _formal(ctx):
    um = len(ctx["titulos"]) == 1
    R = RedatorPorRegras()
    ant = ctx["contato_anterior"]

    def abertura(c, canal):
        quem = R._quem(c, canal)
        jaf = "Já falamos sobre %s" % ("este título" if um else "estes títulos")
        if ant:
            jaf += " (último contato em %s, por %s)" % (_data(ant["quando"]), ant["canal"].lower() if ant["canal"] != "E-mail" else "e-mail")
        return "%s %s e %s sem pagamento%s:" % (quem, jaf, "segue" if um else "seguem",
                                                 "" if um else ", o mais antigo com %s de atraso" % _dias(c["mais_antigo"]))
    return {
        "assunto": lambda c: "Títulos em aberto: %s, posição em %s" % (c["cliente"], _data_completa(c["hoje"])),
        "abertura": abertura,
        "corpo": ["{LISTA}",
                  "Preciso de uma data firme de pagamento até %s. Se houver algum impedimento, me diga qual, para a gente tratar."
                  % _data_completa(ctx["resposta_ate"])],
        "fecho": "Fico aguardando seu retorno.",
        "roteiro": lambda c: [
            ("Abertura", ["Oi, %s, é do financeiro da Aurora. Preciso de alguns minutos, é sobre títulos em aberto." % (
                c["contato"] or "tudo bem")]),
            ("O motivo", ["Já houve contato (%s) e os títulos seguem sem pagamento, o mais antigo há %s." % (
                _data(ant["quando"]) if ant else "anterior", _dias(c["mais_antigo"]))]),
            ("O que pedir", ["Uma data firme de pagamento até %s." % _data_completa(c["resposta_ate"]),
                             "Se houver impedimento, qual é, para tratar."]),
            ("Fechar", ["Repita a data e o prazo combinado; confirme depois por e-mail."]),
        ],
    }


_PARTES = {
    "lembrete_leve": _lembrete_leve, "lembrete_prazo": _lembrete_prazo, "primeiro_aviso": _primeiro_aviso,
    "grande_primeira": _grande_primeira, "conversa_piora": _conversa_piora, "comercial": _comercial,
    "objetiva": _objetiva, "formal": _formal,
}


def _lista_nomes(nomes):
    if not nomes:
        return ""
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def _extenso(n, maiuscula=False):
    nomes = {1: "um", 2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove"}
    t = nomes.get(n, str(n))
    return t.capitalize() if maiuscula else t


def _dias_lista(valores):
    """[7, 18] -> '7 e 18 dias'."""
    return _lista_nomes([str(v) for v in valores]) + (" dia" if len(valores) == 1 and valores[0] == 1 else " dias")


def _canal(c):
    """'E-mail' com hífen que não quebra linha: a palavra nunca vira 'E-' numa linha e 'mail' na outra."""
    return c.replace("-", "\u2011")


def _n(v):
    """Inteiro de reais com ponto de milhar, sem símbolo."""
    return f"{v:,}".replace(",", ".")


def _relatorio_por_regras(ctx):
    import previsao as pv  # só para arredondar as estimativas do mesmo jeito que a tela de previsão
    from risco import MESES_NOME
    est = pv.reais_est
    R, rk, P, cl = ctx["resumo"], ctx["risco"], ctx["previsao"], ctx["clientes"]
    ref = ctx["ref"]
    b = [("titulo", "Relatório da semana"),
         ("sub", "Distribuidora Aurora · Central de Crédito e Cobrança · posição em %s · semana de %s a %s" % (
             _data_completa(ref), _data(R["janela_ini"]), _data(ref)))]

    acima = R["entrou_7d"] > R["entrou_media_8s"]
    b.append(("par", "Entraram %s na semana, %s da média das oito semanas anteriores (%s). Há %s vencidos e não pagos, em %d títulos de "
                     "%d clientes, e a leitura de risco põe %s do saldo de %s em risco. Olhando só a carteira que já existe, "
                     "espero receber %s nas próximas quatro semanas, e não os %s que a soma dos vencimentos aponta. Abaixo, o que "
                     "aconteceu, onde está o risco, quanto deve entrar e o que fazer nesta semana, na ordem de quanto vale."
              % (reais(R["entrou_7d"]), "acima" if acima else "abaixo", est(R["entrou_media_8s"]), reais(R["vencido"]),
                 R["n_vencidos"], R["n_clientes_vencido"], est(rk["valor_em_risco"]), reais(rk["saldo"]), est(P["esperado"]),
                 reais(P["planilha"]))))

    # ---- o que entrou e o que não entrou
    b.append(("secao", "O que entrou e o que não entrou"))
    t = ("Nos sete dias de %s a %s entraram %s, em %d títulos pagos por %d clientes, %s da média de %s por semana nas oito semanas "
         "anteriores. Dos títulos que venceram nesses mesmos sete dias (%s, em %d título%s), %s ainda estão em aberto, em %d título%s. "
         "Somando tudo, a carteira tem %s vencidos e não pagos e %s a vencer."
         % (_data(R["janela_ini"]), _data(ref), reais(R["entrou_7d"]), R["n_entrou_7d"], R["n_clientes_entrou_7d"],
            "acima" if acima else "abaixo", est(R["entrou_media_8s"]), reais(R["venceu_7d"]), R["n_venceu_7d"], "" if R["n_venceu_7d"] == 1 else "s",
            reais(R["venceu_7d_aberto"]), R["n_venceu_7d_aberto"], "" if R["n_venceu_7d_aberto"] == 1 else "s",
            reais(R["vencido"]), reais(R["a_vencer"])))
    c = ctx["contatos"]
    if c["n"]:
        t += (" A equipe registrou %d contato%s de cobrança na semana, sobre %s, com %d cliente%s." % (
            c["n"], "" if c["n"] == 1 else "s", reais(c["valor"]), c["n_clientes"], "" if c["n_clientes"] == 1 else "s"))
    else:
        t += " Nenhum contato de cobrança foi registrado na semana."
    b.append(("par", t))

    # ---- onde está o risco
    b.append(("secao", "Onde está o risco"))
    top = [x for x in cl if x["valor_em_risco"] > 0][:3]
    b.append(("par", "A leitura do histórico de pagamento de cada cliente dá um índice de risco de 0 a 100. Multiplicado pelo saldo em "
                     "aberto de cada um, põe %s em risco, %d%% do saldo de %s. Os três maiores valores em risco são %s."
              % (est(rk["valor_em_risco"]), round(100 * rk["pct_em_risco"]), reais(rk["saldo"]),
                 _lista_nomes(["%s (%s)" % (x["nome"], est(x["valor_em_risco"])) for x in top]))))
    primeiro = True
    for x in (y for y in cl if y["acao"] == "conversa"):
        q = (", e comprou %d%% menos nos últimos 90 dias" % round(100 * x["queda"])) if x["queda"] else ""
        b.append(("par", "%s %s: nunca deixou de pagar, mas de uns meses para cá paga com %s de atraso, contra %s antes%s. Tem %s "
                         "vencidos e %d%% do limite de crédito ocupado." % (
                             "O caso que mais pesa é" if primeiro else "Também piorou:", x["nome"], _dias(arred(x["rec_med"])),
                             _dias(arred(x["base_med"])), q, reais(x["vencido"]), round(100 * x["ocupacao"]))))
        primeiro = False
    for x in (y for y in cl if y["acao"] == "comercial"):
        b.append(("par", "%s parou de comprar: o último pedido foi há %s e, em toda a história, nunca tinha passado de %s entre "
                         "pedidos. Tem %s vencidos, o mais antigo há %s." % (
                             x["nome"], _dias(x["dias_sem_comprar"]), _dias(x["gap_max"]), reais(x["vencido"]), _dias(x["mais_antigo"]))))
    cobrar = [y for y in cl if y["acao"] == "cobrar"]
    if cobrar:
        itens = ["%s (%s, vencido há %s, contra um máximo histórico de %s)" % (
            x["nome"], reais(sum(f["valor"] for f in x["fora"])), _dias(max(f["dias"] for f in x["fora"])), _dias(x["maximo"]))
            for x in cobrar]
        b.append(("par", "%s cliente%s com título vencido além de qualquer atraso que já tiveram: %s." % (
            _extenso(len(cobrar), True), "" if len(cobrar) == 1 else "s", _lista_nomes(itens))))
    prazo = [y for y in cl if y["acao"] == "prazo"]
    if prazo:
        b.append(("par", "Do outro lado, parte do que a lista de vencidos mostra não é risco. %s %s sempre com o mesmo atraso (%s), o que "
                         "dá prazos reais de %s contra %s no contrato, na mesma ordem. Cobrar assim todo mês é trabalho perdido dos "
                         "dois lados." % (
                             _lista_nomes([x["nome"] for x in prazo]), "paga" if len(prazo) == 1 else "pagam",
                             _dias_lista([arred(x["atraso_habitual"]) for x in prazo]),
                             _dias_lista([x["prazo_contrato"] + arred(x["atraso_habitual"]) for x in prazo]),
                             _dias_lista([x["prazo_contrato"] for x in prazo]))))
    for x in (y for y in cl if y["sazonais"]):
        b.append(("par", "%s atrasa em %s nos dois anos da base: é sazonal, e por isso não foi tratado como piora." % (
            x["nome"], _lista_nomes([MESES_NOME[m - 1] for m in sorted(x["sazonais"])]))))
    curtos = [y for y in cl if y["falta_dado"]]
    if curtos:
        b.append(("par", "Faltou dado para alguma das contas, que ficou de fora, em %s; o índice %s é parcial e deve ser lido com "
                         "cuidado." % (_lista_nomes(["%s (%s)" % (y["nome"], y["falta_dado"][0]) for y in curtos]),
                                       "dele" if len(curtos) == 1 else "deles")))

    # ---- quanto entra
    b.append(("secao", "Quanto deve entrar nas próximas quatro semanas"))
    sem = pv.arredonda_partes(P["semanas_esperado"])
    d = P["decomposicao"]
    partes = pv.arredonda_partes([d["adiado"], d["sem_data"], d["probabilidade"], d["antecipado"]])
    b.append(("par", "Até %s, a soma dos vencimentos apontaria %s, incluindo %s de títulos já vencidos. Lendo como cada cliente paga de "
                     "verdade, espero %s, com uma faixa de %s a %s no acumulado (cenários conservador e otimista). Por semana, o "
                     "esperado é %s." % (
                         _data(P["fim"]), reais(P["planilha"]), reais(P["vencidos_na_planilha"]), est(P["esperado"]),
                         est(P["conservador"]), est(P["otimista"]), _lista_nomes([reais_int(v) for v in sem]))))
    b.append(("par", "A diferença de %s para a planilha vem de três coisas: %s de títulos que vencem nas quatro semanas, mas que o "
                     "cliente só costuma pagar depois de %s; %s de vencidos que já passaram de todo atraso que o cliente teve, para "
                     "os quais não consigo dizer a data; e %s de desconto pela chance de não entrarem. Esta previsão considera só a "
                     "carteira que já existe: não inclui venda nova e não é projeção comercial." % (
                         est(P["diferenca"]), reais_int(partes[0]), _data(P["fim"]), reais_int(partes[1]), reais_int(partes[2]))))

    # ---- decisões
    b.append(("secao", "O que fazer nesta semana, em ordem de quanto vale"))
    n = 0
    for x in cl:
        if not x["acao"]:
            continue
        n += 1
        vr = est(x["valor_em_risco"])
        contato = ""
        uc = x["ultimo_contato"]
        if uc and x["cobrado_recente"]:
            contato = " Já foi cobrado em %s, por %s; esperar o retorno antes de insistir." % (_data(uc["quando"]), _canal(uc["canal"]))
        elif uc:
            contato = " O último contato foi em %s, por %s." % (_data(uc["quando"]), _canal(uc["canal"]))
        if x["acao"] == "conversa":
            b.append(("decisao", n, "%s: abrir uma conversa esta semana e segurar novos pedidos a prazo até entender a causa." % x["nome"],
                      "São %s em risco (%s vencidos, saldo de %s, %d%% do limite). A abordagem proposta é de "
                      "conversa, não de cobrança.%s" % (vr, reais(x["vencido"]), reais(x["saldo"]), round(100 * x["ocupacao"]), contato)))
        elif x["acao"] == "comercial":
            b.append(("decisao", n, "%s: o comercial fala primeiro, antes de qualquer cobrança do financeiro, e não se libera novo "
                                    "pedido a prazo antes de acertar o vencido." % x["nome"],
                      "São %s em risco; %s vencidos, o mais antigo há %s.%s" % (vr, reais(x["vencido"]), _dias(x["mais_antigo"]), contato)))
        elif x["acao"] == "cobrar":
            pior = max(x["fora"], key=lambda f: f["dias"])
            b.append(("decisao", n, "%s: cobrar o título de %s vencido há %s, muito além dos %s que já chegou a atrasar." % (
                x["nome"], reais(pior["valor"]), _dias(pior["dias"]), _dias(pior["maximo"])),
                      "São %s em risco.%s" % (vr, contato)))
        elif x["acao"] == "prazo":
            b.append(("decisao", n, "%s: não cobrar antes de %s de atraso e propor ajustar o prazo do contrato de %s para %s." % (
                x["nome"], _dias(x["maximo"]), _dias(x["prazo_contrato"]), _dias(x["prazo_contrato"] + arred(x["atraso_habitual"]))),
                      "Paga sempre com cerca de %s de atraso e, pelo histórico, apareceria na lista de vencidos em %d dos %d fins de "
                      "mês. Valor em risco: %s.%s" % (_dias(arred(x["atraso_habitual"])), x["fins_mes_vencido"], x["fins_mes"], vr, contato)))
    resto = len(cl) - n
    if resto == 0:
        fecho = "Todos os clientes pedem alguma ação esta semana."
    elif resto == 1:
        fecho = "O outro cliente não pede ação esta semana."
    else:
        fecho = "Os outros %d clientes não pedem ação esta semana." % resto
    b.append(("par", fecho))
    return b


# O Redator ativo. Para usar outra redação, troque só esta linha.
REDATOR = RedatorPorRegras()
