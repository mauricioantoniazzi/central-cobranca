"""Frases em português que explicam a posição de cada cliente na fila, e os formatadores de dinheiro e número.

Cada frase é montada só com fatos que já foram calculados (a leitura de risco de risco.py, o valor vencido e a última
cobrança de motor.py). Nenhum número é escrito à mão aqui, e nenhum é recalculado: a tela Hoje diz do cliente o
mesmo que a tela Risco diz.
"""

NB = " "  # espaço inseparável: "R$" nunca fica numa linha e o valor na outra


def _milhar(n):
    return f"{n:,}".replace(",", ".")


def reais(c):
    """Valor FECHADO (centavos, int) -> 'R$ 1.234,56'. Só aritmética inteira."""
    sinal = "-" if c < 0 else ""
    inteiro, cent = divmod(abs(c), 100)
    return "%sR$%s%s,%02d" % (sinal, NB, _milhar(inteiro), cent)


def reais_est(c):
    """ESTIMATIVA (centavos, int) -> reais inteiros, sem centavo: 'R$ 607.674'. Arredonda meio para cima."""
    return reais_int((c + 50) // 100)


def reais_int(v):
    """Inteiro de reais -> 'R$ 1.234' (ou '− R$ 1.234' se negativo)."""
    return ("R$%s%s" % (NB, _milhar(v))) if v >= 0 else ("−%sR$%s%s" % (NB, NB, _milhar(-v)))


def pct1(x):
    """Percentual com uma casa e vírgula: 13.04 -> '13,0'."""
    return ("%.1f" % x).replace(".", ",")


def pl(n, singular, plural):
    """'1 título', '2 títulos': o número com o substantivo no singular ou no plural."""
    return "%d %s" % (n, singular if n == 1 else plural)


def arred(x):
    """Arredonda meio para cima (6,5 -> 7), como a pessoa espera. round() do Python arredondaria 6,5 para 6."""
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def _dias(n):
    n = arred(n)
    return "%d dia%s" % (n, "" if abs(n) == 1 else "s")


def _aprox(x):
    return _dias(x)


def _tempo(horas):
    if horas < 1:
        return "menos de 1 hora"
    if horas < 48:
        return "%d horas" % arred(horas)
    return _dias(int(horas // 24))


def situacao(f):
    c = f["cliente"]
    n = f["n"]
    pct = round(100 * f["leitura"]["ocupacao"])  # o mesmo "limite ocupado" (saldo em aberto / limite) da tela Risco
    titulos = "1 título" if n == 1 else "%d títulos" % n
    idade = "está há %s em atraso" % _dias(f["mais_antigo"]) if n == 1 else \
        "o mais antigo está há %s em atraso" % _dias(f["mais_antigo"])
    return "%s tem %s vencidos em %s (o saldo em aberto dele ocupa %d%% do limite de crédito) e %s" % (
        c["nome"], reais(f["vencido"]), titulos, pct, idade)


def leitura(f):
    """O que o histórico do cliente diz sobre este atraso. Vem da leitura de risco (f["leitura"])."""
    r = f["leitura"]
    p, c, tags = r["pag"], r["compras"], r["tags"]
    if "parou" in tags:
        return ("parou de comprar: o último pedido foi há %s e o maior intervalo dele entre pedidos, em toda a história, foi de %s"
                % (_dias(c["dias_sem_comprar"]), _dias(c["gap_max"])))
    if "piorou" in tags:
        return ("piorou: hoje paga com cerca de %s de atraso, contra %s no resto da história, e nunca deixou de pagar"
                % (_aprox(p["rec_med"]), _aprox(p["base_med"])))
    if not p["ok"]:
        return "ainda tem poucos pagamentos registrados (%d), então não dá para dizer se é atraso normal dele" % r["n_pagos"]
    pior = max(r["vencidos"], key=lambda t: t["posicao"])
    if pior["posicao"] >= 0.95:
        if f["mais_antigo"] > p["maximo"]:
            return ("isso foge do padrão dele: em %d títulos pagos o maior atraso foi de %s e este já passou disso"
                    % (r["n_pagos"], _dias(p["maximo"])))
        return "está entre os maiores atrasos que ele já teve (o máximo em %d títulos pagos foi %s)" % (
            r["n_pagos"], _dias(p["maximo"]))
    if pior["posicao"] <= 0.25:
        return ("isso é o ritmo normal dele: costuma pagar com cerca de %s de atraso, então não é sinal de problema"
                % _aprox(p["mediana"]))
    return ("já está mais lento do que ele costuma ser (paga com cerca de %s de atraso) e pode virar problema se não for "
            "acompanhado" % _aprox(p["mediana"]))


def frase(f):
    texto = situacao(f)
    lei = leitura(f)
    if f["cobrado_recente"]:
        cob = f["cobranca"]
        return "%s; %s; como já foi cobrado por %s há %s (%s), desce na fila para não insistir hoje." % (
            texto, lei, cob["canal"], _tempo(f["horas_desde_cobranca"]), cob["tom"].lower())
    return "%s; %s." % (texto, lei)


def ultimo_contato(f):
    cob = f["cobranca"]
    if not cob:
        return "Nenhuma cobrança registrada para este cliente."
    return "Última cobrança: %s por %s, há %s, tom \"%s\", sobre %s em %d título%s." % (
        cob["quando"].strftime("%d/%m às %H:%M"), cob["canal"], _tempo(f["horas_desde_cobranca"]),
        cob["tom"], reais(cob["valor"]), cob["n_titulos"], "" if cob["n_titulos"] == 1 else "s") + (
        " Registrada na Central." if cob.get("origem") == "Central" else "")


# ------------------------------------------------------------------------------------------------ versões curtas (visual)
FAIXA_ALTO, FAIXA_MEDIO = 60, 30  # índice de risco: >= 60 risco alto, 30 a 59 médio, abaixo disso baixo


def faixa_risco(indice):
    """(chave, palavra) da gravidade pelo índice de risco 0–100. A cor da tela sempre vem com esta palavra."""
    if indice >= FAIXA_ALTO:
        return "alto", "Risco alto"
    if indice >= FAIXA_MEDIO:
        return "medio", "Risco médio"
    return "baixo", "Risco baixo"


def motivo_curto(f):
    """Uma frase de até ~110 caracteres: por que este cliente está na fila. Só usa os fatos de `leitura` (mesmos números)."""
    r = f["leitura"]
    p, c, tags = r["pag"], r["compras"], r["tags"]
    if "parou" in tags:
        return "Parou de comprar: último pedido há %s; o maior intervalo dele foi de %s." % (_dias(c["dias_sem_comprar"]), _dias(c["gap_max"]))
    if "piorou" in tags:
        return "Piorou: paga com cerca de %s de atraso, contra %s no resto da história." % (_aprox(p["rec_med"]), _aprox(p["base_med"]))
    if not p["ok"]:
        return "Pouco histórico: só %d pagamentos registrados." % r["n_pagos"]
    pior = max(r["vencidos"], key=lambda t: t["posicao"])
    if pior["posicao"] >= 0.95:
        if f["mais_antigo"] > p["maximo"]:
            return "Fora do padrão: já passou do maior atraso dele (%s)." % _dias(p["maximo"])
        return "Entre os maiores atrasos dele (o máximo foi %s)." % _dias(p["maximo"])
    if pior["posicao"] <= 0.25:
        return "Ritmo normal dele: costuma pagar com cerca de %s de atraso." % _aprox(p["mediana"])
    return "Mais lento que o normal dele (costuma pagar com cerca de %s de atraso)." % _aprox(p["mediana"])


def contexto_curto(f):
    """Segunda linha do cartão: o que é o vencido, em poucas palavras (os fatos que a frase completa também traz)."""
    c = f["cliente"]
    titulos = "1 título" if f["n"] == 1 else "%d títulos" % f["n"]
    return "%s · mais antigo há %s · %s · %s" % (titulos, _dias(f["mais_antigo"]), c["categoria"], c["regiao"])


def envolve_dinheiro(html):
    """Em texto JÁ escapado, põe cada valor em reais num <span class="din"> (cor própria do dinheiro em todo o sistema)."""
    import re
    return re.sub(r"((?:−\u00a0)?R\$\u00a0[\d.]+(?:,\d{2})?)", r'<span class="din">\1</span>', html)
