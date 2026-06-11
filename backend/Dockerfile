FROM python:3.11-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright system deps
RUN pip install playwright && playwright install-deps chromium

WORKDIR /app

# ─── DEPENDENCIES ───────────────────────────────────────────
FROM base AS dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── DEVELOPMENT ────────────────────────────────────────────
FROM dependencies AS development
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Install playwright browsers
RUN playwright install chromium

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─── PRODUCTION ─────────────────────────────────────────────
FROM dependencies AS production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
# Ruta compartida de los navegadores: se instalan como root acá y el usuario
# de runtime (appuser) los lee desde la misma ubicación.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN playwright install chromium && chmod -R a+rx /ms-playwright

COPY . .
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]

# Force rebuild: 2026-06-09
