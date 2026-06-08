#!/usr/bin/env bash
# ============================================================
# PropTech PDE — Deploy a Producción (VPS)
# Orquesta: build, HTTPS (Let's Encrypt), DB, migraciones y seed.
#
# Uso:
#   sudo ./scripts/deploy.sh tu-dominio.com tu-email@dominio.com
# ============================================================
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Uso: ./scripts/deploy.sh <dominio> <email>"
  echo "Ej:  ./scripts/deploy.sh app.proptech.uy admin@proptech.uy"
  exit 1
fi

green() { echo -e "\033[32m$*\033[0m"; }
blue()  { echo -e "\033[34m$*\033[0m"; }

# ─── 1. Verificar requisitos ────────────────────────────────
blue "▶ 1/7 Verificando Docker..."
command -v docker >/dev/null || { echo "Instalá Docker primero"; exit 1; }

# ─── 2. Preparar .env ───────────────────────────────────────
blue "▶ 2/7 Configurando entorno..."
if [[ ! -f .env ]]; then
  cp .env.example .env
  # Generar secrets seguros
  SK=$(openssl rand -hex 32); JWT=$(openssl rand -hex 32)
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SK|" .env
  sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT|" .env
  sed -i "s|^APP_ENV=.*|APP_ENV=production|" .env
  sed -i "s|^DEBUG=.*|DEBUG=false|" .env
  sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://$DOMAIN|" .env
  sed -i "s|^NEXT_PUBLIC_APP_URL=.*|NEXT_PUBLIC_APP_URL=https://$DOMAIN|" .env
  sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN|" .env
  green "  ✓ .env generado con secrets nuevos. REVISÁ las claves de IA/WhatsApp."
else
  green "  ✓ .env ya existe (no se sobrescribe)"
fi

# ─── 3. Config de Nginx con tu dominio ──────────────────────
blue "▶ 3/7 Generando config Nginx para $DOMAIN..."
rm -f docker/nginx/conf.d/default.conf
sed "s/__DOMAIN__/$DOMAIN/g" docker/nginx/conf.d/proptech.conf.template \
  > docker/nginx/conf.d/proptech.conf
green "  ✓ proptech.conf generado"

# ─── 4. Certificado SSL (Let's Encrypt) ─────────────────────
blue "▶ 4/7 Emitiendo certificado SSL..."
mkdir -p docker/certbot/www docker/certbot/conf
# Arrancar nginx temporal solo-HTTP para el challenge
cat > docker/nginx/conf.d/proptech.conf <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 'ok'; }
}
EOF
$COMPOSE up -d nginx
sleep 5
docker run --rm \
  -v "$(pwd)/docker/certbot/www:/var/www/certbot" \
  -v "$(pwd)/docker/certbot/conf:/etc/letsencrypt" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d "$DOMAIN" -d "www.$DOMAIN" \
  --email "$EMAIL" --agree-tos --no-eff-email --non-interactive || {
    echo "⚠ Falló la emisión del certificado. Verificá que el DNS de $DOMAIN apunte a este servidor."; exit 1;
  }
# Restaurar config HTTPS completa
sed "s/__DOMAIN__/$DOMAIN/g" docker/nginx/conf.d/proptech.conf.template \
  > docker/nginx/conf.d/proptech.conf
green "  ✓ Certificado emitido"

# ─── 5. Build y levantar todo ───────────────────────────────
blue "▶ 5/7 Building imágenes (puede tardar)..."
$COMPOSE build
$COMPOSE up -d

# ─── 6. Migraciones + seed ──────────────────────────────────
blue "▶ 6/7 Migraciones y datos iniciales..."
sleep 10
$COMPOSE exec -T api alembic upgrade head || $COMPOSE exec -T api python -c "import asyncio; from app.db.database import init_db; asyncio.run(init_db())"
$COMPOSE exec -T api python -m app.db.seeds || true

# ─── 7. Primer scraping ─────────────────────────────────────
blue "▶ 7/7 Scraping inicial (4 fuentes)..."
$COMPOSE exec -T api python -m app.scrapers.runner --all || true

green ""
green "════════════════════════════════════════════"
green "  ✅ DEPLOY COMPLETO"
green "════════════════════════════════════════════"
green "  App:   https://$DOMAIN"
green "  API:   https://$DOMAIN/api/v1"
green "  Docs:  https://$DOMAIN/docs"
green "  Admin: admin@proptech.uy / admin123  (CAMBIÁ la contraseña)"
green "════════════════════════════════════════════"
