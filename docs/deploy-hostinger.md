# 🟣 Deploy en Hostinger — PropTech PDE

Guía específica para alojar la plataforma en **Hostinger**.

---

## ⚠️ Lo primero: necesitás un VPS, NO hosting web

| Producto Hostinger | ¿Sirve? | Por qué |
|---|---|---|
| Hosting Web / Compartido | ❌ **NO** | Solo PHP/MySQL/WordPress. No corre Docker, Python, Node ni PostgreSQL. |
| Cloud Hosting | ❌ NO | Igual, orientado a PHP. |
| **VPS Hosting (KVM)** | ✅ **SÍ** | Ubuntu con root + SSH. Corre Docker y todo el stack. |

👉 **Comprá un "VPS Hosting"** en https://www.hostinger.com/vps-hosting

---

## 1️⃣ Qué plan de VPS elegir

El sistema corre Postgres + backend + frontend + workers de scraping. RAM recomendada:

| Plan Hostinger | vCPU / RAM | ¿Recomendado? |
|---|---|---|
| KVM 1 | 1 / 4 GB | Justo, solo para probar |
| **KVM 2** | 2 / 8 GB | ✅ **Ideal** para producción inicial |
| KVM 4 | 4 / 16 GB | Holgado, para crecer |

> Nuestros scrapers **no usan navegador** (HTTP + Googlebot + cloudscraper), así
> que **KVM 2 (8 GB)** alcanza perfecto. Precio promo ~$7–10 USD/mes.

### Al comprar, elegí:
- **Sistema operativo**: `Ubuntu 22.04` (limpio) **o** el template **"Ubuntu 24.04 with Docker"** (te ahorra instalar Docker).
- **Ubicación del servidor**: la más cercana a Uruguay → **Brasil (São Paulo)** o **EE.UU. (este)**.
- **Hostname**: `proptech-pde` (o el que quieras).

---

## 2️⃣ Conseguir el acceso SSH

Cuando el VPS esté listo, en el panel de Hostinger (hPanel → VPS → tu servidor):
- Anotá la **IP pública** del VPS.
- En **"SSH Access"** ves el usuario (`root`) y podés setear/ver la contraseña, o subir tu clave SSH.

Conectate desde tu compu:
```bash
ssh root@TU_IP_DE_HOSTINGER
```

---

## 3️⃣ Apuntar tu dominio

**Si compraste el dominio en Hostinger:**
hPanel → Dominios → tu dominio → **DNS / Nameservers** → Administrar registros DNS → creá:
```
Tipo A   |  Nombre: @     |  Apunta a: TU_IP_DE_HOSTINGER
Tipo A   |  Nombre: www   |  Apunta a: TU_IP_DE_HOSTINGER
```

**Si el dominio es de otro lado:** creá esos mismos registros A en tu proveedor.

> Verificá la propagación: `dig +short tu-dominio.com` debe devolver la IP del VPS.

---

## 4️⃣ Instalar requisitos (si NO usaste el template con Docker)

Ya conectado por SSH:
```bash
curl -fsSL https://get.docker.com | sh
apt-get update && apt-get install -y git
```

Si usaste el template "with Docker", saltá este paso.

---

## 5️⃣ Subir el proyecto al VPS

**Opción A — desde GitHub (recomendado):**
```bash
git clone https://github.com/TU-USUARIO/proptech-pde.git
cd proptech-pde
```

**Opción B — subir por SCP desde tu compu** (si no está en GitHub):
```bash
# Ejecutá ESTO en tu compu, no en el VPS:
cd ~
tar --exclude='proptech-pde/backend/.venv' \
    --exclude='proptech-pde/frontend/node_modules' \
    --exclude='proptech-pde/frontend/.next' \
    --exclude='proptech-pde/backend/proptech_local.db' \
    -czf proptech.tar.gz proptech-pde
scp proptech.tar.gz root@TU_IP:/root/
# Luego en el VPS:
ssh root@TU_IP
tar -xzf proptech.tar.gz && cd proptech-pde
```

---

## 6️⃣ Deploy en un comando

```bash
sudo ./scripts/deploy.sh tu-dominio.com tu-email@dominio.com
```

Esto hace TODO automáticamente:
1. Genera `.env` con secrets seguros
2. Configura Nginx para tu dominio
3. Emite el **certificado SSL (HTTPS)** con Let's Encrypt
4. Buildea backend y frontend
5. Corre migraciones + seed (usuarios, 20 zonas)
6. Lanza el scraping inicial de las 4 fuentes

Al terminar: **https://tu-dominio.com** 🎉 con HTTPS real y sin avisos.

---

## 7️⃣ Configurar el firewall de Hostinger

En hhPanel → VPS → **Firewall**, permití solo:
```
22  (SSH)
80  (HTTP)
443 (HTTPS)
```
El `docker-compose.prod.yml` ya evita exponer Postgres/Redis al exterior.

---

## 8️⃣ Activar credenciales (opcional pero recomendado)

```bash
nano .env
```
Completá: `OPENAI_API_KEY`, `WHATSAPP_TOKEN`, `TELEGRAM_BOT_TOKEN`,
`ML_CLIENT_ID`/`ML_CLIENT_SECRET` (ya los tenés). Reiniciá con `make prod-up`.

---

## ✅ Post-deploy (importante)

- [ ] Cambiar la contraseña de `admin@proptech.uy`
- [ ] Backups diarios: `crontab -e` → `0 3 * * * cd /root/proptech-pde && make backup`
- [ ] Verificar scrapers: hPanel no hace falta, mirá `make logs`

---

## 💡 Alternativa más simple: Coolify en Hostinger

Hostinger VPS ofrece un template de **Coolify** (un "Heroku" self-hosted con UI).
Si preferís deploy con interfaz gráfica en vez de terminal:
1. Comprá el VPS eligiendo el template **Coolify**.
2. Entrá a la UI de Coolify (`http://TU_IP:8000`).
3. Conectá tu repo de GitHub y deployá usando el `docker-compose.yml`.
4. Coolify gestiona SSL, dominios y redeploys automáticos.

Para empezar, el `deploy.sh` por terminal es lo más directo. Coolify conviene si
vas a manejar varios proyectos.

---

## 💰 Costo en Hostinger (estimado)

| Concepto | USD/mes |
|---|---|
| VPS KVM 2 (8 GB) — promo | ~7–10 |
| Dominio (.com / .uy) | ~1.25 |
| OpenAI API (opcional) | 30–80 |
| **Total mínimo funcional** | **~9–12 USD/mes** (sin IA) |

---

## 🆘 Si algo falla

| Problema | Solución |
|---|---|
| `deploy.sh: Permission denied` | `chmod +x scripts/deploy.sh` |
| Certbot falla | El DNS no propagó aún. Esperá y reintentá `./scripts/deploy.sh ...` |
| No conecta por SSH | Revisá IP y que el puerto 22 esté abierto en el firewall de Hostinger |
| 502 al abrir el dominio | `make logs` para ver qué servicio no levantó |
| Memoria llena en KVM 1 | Subí a KVM 2, o reducí `--concurrency` de Celery |
