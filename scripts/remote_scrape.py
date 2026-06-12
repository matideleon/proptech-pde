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


async def run_group_scraper() -> List[dict]:
    """
    Ejecuta el scraper de grupos de Facebook (Playwright + sesión FB) y devuelve
    los posts clasificados ya serializables. Lee FB_C_USER/FB_XS/FB_GROUP_IDS del
    entorno (vía settings). Distinto a las propiedades: van a otro endpoint.
    """
    from app.scrapers.facebook_groups import FacebookGroupScraper

    print("\n→ Scraping facebook_groups (Playwright + sesión FB)...")
    scraper = FacebookGroupScraper()
    if not scraper.session_cookie:
        print("  [error] Sin cookie de FB (FB_C_USER/FB_XS o FB_SESSION_COOKIE). Saltando grupos.")
        return []
    if not scraper.group_ids:
        print("  [error] FB_GROUP_IDS vacío. Saltando grupos.")
        return []

    posts: List[dict] = []
    try:
        async for post in scraper.scrape():
            posts.append(json.loads(json.dumps(post, default=_serializable)))
    except Exception as e:
        print(f"  [error] facebook_groups failed: {e}")
    finally:
        await scraper.close()
    print(f"  facebook_groups: {len(posts)} posts scraped")
    return posts


async def push_group_posts(
    session: aiohttp.ClientSession,
    token: str,
    posts: list,
    dry_run: bool = False,
) -> dict:
    if dry_run:
        print(f"  [dry-run] Would push {len(posts)} group posts")
        return {"received": len(posts), "new": 0, "skipped": 0}

    url = f"{PROD_URL}/api/v1/group-posts/push-batch"
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(url, json={"posts": posts}, headers=headers) as r:
        if r.status != 200:
            text = await r.text()
            raise RuntimeError(f"group push-batch failed ({r.status}): {text[:400]}")
        return await r.json()


async def main(sources: List[str], dry_run: bool, scrape_groups: bool = False):
    if not ADMIN_PASS and not dry_run:
        print("ERROR: ADMIN_PASS env var is required")
        sys.exit(1)

    print(f"Remote scraper — target: {PROD_URL}")
    print(f"Property sources: {sources or '(none)'}")
    print(f"Scrape FB groups: {scrape_groups}")
    if dry_run:
        print("Mode: DRY RUN (no data pushed)")

    # Scrapear propiedades (si hay fuentes) y posts de grupos (si se pidió).
    properties = await run_scrapers(sources) if sources else []
    group_posts = await run_group_scraper() if scrape_groups else []

    print(f"\nTotal scraped: {len(properties)} properties, {len(group_posts)} group posts")
    if not properties and not group_posts:
        print("Nothing to push.")
        return

    BATCH_SIZE = 200
    prop_totals = {"received": 0, "new": 0, "updated": 0, "skipped": 0, "errors": 0}
    group_totals = {"received": 0, "new": 0, "skipped": 0}

    async with aiohttp.ClientSession() as session:
        token = "" if dry_run else await get_token(session)
        if not dry_run:
            print("Authenticated with prod API")

        # Propiedades → /scraping/push-batch
        for i in range(0, len(properties), BATCH_SIZE):
            batch = properties[i : i + BATCH_SIZE]
            print(f"\nPushing property batch {i // BATCH_SIZE + 1} ({len(batch)})...")
            result = await push_properties(session, token, batch, dry_run=dry_run)
            for k in prop_totals:
                prop_totals[k] += result.get(k, 0)

        # Group posts → /group-posts/push-batch
        for i in range(0, len(group_posts), BATCH_SIZE):
            batch = group_posts[i : i + BATCH_SIZE]
            print(f"\nPushing group-post batch {i // BATCH_SIZE + 1} ({len(batch)})...")
            result = await push_group_posts(session, token, batch, dry_run=dry_run)
            for k in group_totals:
                group_totals[k] += result.get(k, 0)

    print(f"\n{'='*50}")
    if properties:
        print("Properties → new={new} updated={updated} skipped={skipped} errors={errors}".format(**prop_totals))
    if group_posts:
        print("Group posts → new={new} skipped={skipped} (received {received})".format(**group_totals))


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
        "--groups", action="store_true",
        help="Also scrape Facebook groups (Playwright + FB session) → /group-posts/push-batch"
    )
    parser.add_argument(
        "--only-groups", action="store_true",
        help="Scrape ONLY Facebook groups (no property sources)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run scrapers but don't push to prod"
    )
    args = parser.parse_args()

    if args.only_groups:
        sources = []
    elif args.all:
        sources = ALL_SOURCES
    else:
        sources = args.sources
    scrape_groups = args.groups or args.only_groups
    asyncio.run(main(sources, dry_run=args.dry_run, scrape_groups=scrape_groups))
