#!/bin/bash
set -e
# El volumen playwright_data se monta como root; aseguramos que appuser pueda escribir.
if [ -d /app/playwright-data ]; then
    chown -R appuser:appuser /app/playwright-data || chmod -R 777 /app/playwright-data || true
fi
exec gosu appuser "$@"
