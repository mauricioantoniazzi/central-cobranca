"""Segunda parte da recontagem independente: índice de risco, valor em risco e previsão, refeitos das regras
escritas nas telas (fatores, pesos, premissas), sem olhar o código da Central."""
import datetime as dt
import math
import statistics as st

import independente as ind
from independente import arred, quantil, tudo


def posicao(valor_d, ref_set):
    n = len(ref_set)
    return (sum(1 for x in ref_set if x < valor_d) + sum(1 for x in ref_set if x == valor_d) / 2) / n


def indice_e_previsao():
    R = tudo()
    tit, C = R["tit"], R["C"]
    saida = {}
    for c, x in C.items():
        ts = [t for t in tit if t["cli"] == c]
        pagos = [t for t in ts if t["pago"]]
        vc = [t for t in ts if t["pago"] is None and t["venc"] < ind.REF]
        tem_hist = "med_ns" in x  # cliente com menos de 20 pagamentos não tem padrão: os fatores de pagamento ficam sem dado
        saz = set(x.get("sazonais", []))
        atr_all = [(t["pago"] - t["venc"]).days for t in pagos]
        pesos = {"habitual": 10, "variacao": 15, "piora": 25, "compras": 20, "limite": 10, "vencido": 20}
        f = {}
        f["habitual"] = min(1, x["med_ns"] / 30) if tem_hist else None
        f["variacao"] = min(1, (x["p90_ns"] - x["p10_ns"]) / 40) if tem_hist else None
        # piora
        if "base_med" in x and "rec_med_misto" in x:
            d_det = x["rec_med_misto"] - x["base_med"]
            ds_det = d_det / x["base_sig"]
            if x["piora"]:
                d_show = (x["rec_med_pagos"] - x["base_med"]) if x["rec_med_pagos"] is not None and x["n_rec_pagos"] >= 3 else d_det
                ds = d_show / x["base_sig"]
                f["piora"] = 0.5 + 0.5 * min(1, (ds - 2) / 4)
            else:
                f["piora"] = 0.1 * min(1, max(ds_det, 0) / 2)
        else:
            f["piora"] = None
        # compras
        if x["dias_sem_comprar"] > x.get("gap_max", 10 ** 9):
            f["compras"] = 1.0
        elif "queda" in x:
            q = x["queda"]
            conf = q >= .25 and x["compras_rec"] < x["compras_media"] - 1.5 * x["compras_dp"]
            f["compras"] = (0.5 + 0.5 * min(1, (q - .25) / .5)) if conf else 0.15 * min(1, max(q, 0) / .25)
        else:
            f["compras"] = None
        f["limite"] = min(1, x["ocupacao"])
        # vencido fora do padrão
        pos = {}
        if not vc:
            f["vencido"] = 0.0
        elif not tem_hist:
            f["vencido"] = None
        else:
            for t in vc:
                d = (ind.REF - t["venc"]).days
                em_saz = t["venc"].month in saz
                ref_set = [(p["pago"] - p["venc"]).days for p in pagos if (p["venc"].month in saz) == em_saz]
                if len(ref_set) < 8:
                    ref_set = atr_all
                pos[t["num"]] = posicao(d, ref_set)
            f["vencido"] = max(pos.values())
        usados = {k: v for k, v in f.items() if v is not None}
        soma_pesos = sum(pesos[k] for k in usados)
        indice = arred(100 * sum(pesos[k] * v for k, v in usados.items()) / soma_pesos)
        saida[c] = {"indice": indice, "valor_em_risco": x["saldo"] * indice / 100, "f": f, "parcial": soma_pesos < 100, "pos": pos}

    # previsão
    ini_janela, fim_janela = ind.REF + dt.timedelta(days=1), ind.REF + dt.timedelta(days=28)
    semanas = lambda d: ((d - ind.REF).days - 1) // 7 if 1 <= (d - ind.REF).days <= 28 else None
    tot = {"esp": [0] * 4, "cons": [0] * 4, "otim": [0] * 4}
    prev_cli = {}
    decomp = {"adiado": 0, "sem_data": 0, "prob": 0, "antec": 0}
    for c, x in C.items():
        ts = [t for t in tit if t["cli"] == c and t["pago"] is None]
        pagos = [t for t in tit if t["cli"] == c and t["pago"]]
        saz = set(x.get("sazonais", []))
        corte = ind.REF - dt.timedelta(days=90)
        ns_all = [(t["pago"] - t["venc"]).days for t in pagos if t["venc"].month not in saz]
        tem_hist = "med_ns" in x
        rec_p = [(t["pago"] - t["venc"]).days for t in pagos if t["venc"].month not in saz and t["venc"] >= corte]
        piorou = x.get("piora") is True
        prev_cli[c] = 0
        for t in ts:
            d = (ind.REF - t["venc"]).days
            if not tem_hist:  # sem padrão de pagamento não há data esperada: o título entra na conta como "sem data"
                if (t["venc"] <= ind.REF) or (t["venc"] - ind.REF).days <= 28:
                    decomp["sem_data"] += t["valor"] * 100
                continue
            mes = t["venc"].month
            saz_set = [(p["pago"] - p["venc"]).days for p in pagos if p["venc"].month == mes]
            if mes in saz and len(saz_set) >= 3:
                regime = saz_set
            elif piorou and len(rec_p) >= 3:
                regime = rec_p
            else:
                regime = ns_all
            base = regime
            if d > 0:
                base = [a for a in regime if a >= d]
                if len(base) < 3:
                    base = [a for a in ns_all if a >= d]
            na_plan = (t["venc"] <= ind.REF) or (t["venc"] - ind.REF).days <= 28
            if d > 0 and len(base) < 3:
                if na_plan:
                    decomp["sem_data"] += t["valor"] * 100
                continue
            datas = {k: max(t["venc"] + dt.timedelta(days=arred(quantil(base, q))), ind.REF + dt.timedelta(days=1))
                     for k, q in (("esp", .5), ("cons", .9), ("otim", .1))}
            pos_t = saida[c]["pos"].get(t["num"], 0) if d > 0 else 0
            p = (1 - .30 * saida[c]["indice"] / 100) * (1 - .50 * pos_t)
            bp = int(round(p * 10000))
            esperado = t["valor"] * 100 * bp // 10000
            for k in tot:
                s = semanas(datas[k])
                if s is not None:
                    tot[k][s] += esperado
            s_esp = semanas(datas["esp"])
            if s_esp is not None:
                prev_cli[c] += esperado
            if na_plan and s_esp is not None:
                decomp["prob"] += t["valor"] * 100 - esperado
            elif na_plan:
                decomp["adiado"] += t["valor"] * 100
            elif s_esp is not None:
                decomp["antec"] -= esperado
    R["ind"] = saida
    R["prev_sem"] = tot
    R["prev_cli"] = prev_cli
    R["decomp"] = decomp
    return R


if __name__ == "__main__":
    R = indice_e_previsao()
    for c, s in R["ind"].items():
        print(c, R["C"][c]["nome"][:22], "indice", s["indice"], "parcial", s["parcial"], "VR", round(s["valor_em_risco"], 2))
    cum = {k: [sum(v[:i + 1]) / 100 for i in range(4)] for k, v in R["prev_sem"].items()}
    print("acum", cum)
    print("decomp", {k: v / 100 for k, v in R["decomp"].items()})
    print("prev por cliente", {c: v / 100 for c, v in R["prev_cli"].items()})
