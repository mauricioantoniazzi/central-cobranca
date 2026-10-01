"""O relógio da Central.

O "hoje" da Central é a data de referência da base (12/08/2026), nunca a data do computador.
Só a hora do dia vem do relógio da máquina, para o registro de uma cobrança ter hora de verdade.
Para testes, a variável de ambiente CENTRAL_HORA=HH:MM fixa a hora.
"""
import os
from datetime import datetime, time


def agora(ref):
    fixa = os.environ.get("CENTRAL_HORA")
    if fixa:
        h, m = (int(x) for x in fixa.split(":"))
    else:
        n = datetime.now()
        h, m = n.hour, n.minute
    return datetime.combine(ref, time(h, m))
