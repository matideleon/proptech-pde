# Digest diario de nuevas propiedades (WhatsApp + dashboard público)

Flujo 100% automático, sin acciones manuales: tu backend manda cada mañana un
WhatsApp con el conteo de nuevas propiedades y un link a un dashboard siempre vivo.

## Qué se agregó

- **`app/web_dashboard.py`** — página pública `GET /nuevas` (HTML autocontenido).
  Lee la API (`/api/v1/properties`) del lado del cliente y muestra las altas de
  las últimas N horas. Link permanente: `https://dynamiclabsai.com/nuevas`
  (selector 24h / 48h / 72h / 7 días, o `?h=48`).
- **`app/workers/tasks/notify.py`** — tarea Celery `daily_new_digest`: cuenta las
  nuevas de las últimas `DIGEST_WINDOW_HOURS`, arma el mensaje y lo envía por
  WhatsApp con el link al dashboard.
- **`app/workers/celery_app.py`** — job en el Beat a las **7:00 America/Montevideo**
  (`crontab(hour=7, minute=0)`, queue `notifications`).
- **`app/core/config.py` / `.env.example`** — nuevas variables (abajo).

## Variables de entorno (en tu `.env`)

```
# Destinatario del digest (formato internacional sin +, ej. 59899XXXXXX)
WHATSAPP_ALERT_TO=59899XXXXXX
# Link del dashboard que se manda en el mensaje
PUBLIC_BASE_URL=https://dynamiclabsai.com
# Ventana de "nuevas"
DIGEST_WINDOW_HOURS=24
```

> WhatsApp Business API (`WHATSAPP_PHONE_ID` / `WHATSAPP_TOKEN`) ya está en tu `.env`.
> Solo falta `WHATSAPP_ALERT_TO` (a quién enviar).

## Activación (una sola vez)

1. Completá `WHATSAPP_ALERT_TO` en `.env`.
2. Redeploy del backend (para servir `/nuevas` y cargar el nuevo Celery include).
3. Reiniciá **celery worker** y **celery beat** para tomar el nuevo schedule.
4. Probar a mano sin esperar a las 7am:
   ```bash
   celery -A app.workers.celery_app call app.workers.tasks.notify.daily_new_digest
   ```
   o abrir directamente `https://dynamiclabsai.com/nuevas`.

## Notas

- Si `WHATSAPP_ALERT_TO` está vacío, la tarea no envía y loguea el mensaje que
  habría mandado (modo seguro).
- El dashboard no genera archivos: siempre refleja el estado actual de la API.
