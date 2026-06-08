# 🟢 Deploy con Easypanel — PropTech PDE

Tu VPS ya tiene **Easypanel** (gestiona dominio + HTTPS automático con Traefik).
Esta guía despliega la app dentro de Easypanel desde GitHub.

---

## PARTE 1 — Subir el código a GitHub

### 1.1 Crear el repo (en github.com)
1. Entrá a https://github.com/new
2. Nombre: `proptech-pde`
3. Privado o público (da igual)
4. **NO** marques "Add README" (el repo local ya tiene todo)
5. Click **Create repository**

### 1.2 Pushear (en tu Mac, dentro de ~/proptech-pde)
```bash
cd ~/proptech-pde
git branch -M main
git remote add origin https://github.com/TU_USUARIO/proptech-pde.git
git push -u origin main
```
> Si pide login: usá tu usuario de GitHub y un **Personal Access Token** como
> contraseña (Settings → Developer settings → Tokens → "classic", scope `repo`).
> O configurá SSH si ya lo usás.

---

## PARTE 2 — Desplegar en Easypanel

### 2.1 Entrar a Easypanel
Abrí `https://82.25.69.18` (o tu dominio de Easypanel) y logueate.

### 2.2 Crear el proyecto
- **Create Project** → nombre: `proptech`

### 2.3 Agregar servicio Compose
- Dentro del proyecto → **+ Service** → **Compose**
- **Source**: GitHub → autorizá y elegí el repo `proptech-pde`, rama `main`
- **Compose file path**: `docker-compose.easypanel.yml`

### 2.4 Variables de entorno del servicio
En el servicio Compose → pestaña **Environment**, pegá (con TUS valores):
```
POSTGRES_USER=proptech
POSTGRES_PASSWORD=0KfQO4gKOxomzoKf6TMQux9M
POSTGRES_DB=proptech_pde
SECRET_KEY=07bf4e350d943c678c25e92ead5a2d4f2a7f8ba1caadf8fb7f522b1080bd19f5
JWT_SECRET_KEY=b95e8bc446bb6c9d29a42b3920b8e0a58e0008e2d05ad4ea9c44ed1181ce3ab3
```
*(opcional, para IA/alertas: `OPENAI_API_KEY`, `WHATSAPP_TOKEN`, `TELEGRAM_BOT_TOKEN`,
`ML_CLIENT_ID`, `ML_CLIENT_SECRET`)*

### 2.5 Deploy
- Click **Deploy**. Easypanel buildea los servicios (tarda unos minutos la 1ª vez).

### 2.6 Asignar el dominio al frontend
- En el servicio, ubicá el contenedor **`frontend`** (puerto **3000**).
- **Domains** → **Add Domain**:
  - Dominio: `dynamiclabsai.com` (y/o `www.dynamiclabsai.com`)
  - Puerto: `3000`
  - **HTTPS**: activado (Easypanel emite el certificado solo)
- Guardá. Easypanel configura Traefik + SSL automáticamente.

> ⚠️ Antes, el DNS de `dynamiclabsai.com` debe apuntar a `82.25.69.18`
> (registro A). Hoy apunta a 2.57.91.91 — cambialo en tu gestor de DNS.

---

## PARTE 3 — Inicializar datos (una vez)

Cuando los servicios estén "running", abrí la **consola** del servicio `api`
en Easypanel (o `Terminal`) y corré:

```bash
python -m app.db.seeds          # usuarios + 20 zonas
python -m app.scrapers.runner --all   # primer scraping (4 fuentes)
```
*(Las tablas + extensión PostGIS se crean solas al arrancar el `api`.)*

---

## ✅ Resultado
- App: **https://dynamiclabsai.com** con HTTPS real
- Login: `admin@proptech.uy` / `admin123` (cambiala)
- Scraping automático cada 4–8 h (Celery Beat ya corre en el servicio `beat`)

---

## 🔄 Updates futuros
Cada vez que hagas `git push`, en Easypanel → servicio → **Deploy** (o activá
auto-deploy por webhook). Easypanel rebuildea y aplica.

## 🆘 Troubleshooting
| Problema | Solución |
|---|---|
| Build falla en frontend | Verificá que `next.config.js` tenga `output: "standalone"` (ya está) |
| `api` reinicia | Revisá logs; suele ser DB no lista — esperá al healthcheck de postgres |
| Dominio no carga | DNS aún apunta a 2.57.91.91; esperá propagación |
| 404 en /api | El dominio debe ir al servicio `frontend` (3000), no al `api` |
