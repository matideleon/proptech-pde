#!/bin/bash
# ============================================================
# PropTech PDE — Script de Setup Completo
# ============================================================
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BLUE}${BOLD}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}${BOLD}║   PropTech PDE — Setup de la Plataforma   ║${NC}"
echo -e "${BLUE}${BOLD}╚═══════════════════════════════════════════╝${NC}"
echo ""

# ─── VERIFICAR REQUISITOS ─────────────────────────────────────
echo -e "${YELLOW}▶ Verificando requisitos...${NC}"

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}✗ $1 no encontrado. Por favor instálalo primero.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ $1 encontrado${NC}"
}

check_command docker
check_command docker-compose || check_command "docker compose"
check_command make

echo ""

# ─── CONFIGURAR .ENV ─────────────────────────────────────────
if [ ! -f .env ]; then
    echo -e "${YELLOW}▶ Creando archivo .env desde .env.example...${NC}"
    cp .env.example .env

    # Generar SECRET_KEY aleatoria
    SECRET_KEY=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 32)

    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/your-super-secret-key-change-in-production-min-32-chars/${SECRET_KEY}/" .env
        sed -i '' "s/your-jwt-secret-key-change-in-production/${JWT_SECRET}/" .env
    else
        sed -i "s/your-super-secret-key-change-in-production-min-32-chars/${SECRET_KEY}/" .env
        sed -i "s/your-jwt-secret-key-change-in-production/${JWT_SECRET}/" .env
    fi

    echo -e "${GREEN}✓ .env creado con claves aleatorias${NC}"
    echo -e "${YELLOW}⚠️  Edita .env y agrega tus claves de API (OpenAI, WhatsApp, Telegram, etc.)${NC}"
else
    echo -e "${GREEN}✓ .env ya existe${NC}"
fi

echo ""

# ─── BUILD Y LEVANTAR SERVICIOS ──────────────────────────────
echo -e "${YELLOW}▶ Construyendo imágenes Docker...${NC}"
docker compose build

echo ""
echo -e "${YELLOW}▶ Levantando servicios...${NC}"
docker compose up -d postgres redis

echo -e "${YELLOW}▶ Esperando que la DB esté lista...${NC}"
sleep 5

# Verificar que postgres está listo
until docker compose exec -T postgres pg_isready -U proptech -d proptech_pde 2>/dev/null; do
    echo "Esperando PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL listo${NC}"

# ─── MIGRATIONS ───────────────────────────────────────────────
echo ""
echo -e "${YELLOW}▶ Corriendo migrations...${NC}"
docker compose up -d api
sleep 5
docker compose exec api alembic upgrade head
echo -e "${GREEN}✓ Migrations completadas${NC}"

# ─── SEEDS ───────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}▶ Insertando datos iniciales...${NC}"
docker compose exec api python -m app.db.seeds
echo -e "${GREEN}✓ Seeds completados${NC}"

# ─── LEVANTAR TODOS LOS SERVICIOS ────────────────────────────
echo ""
echo -e "${YELLOW}▶ Levantando todos los servicios...${NC}"
docker compose up -d

echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║      ✅ Setup completado exitosamente!     ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}🌐 Frontend:${NC}     http://localhost:3000"
echo -e "  ${BLUE}🔌 API Docs:${NC}     http://localhost:8000/docs"
echo -e "  ${BLUE}📊 Metabase:${NC}     http://localhost:3001"
echo -e "  ${BLUE}🗄️  PGAdmin:${NC}      http://localhost:5050"
echo -e "  ${BLUE}🌸 Flower:${NC}       http://localhost:5555"
echo ""
echo -e "  ${YELLOW}Credenciales admin:${NC}"
echo -e "  Email: admin@proptech.uy"
echo -e "  Pass:  admin123"
echo ""
echo -e "  ${YELLOW}Para iniciar scraping:${NC}"
echo -e "  make scrape"
echo ""
