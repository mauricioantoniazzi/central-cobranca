"""Relatório da semana para a diretoria.

Este módulo NÃO calcula nada. Ele só lê os números que as telas já mostram (motor.py: Hoje; risco.py: Risco
por cliente; previsao.py: Previsão de caixa; registro.py: contatos) e escolhe o que contar. Quem escreve as
frases é redacao.py. Se um número faltar, ele passa a existir onde os outros moram e as telas passam a usá-lo.
"""
import io

import docx_min
import redacao
import regua
import risco
import registro


def _acao(r):
    """Que tipo de providência a leitura de risco pede para este cliente (só classifica, não calcula)."""
    tags = r["tags"]
    if "parou" in tags:
        return "comercial"
    if "piorou" in tags:
        return "conversa"
    if risco.fora_do_padrao(r):
        return "cobrar"
    if "atrasa_igual" in tags:
        return "prazo"
    return None


def contexto(painel, prev, agora):
    rs, ref, resumo = painel["rs"], painel["ref"], painel["resumo"]
    por_fila = {f["cliente"]["codigo"]: f for f in painel["fila"]}
    clientes = []
    for r in rs:  # já vem na ordem do valor em risco, a mesma da tela Risco
        cli, p, c = r["cliente"], r["pag"], r["compras"]
        cod = cli["codigo"]
        f = por_fila.get(cod)
        item = {
            "nome": cli["nome"], "codigo": cod, "saldo": r["saldo"], "vencido": r["vencido"], "n_vencidos": len(r["vencidos"]),
            "indice": r["indice"], "valor_em_risco": r["valor_em_risco"], "tags": r["tags"], "acao": _acao(r),
            "ocupacao": r["ocupacao"], "pct_fat": r["pct_fat"], "parcial": r["parcial"],
            "dias_sem_comprar": c["dias_sem_comprar"], "gap_max": c.get("gap_max"),
            "queda": c.get("queda") if c.get("queda_confirmada") else None,
            "fora": [{"numero": t["numero"], "valor": t["valor"], "dias": t["dias_atraso"], "maximo": p["maximo"]}
                     for t in risco.fora_do_padrao(r)],
            "mais_antigo": max((t["dias_atraso"] for t in r["vencidos"]), default=0),
            "rec_med": p.get("rec_med") if p.get("piora") else None, "base_med": p.get("base_med") if p.get("piora") else None,
            "atraso_habitual": p.get("mediana") if p["ok"] else None,
            "prazo_contrato": cli["prazo_dias"],
            "fins_mes": r["fins_mes"], "fins_mes_vencido": r["fins_mes_vencido"],
            "sazonais": p.get("sazonais") or [],
            "falta_dado": r["faltou"], "maximo": p["maximo"] if p["ok"] else None,
            "cobrado_recente": bool(f and f["cobrado_recente"]),
            "ultimo_contato": ({"quando": f["cobranca"]["quando"], "canal": f["cobranca"]["canal"], "origem": f["cobranca"].get("origem")}
                               if f and f["cobranca"] else None),
        }
        if r["vencidos"]:
            ch, _ = regua.escolher(ref, r, regua.contatos_do_cliente(painel["cobrancas"], cod))
            item["tom_nome"] = regua.nome_tom(ch)
        clientes.append(item)
    return {
        "ref": ref, "resumo": resumo, "risco": risco.totais(rs), "clientes": clientes,
        "contatos": registro.resumo_contatos(painel["cobrancas"], agora),
        "previsao": {
            "fim": prev["semanas"][-1][1], "planilha": prev["total_planilha"], "esperado": prev["total_esp"],
            "conservador": prev["total_cons"], "otimista": prev["total_otim"], "diferenca": prev["diferenca"],
            "decomposicao": prev["dec"], "vencidos_na_planilha": prev["vencidos_na_planilha"],
            "semanas_esperado": prev["cen"]["esp"],
        },
    }


def blocos(painel, prev, agora):
    return redacao.REDATOR.relatorio(contexto(painel, prev, agora))


def docx_bytes(painel, prev, agora):
    buf = io.BytesIO()
    docx_min.salvar(blocos(painel, prev, agora), buf)
    return buf.getvalue()
