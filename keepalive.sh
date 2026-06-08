#!/usr/bin/env bash
# ============================================================
# PropTech PDE — Keepalive (arquitectura cloudflared)
# Vigila: backend (uvicorn), frontend (next) y el túnel cloudflared.
# El frontend proxea el API → un solo túnel público.
# La URL pública vigente se escribe en /tmp/pde_public_url.txt
#
# Uso:  nohup ./keepalive.sh > /tmp/pde_keepalive.log 2>&1 &
# ============================================================
set -u

ROOT="$HOME/proptech-pde"
URL_FILE="/tmp/pde_public_url.txt"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

start_backend() {
  pkill -f "uvicorn app.main" 2>/dev/null; sleep 1
  cd "$ROOT/backend" && source .venv/bin/activate
  DEBUG=false nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning \
    > /tmp/pde_api.log 2>&1 &
  log "↻ backend reiniciado"
}

start_frontend() {
  pkill -f "next dev" 2>/dev/null; pkill -f "next-server" 2>/dev/null; sleep 2
  cd "$ROOT/frontend" && PORT=3001 nohup npm run dev > /tmp/pde_frontend.log 2>&1 &
  log "↻ frontend reiniciado"
  sleep 12
}

start_tunnel() {
  pkill -f "cloudflared tunnel" 2>/dev/null; sleep 2
  cd "$ROOT" && nohup npx --yes cloudflared tunnel --url http://localhost:3001 \
    > /tmp/cf_frontend.log 2>&1 &
  sleep 18
  local url
  url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /tmp/cf_frontend.log | head -1)
  if [ -n "$url" ]; then
    echo "$url" > "$URL_FILE"
    log "↻ túnel cloudflared → $url"
  else
    log "⚠ túnel cloudflared sin URL aún"
  fi
}

log "🟢 Keepalive iniciado (cloudflared) — vigilando cada 45s"

while true; do
  curl -s -o /dev/null --max-time 8 http://127.0.0.1:8000/health || { log "backend local caído"; start_backend; sleep 5; }
  curl -s -o /dev/null --max-time 8 http://127.0.0.1:3001/ || { log "frontend local caído"; start_frontend; }
  pgrep -f "cloudflared tunnel" >/dev/null || { log "túnel cloudflared MUERTO"; start_tunnel; }
  sleep 45
done
