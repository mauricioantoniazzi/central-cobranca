"""Menu das telas da Central: a doca fixa no pé da página. É o que faz as seis telas parecerem um sistema só (mostra todas e acende a atual)."""

CURTOS = {"hoje": "Hoje", "regua": "Régua", "cobrancas": "Cobranças", "risco": "Risco", "previsao": "Previsão", "relatorio": "Relatório"}  # rótulos do celular
ITENS = [("/", "Hoje", "hoje"), ("/regua", "Régua de cobrança", "regua"), ("/cobrancas", "Cobranças feitas", "cobrancas"),
         ("/risco", "Risco por cliente", "risco"), ("/previsao", "Previsão de caixa", "previsao"),
         ("/relatorio", "Relatório da semana", "relatorio")]

_SVG = {
    "hoje": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "regua": '<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-5.4A8 8 0 1 1 21 12z"/><path d="M8.5 11h7M8.5 14.5h4"/>',
    "cobrancas": '<path d="M9 11l2 2 4-4"/><rect x="3.5" y="3.5" width="17" height="17" rx="4"/>',
    "risco": '<path d="M12 3l8 3v6c0 4.6-3.2 7.9-8 9-4.8-1.1-8-4.4-8-9V6z"/><path d="M12 8v4.5M12 15.6v.2"/>',
    "previsao": '<path d="M3 17l5.5-5.5 4 4L21 7"/><path d="M15 7h6v6"/>',
    "relatorio": '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
}


def icone(nome):
    return '<svg viewBox="0 0 24 24" aria-hidden="true">%s</svg>' % _SVG[nome]


def nav(ativa):
    """O menu das telas (fica na coluna da esquerda; no celular vira a barra do pé). Só o nome de cada tela."""
    links = "".join('<a href="%s"%s>%s<span class="t">%s</span><span class="c" aria-hidden="true">%s</span></a>'
                    % (h, ' aria-current="page"' if k == ativa else "", icone(k), t, CURTOS[k]) for h, t, k in ITENS)
    return '<nav class="menu" aria-label="Telas da Central">%s</nav>' % links
