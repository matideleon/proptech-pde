# Activación de scrapers: MercadoLibre y Facebook Marketplace

Ambos portales **requieren autenticación**. El código de los scrapers ya está
implementado y listo; solo falta proveer credenciales. Resumen del diagnóstico
(verificado en vivo):

| Portal | Acceso anónimo | Qué necesita |
|---|---|---|
| InfoCasas | ✅ Funciona | Nada — ya operativo (19+ propiedades reales) |
| MercadoLibre | ❌ HTTP 403 / `account-verification` | Token OAuth |
| Facebook Marketplace | ❌ Muro de login | Sesión iniciada |

---

## 🟡 MercadoLibre — Token OAuth (10 minutos)

La API pública de ML dejó de permitir acceso anónimo en 2024 (devuelve 403).
La forma correcta y estable de scrapear ML es su **API oficial con OAuth**, que
es **gratuita** para desarrolladores.

### Pasos
1. Entrá a https://developers.mercadolibre.com.uy e iniciá sesión con tu cuenta.
2. **Crear aplicación** → completá nombre, descripción y redirect URI.
3. Copiá el **Client ID** y **Client Secret**.
4. Generá un **access_token** (válido 6 h, se renueva con el refresh_token).
5. Pegalo en el `.env`:
   ```
   MERCADOLIBRE_ACCESS_TOKEN=APP_USR-xxxxxxxx...
   ```
6. Corré el scraper:
   ```bash
   make scrape-ml
   ```

El scraper ya envía el token automáticamente en `search`, `items/{id}` e
`items/{id}/description`. El filtro de alquiler USD 400–2.000 se aplica igual.

> **Nota**: para producción conviene implementar el refresh automático del token
> (el endpoint `/oauth/token` con `grant_type=refresh_token`). El campo está
> previsto en la config.

---

## 🔴 Facebook Marketplace — Sesión iniciada (complejo)

Facebook Marketplace **no permite scraping anónimo**: redirige a login y aplica
anti-bot agresivo (detección de automatización, rate-limits, challenges).

### Limitaciones importantes
- Requiere una **cuenta de Facebook logueada** (cookies/sesión).
- Scrapear FB puede **violar sus Términos de Servicio** — usar con criterio
  legal y preferentemente datos públicos.
- Necesita **Playwright con navegador real** (no requests HTTP).

### Cómo activarlo (si decidís hacerlo)
1. Generá un `storage_state` de Playwright con una sesión válida:
   ```python
   # login_facebook.py — ejecutar UNA vez, a mano
   from playwright.sync_api import sync_playwright
   with sync_playwright() as p:
       b = p.chromium.launch(headless=False)   # ventana visible
       pg = b.new_page()
       pg.goto("https://www.facebook.com/login")
       input("Logueate manualmente y presioná Enter...")  # vos te logueás
       pg.context.storage_state(path="facebook_session.json")
       b.close()
   ```
2. Configurá en `.env`:
   ```
   FACEBOOK_SESSION_FILE=./facebook_session.json
   ```
3. El scraper (`app/scrapers/playwright_helper.py`) cargará esa sesión.

> ⚠️ **El login debe hacerlo una persona** (no se automatiza el ingreso de
> credenciales por seguridad). Una vez generado el `storage_state`, el scraper
> reutiliza la sesión hasta que expire.

---

## ✅ Recomendación del CTO

1. **Inmediato**: MercadoLibre con token OAuth — es gratis, estable y legal.
   Es el de mayor volumen de inventario en Uruguay.
2. **InfoCasas** ya está trayendo datos reales; ampliar a más zonas
   (José Ignacio, La Barra, Piriápolis) es trivial.
3. **Facebook Marketplace**: dejarlo para una fase posterior por su fragilidad
   legal y técnica. El código está listo para cuando se provea una sesión.
