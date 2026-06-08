# 🚀 Guía de Deploy en VPS — PropTech PDE

Guía completa para poner la plataforma en producción con **dominio propio**,
**HTTPS real** (Let's Encrypt) y las **4 fuentes de scraping** corriendo
automáticamente. Sin el aviso de localtunnel.

---

## 📋 Requisitos previos

| Recurso | Recomendado | Costo aprox. |
|---|---|---|
| **VPS** | 4 vCPU / 8 GB RAM / 80 GB SSD | ~$24–40 USD/mes |
| **Sistema** | Ubuntu 22.04 LTS | — |
| **Dominio** | ej. `proptech.uy` | ~$15 USD/año |

Proveedores sugeridos: Hetzner (mejor precio), DigitalOcean, Vultr, Linode.

---

## 1️⃣ Apuntar el dominio al VPS

En tu proveedor de DNS (donde compraste el dominio), creá dos registros **A**:

```
A    @      → IP_DE_TU_VPS
A    www    → IP_DE_TU_VPS
```

> Esperá 5–30 min a que propague. Verificá con: `dig +short tu-dominio.com`

---

## 2️⃣ Preparar el VPS

Conectate por SSH e instalá Docker:

```bash
ssh root@IP_DE_TU_VPS

# Instalar Docker + Compose
curl -fsSL https://get.docker.com | sh
apt-get install -y git make

# (opcional) usuario no-root
adduser deploy && usermod -aG docker deploy
```

---

## 3️⃣ Clonar el proyecto

```bash
git clone https://github.com/tu-org/proptech-pde.git
cd proptech-pde
```

---

## 4️⃣ Deploy automático (un comando)

```bash
sudo ./scripts/deploy.sh tu-dominio.com tu-email@dominio.com
```

El script hace **todo**:
1. ✅ Verifica Docker
2. ✅ Genera `.env` con secrets seguros (SECRET_KEY, JWT)
3. ✅ Configura Nginx para tu dominio
4. ✅ Emite certificado **SSL Let's Encrypt** (HTTPS real)
5. ✅ Buildea las imágenes (backend, frontend)
6. ✅ Corre migraciones + seed (usuarios, 20 zonas)
7. ✅ Ejecuta el scraping inicial de las 4 fuentes

Al terminar, tu app está en **https://tu-dominio.com** 🎉

---

## 5️⃣ Configurar credenciales (importante)

Editá el `.env` para activar todas las funciones:

```bash
nano .env
```

```ini
# IA (resúmenes, scoring) — opcional pero recomendado
OPENAI_API_KEY=sk-...

# Alertas
WHATSAPP_TOKEN=...
TELEGRAM_BOT_TOKEN=...
SENDGRID_API_KEY=SG...

# MercadoLibre (ya configurado con tu app)
ML_CLIENT_ID=757343000940978
ML_CLIENT_SECRET=...
```

Reiniciá para aplicar: `make prod-up` (o `docker compose ... up -d`).

---

## 6️⃣ Scraping automático (cron)

El servicio **Celery Beat** ya corre y programa los scrapers. Frecuencias por
defecto (editables en `app/workers/celery_app.py`):

| Fuente | Frecuencia |
|---|---|
| MercadoLibre | cada 4 h |
| InfoCasas | cada 6 h |
| Facebook Marketplace | cada 8 h |
| Gallito | cada 8 h |

Monitoreá las tareas en **https://tu-dominio.com:5555** (Flower, perfil `tools`).

---

## 🔐 Checklist de seguridad post-deploy

- [ ] **Cambiar contraseña admin** (`admin@proptech.uy / admin123`)
- [ ] Verificar que Postgres y Redis **NO** estén expuestos (el override prod ya lo hace)
- [ ] Configurar firewall: `ufw allow 22,80,443/tcp && ufw enable`
- [ ] Activar backups automáticos (ver abajo)
- [ ] Considerar ocultar `/docs` en prod (comentar el bloque en `proptech.conf`)

---

## 💾 Backups automáticos

Agregá a `crontab -e`:

```bash
# Backup diario de la DB a las 3 AM
0 3 * * * cd /root/proptech-pde && make backup
```

Restaurar: `make restore FILE=backups/backup_YYYYMMDD.sql.gz`

---

## 🔄 Comandos útiles en producción

```bash
make prod-up        # levantar
make prod-down      # bajar
make logs           # ver logs
make scrape         # scraping manual
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps   # estado
```

Actualizar a una nueva versión:
```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose ... exec api alembic upgrade head
```

---

## 🩺 Troubleshooting

| Síntoma | Causa / Solución |
|---|---|
| Certbot falla | DNS no apunta al VPS aún. Esperá propagación y reintentá. |
| 502 Bad Gateway | El backend/frontend no levantó. `make logs` para ver el error. |
| Scrapers traen 0 | Los portales cambiaron HTML o bloquearon IP. Considerá proxies. |
| Memoria alta | Bajá `--concurrency` de Celery o subí el plan del VPS. |

---

## 📈 Escalado futuro (SaaS)

Cuando crezcas:
- **DB gestionada** (Supabase / RDS) en vez de Postgres en el mismo VPS
- **Proxies rotativos** para scraping a mayor escala (Bright Data, Oxylabs)
- **CDN** (Cloudflare) delante de Nginx
- **Multi-tenant**: separar datos por inmobiliaria (columna `tenant_id`)
- **Horizontal**: varios workers de Celery en VPS separados

---

## 💰 Costo mensual estimado (producción)

| Componente | USD/mes |
|---|---|
| VPS 4vCPU/8GB | 24–40 |
| Dominio | ~1.25 |
| OpenAI API (uso moderado) | 30–80 |
| WhatsApp Business API | ~20 |
| **Total** | **~75–140 USD/mes** |
