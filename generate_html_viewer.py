#!/usr/bin/env python3
"""
Generates an interactive HTML species viewer with:
- Map per vegetation type with colored markers
- Photo tooltips on hover over species in the legend
- Standalone file (images embedded as base64)
"""

import os
import sys
import json
import base64

import fitz

sys.path.insert(0, os.path.dirname(__file__))
from api.extraction import (
    SPECIES, extract_positions, extract_shrub_positions,
    extract_ground_cover_areas, assign_colors,
)
from api.species import get_species_database

BASE_DIR = os.path.dirname(__file__)
ARQUIVOS = os.path.join(BASE_DIR, "arquivos")
IMG_DIR = os.path.join(BASE_DIR, "especies_img")
OUTPUT = os.path.join(BASE_DIR, "especies_interativo.html")

TYPE_PDFS = {
    "arvore": os.path.join(ARQUIVOS, "PINI-PSG-PE-0504-LAZ-R00_IA_arvores.pdf"),
    "arbusto": os.path.join(ARQUIVOS, "PINI-PSG-PE-0504-LAZ-R00_IA_arbustos.pdf"),
    "forracao": os.path.join(ARQUIVOS, "PINI-PSG-PE-0504-LAZ-R00_IA_forrações.pdf"),
}
TYPE_LABELS = {"arvore": "Arvores / Palmeiras", "arbusto": "Arbustos", "forracao": "Forracoes"}


def find_image(code):
    for ext in [".png", ".jpeg", ".jpg"]:
        p = os.path.join(IMG_DIR, code + ext)
        if os.path.exists(p):
            return p
    return None


def img_to_base64(path, max_dim=300):
    """Load image, resize, and return base64 data URL."""
    if not path or not os.path.exists(path):
        return ""
    try:
        pix = fitz.Pixmap(path)
        if pix.width > max_dim or pix.height > max_dim:
            scale = max_dim / max(pix.width, pix.height)
            tmp = fitz.open()
            p = tmp.new_page(width=pix.width, height=pix.height)
            p.insert_image(p.rect, pixmap=pix)
            pix = p.get_pixmap(matrix=fitz.Matrix(scale, scale))
            tmp.close()
        # Convert to PNG bytes
        img_bytes = pix.tobytes("jpeg")
        b64 = base64.b64encode(img_bytes).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except:
        return ""


def render_map_base64(pdf_path, dpi=48):
    """Render PDF page to base64 PNG for use as background."""
    doc = fitz.open(pdf_path)
    page = doc[0]
    pw, ph = page.rect.width, page.rect.height
    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("jpeg")
    b64 = base64.b64encode(img_bytes).decode("ascii")
    doc.close()
    return f"data:image/jpeg;base64,{b64}", pw, ph, pix.width, pix.height


def extract_all(species_db):
    all_data = {}
    for ptype, pdf_path in TYPE_PDFS.items():
        if not os.path.exists(pdf_path):
            continue
        doc = fitz.open(pdf_path)
        page = doc[0]
        pw, ph = page.rect.width, page.rect.height

        if ptype == "forracao":
            raw = extract_ground_cover_areas(page)
            color_map = assign_colors(raw, "forracao")
            entries = []
            for label in sorted(raw.keys()):
                info = raw[label]
                codes = label.replace("(", "").replace(")", "").split("+")
                first_code = codes[0].strip().split()[0]
                db = species_db.get(first_code, {})
                # Centroid of all paths for marker position
                all_pts = [p for path in info["paths"] for p in path]
                if all_pts:
                    cx = sum(p[0] for p in all_pts) / len(all_pts)
                    cy = sum(p[1] for p in all_pts) / len(all_pts)
                else:
                    cx, cy = pw / 2, ph / 2
                entries.append({
                    "code": label, "color": color_map[label],
                    "count": len(info["paths"]),
                    "scientific": db.get("scientific_name", ""),
                    "common": db.get("common_name", ""),
                    "origin": db.get("origin", ""),
                    "sun": db.get("sun_exposure", ""),
                    "x": cx / pw * 100, "y": cy / ph * 100,
                    "image_path": find_image(first_code),
                })
            all_data[ptype] = {"entries": entries, "pw": pw, "ph": ph, "pdf": pdf_path}
        elif ptype == "arbusto":
            raw = extract_shrub_positions(page)
            color_map = assign_colors(raw, "arbusto")
            entries = []
            for code in sorted(raw.keys()):
                db = species_db.get(code, {})
                positions = raw[code]
                cx = sum(p["x"] for p in positions) / len(positions) if positions else pw / 2
                cy = sum(p["y"] for p in positions) / len(positions) if positions else ph / 2
                entries.append({
                    "code": code, "color": color_map[code],
                    "count": len(positions),
                    "scientific": db.get("scientific_name", ""),
                    "common": db.get("common_name", ""),
                    "origin": db.get("origin", ""),
                    "sun": db.get("sun_exposure", ""),
                    "x": cx / pw * 100, "y": cy / ph * 100,
                    "image_path": find_image(code),
                })
            all_data[ptype] = {"entries": entries, "pw": pw, "ph": ph, "pdf": pdf_path}
        else:
            raw = extract_positions(page, "arvore")
            color_map = assign_colors(raw, "arvore")
            entries = []
            for code in sorted(raw.keys()):
                db = species_db.get(code, {})
                positions = raw[code]
                cx = sum(p["x"] for p in positions) / len(positions) if positions else pw / 2
                cy = sum(p["y"] for p in positions) / len(positions) if positions else ph / 2
                entries.append({
                    "code": code, "color": color_map[code],
                    "count": len(positions),
                    "scientific": db.get("scientific_name", ""),
                    "common": db.get("common_name", ""),
                    "origin": db.get("origin", ""),
                    "sun": db.get("sun_exposure", ""),
                    "x": cx / pw * 100, "y": cy / ph * 100,
                    "image_path": find_image(code),
                })
            all_data[ptype] = {"entries": entries, "pw": pw, "ph": ph, "pdf": pdf_path}
        doc.close()
    return all_data


def build_html(all_data):
    # Pre-encode all images
    print("   Encoding images...")
    for ptype, tdata in all_data.items():
        for entry in tdata["entries"]:
            entry["img_b64"] = img_to_base64(entry.get("image_path"), max_dim=250)

    # Pre-encode maps
    print("   Encoding maps...")
    maps_b64 = {}
    for ptype, tdata in all_data.items():
        maps_b64[ptype], _, _, img_w, img_h = render_map_base64(tdata["pdf"], dpi=48)
        tdata["img_w"] = img_w
        tdata["img_h"] = img_h

    # Build species data as JSON
    species_json = {}
    for ptype, tdata in all_data.items():
        species_json[ptype] = {
            "label": TYPE_LABELS.get(ptype, ptype),
            "map": maps_b64[ptype],
            "img_w": tdata["img_w"],
            "img_h": tdata["img_h"],
            "pw": tdata["pw"],
            "ph": tdata["ph"],
            "entries": [{
                "code": e["code"],
                "color": e["color"],
                "count": e["count"],
                "scientific": e["scientific"],
                "common": e["common"],
                "origin": e["origin"],
                "sun": e["sun"],
                "x": round(e["x"], 2),
                "y": round(e["y"], 2),
                "img": e["img_b64"],
            } for e in tdata["entries"]],
        }

    total_species = sum(len(d["entries"]) for d in species_json.values())
    total_items = sum(sum(e["count"] for e in d["entries"]) for d in species_json.values())

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Legenda de Especies - Interativo</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f5f5f5;color:#222}}
.header{{background:#1a1d21;color:#fff;padding:24px 32px;display:flex;justify-content:space-between;align-items:center}}
.header h1{{font-size:18px;font-weight:600;letter-spacing:1px}}
.header .stats{{display:flex;gap:24px}}
.header .stat{{text-align:center}}
.header .stat .num{{font-size:24px;font-weight:700;color:#4CAF50}}
.header .stat .lbl{{font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px}}
.tabs{{display:flex;background:#242830;border-bottom:2px solid #4CAF50}}
.tab{{padding:12px 28px;cursor:pointer;color:#888;font-size:13px;font-weight:600;letter-spacing:0.5px;
      border-bottom:3px solid transparent;transition:all .15s}}
.tab:hover{{color:#ccc}}
.tab.active{{color:#4CAF50;border-bottom-color:#4CAF50;background:#1a1d21}}
.content{{display:flex;height:calc(100vh - 130px)}}
.map-panel{{flex:1;position:relative;overflow:hidden;background:#fff}}
.map-panel img{{width:100%;height:100%;object-fit:contain}}
.map-marker{{position:absolute;width:12px;height:12px;border-radius:50%;border:2px solid #fff;
             cursor:pointer;transform:translate(-50%,-50%);transition:all .15s;z-index:2;
             box-shadow:0 1px 4px rgba(0,0,0,.3)}}
.map-marker:hover{{transform:translate(-50%,-50%) scale(1.8);z-index:10}}
.map-marker.highlight{{transform:translate(-50%,-50%) scale(2);z-index:10;
                       box-shadow:0 0 0 4px rgba(76,175,80,.4)}}
.legend-panel{{width:360px;overflow-y:auto;background:#fff;border-left:1px solid #e0e0e0;padding:0}}
.legend-title{{padding:16px 20px 8px;font-size:11px;font-weight:700;color:#888;
               letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid #eee}}
.species-row{{display:flex;align-items:center;gap:10px;padding:10px 20px;cursor:pointer;
              border-bottom:1px solid #f5f5f5;transition:background .1s;position:relative}}
.species-row:hover{{background:#f0faf0}}
.species-row.active{{background:#e8f5e9}}
.sp-dot{{width:14px;height:14px;border-radius:50%;flex-shrink:0}}
.sp-info{{flex:1;min-width:0}}
.sp-code{{font-weight:700;font-size:13px}}
.sp-name{{font-size:11px;color:#666;font-style:italic;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.sp-meta{{font-size:10px;color:#999}}
.sp-count{{font-size:11px;color:#fff;padding:2px 8px;border-radius:10px;font-weight:600;flex-shrink:0}}
/* Tooltip */
.tooltip{{position:fixed;z-index:1000;pointer-events:none;opacity:0;transition:opacity .15s;
          background:#fff;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.2);
          border:1px solid #e0e0e0;overflow:hidden;max-width:280px}}
.tooltip.show{{opacity:1}}
.tooltip img{{display:block;width:260px;height:auto;max-height:200px;object-fit:cover}}
.tooltip .tt-info{{padding:10px 14px}}
.tooltip .tt-code{{font-weight:700;font-size:14px}}
.tooltip .tt-sci{{font-style:italic;font-size:12px;color:#555;margin-top:2px}}
.tooltip .tt-common{{font-size:11px;color:#888;margin-top:2px}}
.tooltip .tt-meta{{font-size:10px;color:#aaa;margin-top:4px}}
.tooltip .tt-noimg{{width:260px;height:120px;background:#f5f5f5;display:flex;
                    align-items:center;justify-content:center;color:#ccc;font-size:13px}}
.panel-hidden{{display:none}}
</style>
</head>
<body>
<div class="header">
  <h1>LEGENDA DE ESPECIES</h1>
  <div class="stats">
    <div class="stat"><div class="num">{total_species}</div><div class="lbl">Especies</div></div>
    <div class="stat"><div class="num">{total_items}</div><div class="lbl">Itens</div></div>
    <div class="stat"><div class="num">{len(species_json)}</div><div class="lbl">Categorias</div></div>
  </div>
</div>
<div class="tabs" id="tabs"></div>
<div class="content">
  <div class="map-panel" id="mapPanel"></div>
  <div class="legend-panel" id="legendPanel"></div>
</div>
<div class="tooltip" id="tooltip"></div>

<script>
const DATA = {json.dumps(species_json, ensure_ascii=False)};

const tabs = document.getElementById('tabs');
const mapPanel = document.getElementById('mapPanel');
const legendPanel = document.getElementById('legendPanel');
const tooltip = document.getElementById('tooltip');
let activeType = null;
let activeCode = null;

// Build tabs
Object.keys(DATA).forEach((type, i) => {{
  const d = DATA[type];
  const tab = document.createElement('div');
  tab.className = 'tab' + (i === 0 ? ' active' : '');
  tab.textContent = d.label + ' (' + d.entries.length + ')';
  tab.onclick = () => showType(type);
  tabs.appendChild(tab);
}});

function showType(type) {{
  activeType = type;
  activeCode = null;
  document.querySelectorAll('.tab').forEach((t, i) => {{
    t.classList.toggle('active', Object.keys(DATA)[i] === type);
  }});
  renderMap(type);
  renderLegend(type);
}}

function renderMap(type) {{
  const d = DATA[type];
  mapPanel.innerHTML = '<img src="' + d.map + '" id="mapImg">';
  // Add markers
  d.entries.forEach(e => {{
    const m = document.createElement('div');
    m.className = 'map-marker';
    m.style.left = e.x + '%';
    m.style.top = e.y + '%';
    m.style.background = e.color;
    m.dataset.code = e.code;
    m.onmouseenter = (ev) => {{ highlightSpecies(e.code); showTooltip(ev, e); }};
    m.onmouseleave = () => {{ unhighlightSpecies(); hideTooltip(); }};
    m.onclick = () => scrollToSpecies(e.code);
    mapPanel.appendChild(m);
  }});
}}

function renderLegend(type) {{
  const d = DATA[type];
  legendPanel.innerHTML = '<div class="legend-title">' + d.label + ' - ' + d.entries.length + ' especies</div>';
  d.entries.forEach(e => {{
    const row = document.createElement('div');
    row.className = 'species-row';
    row.id = 'row-' + e.code.replace(/[^a-zA-Z0-9]/g, '_');
    row.innerHTML = `
      <div class="sp-dot" style="background:${{e.color}}"></div>
      <div class="sp-info">
        <div class="sp-code">${{e.code}}</div>
        <div class="sp-name">${{e.scientific || ''}}</div>
        <div class="sp-meta">${{e.common || ''}}</div>
      </div>
      <div class="sp-count" style="background:${{e.color}}">${{e.count}}</div>
    `;
    row.onmouseenter = (ev) => {{ highlightSpecies(e.code); showTooltip(ev, e); }};
    row.onmouseleave = () => {{ unhighlightSpecies(); hideTooltip(); }};
    legendPanel.appendChild(row);
  }});
}}

function highlightSpecies(code) {{
  activeCode = code;
  document.querySelectorAll('.map-marker').forEach(m => {{
    m.classList.toggle('highlight', m.dataset.code === code);
    m.style.opacity = m.dataset.code === code ? '1' : '0.3';
  }});
  document.querySelectorAll('.species-row').forEach(r => {{
    const rCode = r.id.replace('row-', '').replace(/_/g, ' ');
    r.classList.toggle('active', r.id === 'row-' + code.replace(/[^a-zA-Z0-9]/g, '_'));
  }});
}}

function unhighlightSpecies() {{
  activeCode = null;
  document.querySelectorAll('.map-marker').forEach(m => {{
    m.classList.remove('highlight');
    m.style.opacity = '1';
  }});
  document.querySelectorAll('.species-row').forEach(r => r.classList.remove('active'));
}}

function showTooltip(ev, entry) {{
  let html = '';
  if (entry.img) {{
    html += '<img src="' + entry.img + '">';
  }} else {{
    html += '<div class="tt-noimg">sem foto</div>';
  }}
  html += '<div class="tt-info">';
  html += '<div class="tt-code">' + entry.code + '</div>';
  if (entry.scientific) html += '<div class="tt-sci">' + entry.scientific + '</div>';
  if (entry.common) html += '<div class="tt-common">' + entry.common + '</div>';
  const meta = [entry.origin, entry.sun].filter(Boolean).join(' | ');
  if (meta) html += '<div class="tt-meta">' + meta + ' | ' + entry.count + ' un.</div>';
  else html += '<div class="tt-meta">' + entry.count + ' un.</div>';
  html += '</div>';
  tooltip.innerHTML = html;
  tooltip.classList.add('show');
  positionTooltip(ev);
}}

function positionTooltip(ev) {{
  const tt = tooltip;
  const x = ev.clientX + 16;
  const y = ev.clientY - 10;
  const maxX = window.innerWidth - tt.offsetWidth - 10;
  const maxY = window.innerHeight - tt.offsetHeight - 10;
  tt.style.left = Math.min(x, maxX) + 'px';
  tt.style.top = Math.min(y, maxY) + 'px';
}}

document.addEventListener('mousemove', (ev) => {{
  if (tooltip.classList.contains('show')) positionTooltip(ev);
}});

function hideTooltip() {{
  tooltip.classList.remove('show');
}}

function scrollToSpecies(code) {{
  const id = 'row-' + code.replace(/[^a-zA-Z0-9]/g, '_');
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
}}

// Init
showType(Object.keys(DATA)[0]);
</script>
</body>
</html>"""
    return html


def main():
    print("=== Gerando HTML Interativo ===\n")

    print("1. Carregando banco de especies...")
    species_db = get_species_database()
    print(f"   {len(species_db)} especies\n")

    print("2. Extraindo dados...")
    all_data = extract_all(species_db)
    for ptype, tdata in all_data.items():
        print(f"   {ptype}: {len(tdata['entries'])} especies")

    print("\n3. Gerando HTML...")
    html = build_html(all_data)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"\n=== HTML gerado: {OUTPUT} ({size_kb:.0f} KB) ===")


if __name__ == "__main__":
    main()
