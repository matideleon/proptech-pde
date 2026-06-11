#!/usr/bin/env python3
"""
daily_new_report.py — Genera un reporte HTML autocontenido con las NUEVAS
propiedades inmobiliarias detectadas en las últimas N horas.

Pensado para correr desde la tarea diaria de Cowork (7:00 America/Montevideo):
  1. El agente trae los datos de la API vía fetch y los guarda en un JSON.
  2. Este script lee ese JSON, filtra las nuevas por `created_at` y renderiza
     un HTML elegante y autocontenido (sin dependencias externas).

Uso:
  python scripts/daily_new_report.py --input data.json --hours 24 \
      --out reports/nuevas_2026-06-11.html

El JSON de entrada puede ser:
  - La respuesta cruda de /api/v1/properties  -> {"items": [...], ...}
  - Una lista de respuestas (varias páginas)  -> [{"items":[...]}, {"items":[...]}]
  - Directamente una lista de propiedades     -> [ {...}, {...} ]
"""
import argparse
import json
import html
from datetime import datetime, timedelta, timezone
from pathlib import Path

MVD = timezone(timedelta(hours=-3))  # America/Montevideo (sin DST)

SOURCE_LABEL = {
    "infocasas": "InfoCasas",
    "mercadolibre": "MercadoLibre",
    "gallito": "Gallito",
    "facebook": "Facebook Marketplace",
}
SOURCE_COLOR = {
    "infocasas": "#22c55e",
    "mercadolibre": "#facc15",
    "gallito": "#38bdf8",
    "facebook": "#818cf8",
}
OP_LABEL = {
    "venta": "Venta",
    "alquiler": "Alquiler",
    "alquiler_temporal": "Alquiler temporal",
}


# ─────────────────────────── helpers ───────────────────────────
def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def load_items(raw):
    """Normaliza cualquier forma de entrada a una lista de propiedades."""
    items = []
    if isinstance(raw, dict):
        items = raw.get("items", [])
    elif isinstance(raw, list):
        for el in raw:
            if isinstance(el, dict) and "items" in el:
                items.extend(el["items"])
            elif isinstance(el, dict):
                items.append(el)
    # dedup por id
    seen, out = set(), []
    for it in items:
        pid = it.get("id") or it.get("url")
        if pid in seen:
            continue
        seen.add(pid)
        out.append(it)
    return out


def fnum(v):
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return None


def money(v, currency="USD"):
    f = fnum(v)
    if f is None:
        return "—"
    sym = "U$S" if currency == "USD" else "$"
    return f"{sym} {f:,.0f}".replace(",", ".")


def esc(v):
    return html.escape(str(v)) if v is not None else ""


# ─────────────────────────── render ───────────────────────────
def card(p):
    src = (p.get("source") or "").lower()
    src_label = SOURCE_LABEL.get(src, src.title() or "—")
    src_color = SOURCE_COLOR.get(src, "#94a3b8")
    op = OP_LABEL.get(p.get("operation"), p.get("operation") or "")
    ptype = (p.get("property_type") or "").title()
    title = esc(p.get("title") or "Sin título")
    neigh = esc(p.get("neighborhood") or p.get("city") or "")
    city = esc(p.get("city") or "")
    url = p.get("url") or "#"
    img = p.get("main_image_url") or ""
    price = money(p.get("price_usd") or p.get("price"), p.get("currency") or "USD")
    ppm2 = fnum(p.get("price_per_m2_usd"))
    ppm2_s = f"U$S {ppm2:,.0f}/m²".replace(",", ".") if ppm2 else ""
    beds = p.get("bedrooms")
    baths = p.get("bathrooms")
    area = fnum(p.get("area_total"))
    area_s = f"{area:,.0f} m²".replace(",", ".") if area else ""

    specs = []
    if beds is not None:
        specs.append(f'<span class="spec">🛏 {esc(beds)}</span>')
    if baths is not None:
        specs.append(f'<span class="spec">🛁 {esc(baths)}</span>')
    if area_s:
        specs.append(f'<span class="spec">📐 {area_s}</span>')
    specs_html = "".join(specs)

    ai_badges = []
    if p.get("ai_premium"):
        ai_badges.append('<span class="ai ai-premium">★ Premium</span>')
    if p.get("ai_opportunity"):
        ai_badges.append('<span class="ai ai-opp">⚡ Oportunidad</span>')
    if p.get("ai_undervalued"):
        ai_badges.append('<span class="ai ai-under">↓ Subvaluada</span>')
    score = fnum(p.get("ai_score"))
    if score is not None:
        ai_badges.append(f'<span class="ai ai-score">IA {score:.0f}</span>')
    ai_html = "".join(ai_badges)

    img_html = (
        f'<div class="thumb" style="background-image:url(\'{esc(img)}\')"></div>'
        if img
        else '<div class="thumb thumb-empty">sin foto</div>'
    )

    return f"""
    <a class="card" href="{esc(url)}" target="_blank" rel="noopener">
      {img_html}
      <div class="card-body">
        <div class="row-top">
          <span class="badge-op">{esc(op)}</span>
          <span class="badge-src" style="--c:{src_color}">{esc(src_label)}</span>
        </div>
        <div class="price">{price}</div>
        <div class="ptype">{esc(ptype)}{(' · ' + ppm2_s) if ppm2_s else ''}</div>
        <div class="title">{title}</div>
        <div class="loc">📍 {neigh}{(' · ' + city) if city and city != neigh else ''}</div>
        <div class="specs">{specs_html}</div>
        <div class="ai-row">{ai_html}</div>
      </div>
    </a>"""


def build_html(new_items, generated_at, hours):
    n = len(new_items)
    # métricas
    by_source = {}
    by_op = {}
    by_zone = {}
    prices = []
    for p in new_items:
        s = SOURCE_LABEL.get((p.get("source") or "").lower(), p.get("source") or "—")
        by_source[s] = by_source.get(s, 0) + 1
        o = OP_LABEL.get(p.get("operation"), p.get("operation") or "—")
        by_op[o] = by_op.get(o, 0) + 1
        z = p.get("neighborhood") or p.get("city") or "—"
        by_zone[z] = by_zone.get(z, 0) + 1
        pr = fnum(p.get("price_usd") or p.get("price"))
        if pr:
            prices.append(pr)

    price_range = "—"
    if prices:
        price_range = f"{money(min(prices))} – {money(max(prices))}"
    top_zones = sorted(by_zone.items(), key=lambda x: -x[1])[:6]

    def chips(d):
        return "".join(
            f'<span class="chip"><b>{v}</b> {esc(k)}</span>'
            for k, v in sorted(d.items(), key=lambda x: -x[1])
        )

    zone_chips = "".join(
        f'<span class="chip"><b>{v}</b> {esc(k)}</span>' for k, v in top_zones
    )

    gen_str = generated_at.astimezone(MVD).strftime("%A %d/%m/%Y · %H:%M")
    cards_html = (
        "".join(card(p) for p in new_items)
        if new_items
        else '<div class="empty">No se detectaron propiedades nuevas en este período. 🌙</div>'
    )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nuevas propiedades · Punta del Este</title>
<style>
  :root {{
    --bg:#0b0f17; --panel:#121826; --panel2:#1a2335; --line:#233047;
    --txt:#e7ecf5; --muted:#8b9bb4; --accent:#38bdf8; --accent2:#22c55e;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; background:radial-gradient(1200px 600px at 80% -10%, #16233b 0%, var(--bg) 55%);
    color:var(--txt); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
    -webkit-font-smoothing:antialiased;
  }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:40px 24px 80px; }}
  header.top {{ display:flex; justify-content:space-between; align-items:flex-end;
    gap:24px; flex-wrap:wrap; margin-bottom:28px; }}
  .brand {{ font-size:13px; letter-spacing:3px; text-transform:uppercase; color:var(--accent);
    font-weight:700; }}
  h1 {{ margin:6px 0 4px; font-size:34px; letter-spacing:-.5px; }}
  .sub {{ color:var(--muted); font-size:14px; }}
  .hero-count {{ text-align:right; }}
  .hero-count .big {{ font-size:56px; font-weight:800; line-height:1;
    background:linear-gradient(135deg,#38bdf8,#22c55e); -webkit-background-clip:text;
    background-clip:text; color:transparent; }}
  .hero-count .lbl {{ color:var(--muted); font-size:13px; text-transform:uppercase;
    letter-spacing:1.5px; }}

  .metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:14px; margin-bottom:28px; }}
  .metric {{ background:var(--panel); border:1px solid var(--line); border-radius:16px;
    padding:18px 20px; }}
  .metric .k {{ color:var(--muted); font-size:12px; text-transform:uppercase;
    letter-spacing:1px; margin-bottom:10px; }}
  .chip {{ display:inline-block; background:var(--panel2); border:1px solid var(--line);
    color:var(--txt); border-radius:999px; padding:5px 11px; font-size:13px; margin:3px 4px 0 0; }}
  .chip b {{ color:var(--accent); }}
  .metric .val {{ font-size:22px; font-weight:700; }}

  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(270px,1fr)); gap:18px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:18px;
    overflow:hidden; text-decoration:none; color:inherit; display:flex; flex-direction:column;
    transition:transform .15s ease, border-color .15s ease, box-shadow .15s ease; }}
  .card:hover {{ transform:translateY(-4px); border-color:var(--accent);
    box-shadow:0 18px 40px -18px rgba(56,189,248,.5); }}
  .thumb {{ height:170px; background-size:cover; background-position:center;
    background-color:var(--panel2); }}
  .thumb-empty {{ display:flex; align-items:center; justify-content:center; color:var(--muted);
    font-size:13px; }}
  .card-body {{ padding:14px 16px 16px; display:flex; flex-direction:column; gap:6px; }}
  .row-top {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
  .badge-op {{ font-size:11px; text-transform:uppercase; letter-spacing:.8px; color:var(--muted);
    font-weight:600; }}
  .badge-src {{ font-size:11px; font-weight:700; color:var(--c); border:1px solid var(--c);
    padding:2px 8px; border-radius:999px; }}
  .price {{ font-size:23px; font-weight:800; letter-spacing:-.3px; }}
  .ptype {{ color:var(--muted); font-size:12.5px; }}
  .title {{ font-size:14px; font-weight:600; line-height:1.35; max-height:2.7em; overflow:hidden;
    margin-top:2px; }}
  .loc {{ color:var(--muted); font-size:12.5px; }}
  .specs {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:4px; }}
  .spec {{ font-size:12.5px; color:var(--txt); background:var(--panel2);
    border:1px solid var(--line); border-radius:8px; padding:3px 8px; }}
  .ai-row {{ display:flex; gap:6px; flex-wrap:wrap; margin-top:2px; }}
  .ai {{ font-size:11px; font-weight:700; padding:2px 8px; border-radius:999px; }}
  .ai-premium {{ background:rgba(250,204,21,.15); color:#facc15; }}
  .ai-opp {{ background:rgba(56,189,248,.15); color:#38bdf8; }}
  .ai-under {{ background:rgba(34,197,94,.15); color:#22c55e; }}
  .ai-score {{ background:rgba(129,140,248,.15); color:#a5b4fc; }}
  .empty {{ grid-column:1/-1; text-align:center; color:var(--muted); padding:80px 0;
    font-size:16px; }}
  footer {{ margin-top:50px; color:var(--muted); font-size:12.5px; text-align:center;
    border-top:1px solid var(--line); padding-top:22px; }}
  a.api {{ color:var(--accent); text-decoration:none; }}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <div class="brand">PropTech PDE · Punta del Este</div>
      <h1>Nuevas propiedades</h1>
      <div class="sub">Detectadas en las últimas {hours} h · generado {esc(gen_str)} (Montevideo)</div>
    </div>
    <div class="hero-count">
      <div class="big">{n}</div>
      <div class="lbl">nuevas hoy</div>
    </div>
  </header>

  <section class="metrics">
    <div class="metric"><div class="k">Por fuente</div><div>{chips(by_source)}</div></div>
    <div class="metric"><div class="k">Por operación</div><div>{chips(by_op)}</div></div>
    <div class="metric"><div class="k">Rango de precios</div><div class="val">{price_range}</div></div>
    <div class="metric"><div class="k">Zonas con más altas</div><div>{zone_chips or '—'}</div></div>
  </section>

  <section class="grid">
    {cards_html}
  </section>

  <footer>
    PropTech PDE — Inteligencia inmobiliaria de Punta del Este ·
    Datos vía <a class="api" href="https://dynamiclabsai.com/api/v1/properties">API</a>
  </footer>
</div>
</body>
</html>"""


# ─────────────────────── email (Gmail-safe) ───────────────────────
def email_card(p):
    """Tarjeta optimizada para email: <img> real + estilos inline, tema claro."""
    op = OP_LABEL.get(p.get("operation"), p.get("operation") or "")
    src = (p.get("source") or "").lower()
    src_label = SOURCE_LABEL.get(src, src.title() or "—")
    ptype = (p.get("property_type") or "").title()
    title = esc(p.get("title") or "Sin título")
    neigh = esc(p.get("neighborhood") or p.get("city") or "")
    url = p.get("url") or "#"
    img = p.get("main_image_url") or ""
    price = money(p.get("price_usd") or p.get("price"), p.get("currency") or "USD")
    ppm2 = fnum(p.get("price_per_m2_usd"))
    ppm2_s = f" · U$S {ppm2:,.0f}/m²".replace(",", ".") if ppm2 else ""
    beds = p.get("bedrooms")
    baths = p.get("bathrooms")
    area = fnum(p.get("area_total"))
    bits = []
    if beds is not None:
        bits.append(f"{esc(beds)} dorm")
    if baths is not None:
        bits.append(f"{esc(baths)} baño{'s' if (baths or 0)!=1 else ''}")
    if area:
        bits.append(f"{area:,.0f} m²".replace(",", "."))
    specs = " · ".join(bits)
    img_cell = (
        f'<img src="{esc(img)}" width="150" alt="" '
        f'style="display:block;width:150px;height:115px;object-fit:cover;border-radius:8px;">'
        if img else
        '<div style="width:150px;height:115px;background:#e8edf3;border-radius:8px;"></div>'
    )
    return f"""
    <tr>
      <td style="padding:10px 0;border-bottom:1px solid #eef1f6;">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>
          <td width="150" valign="top">{img_cell}</td>
          <td valign="top" style="padding-left:14px;font-family:Arial,Helvetica,sans-serif;">
            <div style="font-size:11px;color:#8a93a3;text-transform:uppercase;letter-spacing:.5px;">
              {esc(op)} · {esc(src_label)}</div>
            <div style="font-size:20px;font-weight:800;color:#0b1f33;margin:2px 0;">{price}</div>
            <div style="font-size:13px;color:#5a6473;">{esc(ptype)}{ppm2_s}</div>
            <div style="font-size:14px;font-weight:600;color:#16202e;margin:3px 0;">{title}</div>
            <div style="font-size:13px;color:#5a6473;">📍 {neigh}{(' &nbsp;|&nbsp; ' + specs) if specs else ''}</div>
            <div style="margin-top:6px;">
              <a href="{esc(url)}" style="font-size:13px;font-weight:700;color:#0a84ff;text-decoration:none;">
                Ver publicación →</a>
            </div>
          </td>
        </tr></table>
      </td>
    </tr>"""


def build_email_html(new_items, generated_at, hours):
    n = len(new_items)
    by_source, prices = {}, []
    for p in new_items:
        s = SOURCE_LABEL.get((p.get("source") or "").lower(), p.get("source") or "—")
        by_source[s] = by_source.get(s, 0) + 1
        pr = fnum(p.get("price_usd") or p.get("price"))
        if pr:
            prices.append(pr)
    src_txt = ", ".join(f"{v} {k}" for k, v in by_source.items()) or "—"
    price_txt = f"{money(min(prices))} – {money(max(prices))}" if prices else "—"
    gen = generated_at.astimezone(MVD).strftime("%d/%m/%Y %H:%M")
    rows = "".join(email_card(p) for p in new_items) or (
        '<tr><td style="padding:30px;text-align:center;color:#8a93a3;'
        'font-family:Arial,sans-serif;">No hubo propiedades nuevas en este período.</td></tr>'
    )
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:#f4f6fa;padding:24px 0;">
<tr><td align="center">
<table role="presentation" cellpadding="0" cellspacing="0" width="640" style="max-width:640px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e6eaf0;">
  <tr><td style="background:linear-gradient(135deg,#0b1f33,#123a5a);padding:24px 26px;">
    <div style="font-family:Arial,sans-serif;font-size:12px;letter-spacing:2px;color:#7fd1ff;text-transform:uppercase;font-weight:700;">PropTech PDE · Punta del Este</div>
    <div style="font-family:Arial,sans-serif;font-size:26px;font-weight:800;color:#ffffff;margin-top:4px;">{n} propiedades nuevas</div>
    <div style="font-family:Arial,sans-serif;font-size:13px;color:#acc3da;margin-top:2px;">Últimas {hours} h · {esc(gen)} (Montevideo)</div>
  </td></tr>
  <tr><td style="padding:14px 26px;background:#f8fafc;border-bottom:1px solid #eef1f6;font-family:Arial,sans-serif;font-size:13px;color:#5a6473;">
    <b style="color:#0b1f33;">Fuentes:</b> {esc(src_txt)} &nbsp;·&nbsp; <b style="color:#0b1f33;">Precios:</b> {esc(price_txt)}
  </td></tr>
  <tr><td style="padding:6px 26px 18px;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">{rows}</table>
  </td></tr>
  <tr><td style="padding:16px 26px;background:#f8fafc;font-family:Arial,sans-serif;font-size:12px;color:#8a93a3;text-align:center;">
    PropTech PDE — Inteligencia inmobiliaria de Punta del Este
  </td></tr>
</table>
</td></tr>
</table>"""


# ─────────────────────────── main ───────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON con propiedades (API response)")
    ap.add_argument("--hours", type=float, default=24, help="Ventana de 'nuevas' en horas")
    ap.add_argument("--out", required=True, help="Ruta del HTML de salida")
    ap.add_argument("--all", action="store_true",
                    help="No filtrar por fecha; incluir todas las propiedades del input")
    ap.add_argument("--email", action="store_true",
                    help="Genera HTML optimizado para email (Gmail-safe, <img> inline)")
    args = ap.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    items = load_items(raw)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=args.hours)

    if args.all:
        new_items = items
    else:
        new_items = []
        for p in items:
            dt = parse_dt(p.get("created_at")) or parse_dt(p.get("first_seen_at"))
            if dt and dt >= cutoff:
                new_items.append(p)

    # ordenar: más recientes primero, luego por score IA
    new_items.sort(
        key=lambda p: (
            parse_dt(p.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc),
            fnum(p.get("ai_score")) or 0,
        ),
        reverse=True,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    render = build_email_html if args.email else build_html
    out.write_text(render(new_items, now, args.hours), encoding="utf-8")
    print(f"OK · {len(new_items)} nuevas de {len(items)} totales → {out}")


if __name__ == "__main__":
    main()
