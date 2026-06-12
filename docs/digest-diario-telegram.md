# Digest diario de nuevas propiedades (Telegram + dashboard público)

Flujo 100% automático, sin acciones manuales: tu backend manda cada mañana un
mensaje de Telegram con el conteo de nuevas propiedades y un link a un dashboard
siempre vivo.

## Qué se agregó

- **`app/web_dashboard.py`** — página pública `GET /nuevas` (HTML autocontenido).
  Lee la API (`/api/v1/properties`) del lado del cliente y muestra las altas de
  las últimas N horas. Link permanente: `https://dynamiclabsai.com/nuevas`
  (selector 24h / 48h / 72h / 7 días, o `?h=48`).
- **`app/workers/tasks/notify.py`** — tarea Celery `daily_new_digest`: cuenta las
  nuevas de las últimas `DIGEST_WINDOW_HOURS`, arma el mensaje y lo envía por
  **Telegram** con el link al dashboard.
- **`app/workers/celery_app.py`** — job en el Beat a las **7:00 America/Montevideo**
  (`crontab(hour=7, minute=0)`, queue `notifications`).
- **`app/core/config.py` / `.env.example`** — variables del digest.

## Configurar Telegram (una sola vez)

1. En Telegram, abrí **@BotFather** → `/newbot` → seguí los pasos → te da un
   **bot token** (algo como `123456:ABC-DEF...`).
2. Conseguí tu **chat_id**: escribile algo a tu bot, después abrí
   `https://api.telegram.org/bot<TOKEN>/getUpdates` y copiá el `chat.id`.
   (Para un grupo, agregá el bot al grupo y usá el id del grupo, que empieza con `-`.)
3. Completá en tu `.env`:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
PUBLIC_BASE_URL=https://dynamiclabsai.com
DIGEST_WINDOW_HOURS=24
```

## Activación

1. Redeploy del backend (para servir `/nuevas` y cargar el nuevo Celery include).
2. Reiniciá **celery worker** y **celery beat** para tomar el nuevo schedule.
3. Probar sin esperar a las 7am:
   ```bash
   celery -A app.workers.celery_app call app.workers.tasks.notify.daily_new_digest
   ```
   o abrir directamente `https://dynamiclabsai.com/nuevas`.

## Notas

- Si falta `TELEGRAM_BOT_TOKEN` o `TELEGRAM_CHAT_ID`, la tarea no envía y loguea
  el mensaje que habría mandado (modo seguro).
- El dashboard no genera archivos: siempre refleja el estado actual de la API.
- El mensaje usa `parse_mode=HTML` y muestra vista previa del link del dashboard.
