#!/bin/bash
# Restaura o dump do hackathon no banco criado pelo entrypoint (só roda com o volume vazio).
set -euo pipefail

DUMP=/dump/fortuna_hackathon.dump
if [ ! -f "$DUMP" ] || [ ! -s "$DUMP" ]; then
  echo "ERRO: dump não encontrado em $DUMP. Copie fortuna_hackathon.dump para ./data/ ou defina FORTUNA_DUMP no .env." >&2
  exit 1
fi

echo "Restaurando $DUMP em $POSTGRES_DB..."
pg_restore --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$DUMP"

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT tipo_base, count(*) FROM hackathon.pedidos GROUP BY 1 ORDER BY 1"
echo "Esperado: historico = 10000 e novo = 2000."
