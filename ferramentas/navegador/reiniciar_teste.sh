#!/bin/bash
# Reinicia a Central DE TESTE na porta 8250 (nunca mexe na porta 8000, que é a do uso de verdade).
# No Windows várias cópias podem escutar a mesma porta ao mesmo tempo (e a antiga continua respondendo com o código velho),
# por isso encerra TODAS as que escutam em 8250 antes de subir a nova.
powershell -NoProfile -Command 'for($i=0;$i -lt 4;$i++){ Get-NetTCPConnection -LocalPort 8250 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; Start-Sleep 1 }'
mkdir -p "$TEMP/cd8250"
cd "$(dirname "$0")/../.."
PORTA=8250 SEM_NAVEGADOR=1 CENTRAL_HORA=10:00 CENTRAL_DADOS="$TEMP/cd8250" PYTHONIOENCODING=utf-8 python central.py > "$TEMP/central8250.log" 2>&1 &
sleep 2.5
head -3 "$TEMP/central8250.log"
