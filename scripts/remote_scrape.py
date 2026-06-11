#!/usr/bin/env python3
"""
Runner remoto de scrapers — para GitHub Actions o ejecución local.

Corre los scrapers localmente (donde el IP no está bloqueado) y empuja
los resultados al API de producción via POST /api/v1/scraping/push-batch.

Uso:
    python scripts/remote_scrape.py
    python scripts/remote_scrape.py --sources facebook gallito
    python scripts/remote_scrape.py --dry-run

Variables de entorno requeridas:
    PROD_URL      URL base del API (ej: https://dynamiclabsai.com)
    ADMIN_EMAIL   email admin (default: admin@proptech.uy)
    ADMIN_PASS    contraseña admin
"""
import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

import aiohttp

# Asegurar que el módulo backend está en el path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)


PROD_URL = os.environ.get("PROD_URL", "https://dynamiclabsai.com").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@proptech.uy")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "")

ALL_SOURCES = ["mercadolibre", "infocasas", "facebook", "gallito"]
# En GH Actions corremos solo los que fallan en VPS por IP bloqueada
REMOTE_ONLY_SOURCES = ["facebook", "gallito"]


def _serializable(obj):
    """Convierte datetimes y sets a tipos JSON-serializables."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def get_token(session: aiohttp.ClientSession) -> str:
    url = f"{PROD_URL}/api/v1/auth/login"
    async with session.post(url, json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}) as r:
        if r.status != 200:
            text = await r.text()
            raise RuntimeError(f"Login failed ({r.status}): {text[:200]}")
        data = await r.json()
        return data["access_token"]


async def push_properties(
    session: aiohttp.ClientSession,
    token: str,
    properties: list,
    dry_run: bool = False,
) -> dict:
    if dry_run:
        print(f"  [dry-run] Would push {len(properties)} properties")
        return {"received": len(properties), "new": 0, "updated": 0, "skipped": 0, "errors": 0}

    url = f"{PROD_URL}/api/v1/scraping/push-batch"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"properties": properties}

    async with session.post(url, json=payload, headers=headers) as r:
        if r.status != 200:
            text = await r.text()
            raise RuntimeError(f"push-batch failed ({r.status}): {text[:400]}")
        return await r.json()


async def run_scrapers(sources: List[str]) -> List[dict]:
    """Ejecuta scrapers localmente y retorna lista de propiedades serializadas."""
    from app.scrapers.facebook import FacebookMarketplaceScraper
    from app.scrapers.gallito import GallitoScraper
    from app.scrapers.infocasas import InfoCasasScraper
    from app.scrapers.mercadolibre import MercadoLibreWebScraper

    SCRAPER_MAP = {
        "mercadolibre": MercadoLibreWebScraper,
        "infocasas": InfoCasasScraper,
        "facebook": FacebookMarketplaceScraper,
        "gallito": GallitoScraper,
    }

    all_props = []

    for source in sources:
        cls = SCRAPER_MAP.get(source)
        if not cls:
            print(f"  [warn] Unknown source: {source}")
            continue

        print(f"\n→ Scraping {source}...")
        scraper = cls()
        count = 0
        try:
            async for prop in scraper.scrape():
                d = asdict(prop)
                # Serializar campos no-JSON
                d = json.loads(json.dumps(d, default=_serializable))
                all_props.append(d)
                count += 1
        except Exception as e:
            print(f"  [error] {source} failed: {e}")
        finally:
            await scraper.close()
        print(f"  {source}: {count} properties scraped")

    return all_props


async def main(sources: List[str], dry_run: bool):
    if not ADMIN_PASS and not dry_run:
        print("ERROR: ADMIN_PASS env var is required")
        sys.exit(1)

    print(f"Remote scraper — target: {PROD_URL}")
    print(f"Sources: {sources}")
    if dry_run:
        print("Mode: DRY RUN (no data pushed)")

    properties = await run_scrapers(sources)
    print(f"\nTotal scraped: {len(properties)} properties")

    if not properties:
        print("Nothing to push.")
        return

    # Push in batches of 200 to avoid huge payloads
    BATCH_SIZE = 200
    totals = {"received": 0, "new": 0, "updated": 0, "skipped": 0, "errors": 0}

    async with aiohttp.ClientSession() as session:
        token = "" if dry_run else await get_token(session)
        if not dry_run:
            print("Authenticated with prod API")

        for i in range(0, len(properties), BATCH_SIZE):
            batch = properties[i : i + BATCH_SIZE]
            print(f"\nPushing batch {i // BATCH_SIZE + 1} ({len(batch)} props)...")
            result = await push_properties(session, token, batch, dry_run=dry_run)
            for k in totals:
                totals[k] += result.get(k, 0)

    print(f"\n{'='*50}")
    print(f"Push summary:")
    print(f"  Received : {totals['received']}")
    print(f"  New      : {totals['new']}")
    print(f"  Updated  : {totals['updated']}")
    print(f"  Skipped  : {totals['skipped']} (out of price range)")
    print(f"  Errors   : {totals['errors']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remote scraper for PropTech PDE")
    parser.add_argument(
        "--sources", nargs="+", default=REMOTE_ONLY_SOURCES,
        help=f"Sources to scrape (default: {REMOTE_ONLY_SOURCES})"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Scrape all sources"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run scrapers but don't push to prod"
    )
    args = parser.parse_args()

    sources = ALL_SOURCES if args.all else args.sources
    asyncio.run(main(sources, dry_run=args.dry_run))
