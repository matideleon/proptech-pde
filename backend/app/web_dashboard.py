"""
Dashboard público de NUEVAS propiedades.

Sirve una página HTML autocontenida en `/nuevas` que consume la API pública
(`/api/v1/properties`) del lado del cliente y muestra las propiedades dadas de
alta en las últimas N horas (por defecto 24, configurable con `?h=`).

Es una URL permanente y siempre viva: no genera archivos ni depende del frontend
Next.js. Se incluye en `app/main.py` sin prefijo.
"""
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

_PAGE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Nuevas propiedades · Punta del Este</title>
<style>
  :root{--bg:#0b0f17;--panel:#121826;--panel2:#1a2335;--line:#233047;
    --txt:#e7ecf5;--muted:#8b9bb4;--accent:#38bdf8;--accent2:#22c55e;}
  *{box-sizing:border-box;}
  body{margin:0;background:radial-gradient(1200px 600px at 80% -10%,#16233b 0%,var(--bg) 55%);
    color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
    -webkit-font-smoothing:antialiased;min-height:100vh;}
  .wrap{max-width:1180px;margin:0 auto;padding:40px 24px 80px;}
  header.top{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;
    flex-wrap:wrap;margin-bottom:24px;}
  .brand{font-size:13px;letter-spacing:3px;text-transform:uppercase;color:var(--accent);font-weight:700;}
  h1{margin:6px 0 4px;font-size:34px;letter-spacing:-.5px;}
  .sub{color:var(--muted);font-size:14px;}
  .hero-count{text-align:right;}
  .hero-count .big{font-size:56px;font-weight:800;line-height:1;
    background:linear-gradient(135deg,#38bdf8,#22c55e);-webkit-background-clip:text;
    background-clip:text;color:transparent;}
  .hero-count .lbl{color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:1.5px;}
  .toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:22px;align-items:center;}
  .toolbar select,.toolbar button{background:var(--panel2);color:var(--txt);border:1px solid var(--line);
    border-radius:10px;padding:8px 12px;font-size:13px;cursor:pointer;}
  .metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:26px;}
  .metric{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px 18px;}
  .metric .k{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;}
  .chip{display:inline-block;background:var(--panel2);border:1px solid var(--line);color:var(--txt);
    border-radius:999px;padding:5px 11px;font-size:13px;margin:3px 4px 0 0;}
  .chip b{color:var(--accent);}
  .metric .val{font-size:22px;font-weight:700;}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:18px;}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:18px;overflow:hidden;
    text-decoration:none;color:inherit;display:flex;flex-direction:column;
    transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease;}
  .card:hover{transform:translateY(-4px);border-color:var(--accent);
    box-shadow:0 18px 40px -18px rgba(56,189,248,.5);}
  .thumb{height:170px;background-size:cover;background-position:center;background-color:var(--panel2);}
  .card-body{padding:14px 16px 16px;display:flex;flex-direction:column;gap:6px;}
  .row-top{display:flex;justify-content:space-between;align-items:center;gap:8px;}
  .badge-op{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);font-weight:600;}
  .badge-src{font-size:11px;font-weight:700;color:var(--accent2);border:1px solid var(--accent2);
    padding:2px 8px;border-radius:999px;}
  .price{font-size:23px;font-weight:800;letter-spacing:-.3px;}
  .ptype{color:var(--muted);font-size:12.5px;}
  .title{font-size:14px;font-weight:600;line-height:1.35;max-height:2.7em;overflow:hidden;margin-top:2px;}
  .loc{color:var(--muted);font-size:12.5px;}
  .specs{display:flex;gap:10px;flex-wrap:wrap;margin-top:4px;}
  .spec{font-size:12.5px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:3px 8px;}
  .state{grid-column:1/-1;text-align:center;color:var(--muted);padding:80px 0;font-size:16px;}
  footer{margin-top:50px;color:var(--muted);font-size:12.5px;text-align:center;border-top:1px solid var(--line);padding-top:22px;}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <div class="brand">PropTech PDE · Punta del Este</div>
      <h1>Nuevas propiedades</h1>
      <div class="sub" id="sub">Cargando…</div>
    </div>
    <div class="hero-count"><div class="big" id="count">—</div><div class="lbl">nuevas</div></div>
  </header>

  <div class="toolbar">
    <label style="color:var(--muted);font-size:13px;">Ventana:</label>
    <select id="hsel">
      <option value="24">Últimas 24 h</option>
      <option value="48">Últimas 48 h</option>
      <option value="72">Últimas 72 h</option>
      <option value="168">Últimos 7 días</option>
    </select>
    <button id="reload">↻ Actualizar</button>
  </div>

  <section class="metrics" id="metrics"></section>
  <section class="grid" id="grid"><div class="state">Cargando…</div></section>
  <footer>PropTech PDE — Inteligencia inmobiliaria de Punta del Este</footer>
</div>

<script>
const fmtUSD = v => v==null||isNaN(v) ? "—" : "U$S " + Math.round(v).toLocaleString("es-UY");
const esc = s => (s==null?"":String(s)).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function hoursParam(){ const u=new URL(location.href); return parseInt(u.searchParams.get('h')||document.getElementById('hsel').value||'24',10); }

async function fetchAll(){
  let items=[], page=1;
  while(page<=10){
    const r = await fetch(`/api/v1/properties?sort_by=created_at&sort_order=desc&page_size=80&page=${page}`);
    if(!r.ok) break;
    const j = await r.json();
    items = items.concat(j.items||[]);
    if(!j.pages || page>=j.pages) break;
    page++;
  }
  return items;
}

function render(items, hours){
  const cutoff = Date.now() - hours*3600*1000;
  const news = items.filter(p=>{
    const t = Date.parse(p.created_at || p.first_seen_at || "");
    return !isNaN(t) && t >= cutoff;
  }).sort((a,b)=>Date.parse(b.created_at)-Date.parse(a.created_at));

  document.getElementById('count').textContent = news.length;
  document.getElementById('sub').textContent =
    `Detectadas en las últimas ${hours} h · actualizado ${new Date().toLocaleString("es-UY",{timeZone:"America/Montevideo"})}`;

  // métricas
  const bySrc={}, byOp={}, byZone={}, prices=[];
  news.forEach(p=>{
    const s=(p.source||"—"); bySrc[s]=(bySrc[s]||0)+1;
    const o=(p.operation||"—"); byOp[o]=(byOp[o]||0)+1;
    const z=(p.neighborhood||p.city||"—"); byZone[z]=(byZone[z]||0)+1;
    const pr=parseFloat(p.price_usd||p.price); if(!isNaN(pr)) prices.push(pr);
  });
  const chips=o=>Object.entries(o).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<span class="chip"><b>${v}</b> ${esc(k)}</span>`).join("");
  const zoneTop=Object.entries(byZone).sort((a,b)=>b[1]-a[1]).slice(0,6);
  const range = prices.length ? `${fmtUSD(Math.min(...prices))} – ${fmtUSD(Math.max(...prices))}` : "—";
  document.getElementById('metrics').innerHTML =
    `<div class="metric"><div class="k">Por fuente</div><div>${chips(bySrc)||'—'}</div></div>
     <div class="metric"><div class="k">Por operación</div><div>${chips(byOp)||'—'}</div></div>
     <div class="metric"><div class="k">Rango de precios</div><div class="val">${range}</div></div>
     <div class="metric"><div class="k">Zonas con más altas</div><div>${zoneTop.map(([k,v])=>`<span class="chip"><b>${v}</b> ${esc(k)}</span>`).join("")||'—'}</div></div>`;

  const grid=document.getElementById('grid');
  if(!news.length){ grid.innerHTML='<div class="state">No hay propiedades nuevas en este período. 🌙</div>'; return; }
  grid.innerHTML = news.map(p=>{
    const img=p.main_image_url?`<div class="thumb" style="background-image:url('${esc(p.main_image_url)}')"></div>`:'<div class="thumb"></div>';
    const ppm2=parseFloat(p.price_per_m2_usd);
    const ppm2s=!isNaN(ppm2)?` · ${fmtUSD(ppm2)}/m²`:'';
    const specs=[p.bedrooms!=null?`🛏 ${p.bedrooms}`:'',p.bathrooms!=null?`🛁 ${p.bathrooms}`:'',
      p.area_total?`📐 ${Math.round(parseFloat(p.area_total))} m²`:''].filter(Boolean)
      .map(s=>`<span class="spec">${s}</span>`).join("");
    return `<a class="card" href="${esc(p.url||'#')}" target="_blank" rel="noopener">${img}
      <div class="card-body">
        <div class="row-top"><span class="badge-op">${esc(p.operation||'')}</span>
          <span class="badge-src">${esc(p.source||'')}</span></div>
        <div class="price">${fmtUSD(parseFloat(p.price_usd||p.price))}</div>
        <div class="ptype">${esc((p.property_type||'').replace(/^./,c=>c.toUpperCase()))}${ppm2s}</div>
        <div class="title">${esc(p.title||'Sin título')}</div>
        <div class="loc">📍 ${esc(p.neighborhood||p.city||'')}</div>
        <div class="specs">${specs}</div>
      </div></a>`;
  }).join("");
}

async function load(){
  const grid=document.getElementById('grid');
  grid.innerHTML='<div class="state">Cargando…</div>';
  try{ const items=await fetchAll(); render(items, hoursParam()); }
  catch(e){ grid.innerHTML='<div class="state">No se pudo cargar la API. Reintentá en unos segundos.</div>'; }
}
document.getElementById('reload').addEventListener('click', load);
document.getElementById('hsel').addEventListener('change', load);
(function(){ const h=new URL(location.href).searchParams.get('h'); if(h) document.getElementById('hsel').value=h; })();
load();
</script>
</body>
</html>"""


@router.get("/nuevas", response_class=HTMLResponse, include_in_schema=False)
async def nuevas_dashboard(h: int = Query(24, ge=1, le=720)):
    """Dashboard público de nuevas propiedades (últimas `h` horas)."""
    return HTMLResponse(content=_PAGE)
