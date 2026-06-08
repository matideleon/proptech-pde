#!/usr/bin/env bash
# ============================================================
# PropTech PDE — Deploy por IP (sin dominio, HTTP)
# Para arrancar rápido en un VPS sin dominio todavía.
# El HTTPS se agrega luego con scripts/deploy.sh <dominio> <email>.
#
# Uso:  sudo ./scripts/deploy-ip.sh
# ============================================================
set -euo pipefail

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

green() { echo -e "\033[32m$*\033[0m"; }
blue()  { echo -e "\033[34m$*\033[0m"; }

# IP pública del VPS (para mostrarla al final)
IP=$(curl -s --max-time 8 https://ipv4.icanhazip.com 2>/dev/null || hostname -I | awk '{print $1}')

blue "▶ 1/6 Verificando Docker..."
command -v docker >/dev/null || { echo "Instalá Docker: curl -fsSL https://get.docker.com | sh"; exit 1; }

blue "▶ 2/6 Configurando entorno (.env)..."
if [[ ! -f .env ]]; then
  cp .env.example .env
  SK=$(openssl rand -hex 32); JWT=$(openssl rand -hex 32)
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SK|" .env
  sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT|" .env
  sed -i "s|^APP_ENV=.*|APP_ENV=production|" .env
  sed -i "s|^DEBUG=.*|DEBUG=false|" .env
  # API por ruta relativa (Nginx enruta /api/ al backend) → sirve en cualquier IP
  sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=|" .env
  sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=*|" .env
  green "  ✓ .env generado con secrets seguros"
else
  green "  ✓ .env ya existe (no se sobrescribe)"
fi

blue "▶ 3/6 Liberando puerto 80 y configurando Nginx HTTP..."
# Parar servidores web del sistema que ocupen el puerto 80 (Apache/Nginx default)
systemctl stop apache2 nginx httpd 2>/dev/null || true
systemctl disable apache2 nginx httpd 2>/dev/null || true
# Usar el default.conf (catch-all HTTP). Quitar config de dominio si existe.
rm -f docker/nginx/conf.d/proptech.conf
if [[ ! -f docker/nginx/conf.d/default.conf ]]; then
  echo "Falta docker/nginx/conf.d/default.conf"; exit 1
fi
if ss -tlnp 2>/dev/null | grep -q ':80 '; then
  echo "  ⚠ Algo sigue usando el puerto 80. Mostralo con: ss -tlnp | grep ':80 '"
fi
green "  ✓ Nginx HTTP listo"

blue "▶ 4/6 Building imágenes (puede tardar varios minutos)..."
$COMPOSE build

blue "▶ 5/6 Levantando servicios (sin certbot)..."
$COMPOSE up -d   # certbot tiene profile 'ssl', no arranca

blue "▶ 6/6 Migraciones, seed y scraping inicial..."
sleep 12
$COMPOSE exec -T api alembic upgrade head 2>/dev/null || \
  $COMPOSE exec -T api python -c "import asyncio; from app.db.database import init_db; asyncio.run(init_db())"
$COMPOSE exec -T api python -m app.db.seeds || true
$COMPOSE exec -T api python -m app.scrapers.runner --all || true

green ""
green "════════════════════════════════════════════"
green "  ✅ DEPLOY POR IP COMPLETO"
green "════════════════════════════════════════════"
green "  App:   http://$IP"
green "  API:   http://$IP/api/v1"
green "  Docs:  http://$IP/docs"
green "  Admin: admin@proptech.uy / admin123  (cambiá la contraseña)"
green ""
green "  Cuando tengas dominio, agregá HTTPS con:"
green "    ./scripts/deploy.sh tu-dominio.com tu-email@dominio.com"
green "════════════════════════════════════════════"
