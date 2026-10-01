"""Junta, num lugar só, os dados que as telas precisam, sempre pelos mesmos caminhos de cálculo."""
import os

import motor
import registro
import risco
import validacao

PASTA = os.path.dirname(os.path.abspath(__file__))
PADRAO = os.path.join(PASTA, "Base_bruta.xlsx")
BASE = PADRAO  # nome antigo, mantido


def caminho_base():
    """A planilha em uso: Base_bruta.xlsx ao lado do código, ou o arquivo da variável de ambiente CENTRAL_BASE."""
    return os.environ.get("CENTRAL_BASE") or PADRAO


def painel(base=None):
    base = base or caminho_base()
    """Hoje, risco e cobranças (planilha da empresa + registradas na Central) com o mesmo relógio da base."""
    central = registro.como_cobrancas()
    ref0, clientes0, titulos0, da_planilha = motor.carregar(base)  # já valida a planilha: levanta BaseInvalida com a explicação
    avisos = validacao.avisos(ref0, clientes0, titulos0, da_planilha)
    ref, rs, n_lista = risco.analisar(base)
    resumo, fila = motor.calcular(base, extras=central, leitura={r["cliente"]["codigo"]: r for r in rs})
    todas = sorted(da_planilha + central, key=lambda c: c["quando"])
    return {"avisos": avisos, "ref": ref, "resumo": resumo, "fila": fila, "rs": rs, "n_lista": n_lista,
            "cobrancas": todas, "da_planilha": da_planilha, "da_central": central,
            "risco_por_cliente": {r["cliente"]["codigo"]: r for r in rs}}
