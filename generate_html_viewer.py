#!/usr/bin/env python3
"""
Generates an interactive HTML species viewer with SVG overlay markers
and photo tooltips. Standalone file with embedded base64 images.
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


def img_to_base64(path, max_dim=250):
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
        img_bytes = pix.tobytes("jpeg")
        b64 = base64.b64encode(img_bytes).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except:
        return ""


def render_map_base64(pdf_path, dpi=48):
    doc = fitz.open(pdf_path)
    page = doc[0]
    pw, ph = page.rect.width, page.rect.height
    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("jpeg")
    b64 = base64.b64encode(img_bytes).decode("ascii")
    doc.close()
    return f"data:image/jpeg;base64,{b64}", pw, ph


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
                # Collect all points for SVG paths
                all_pts = [p for path in info["paths"] for p in path]
                # Use centroid for legend marker
                cx = sum(p[0] for p in all_pts) / len(all_pts) if all_pts else pw / 2
                cy = sum(p[1] for p in all_pts) / len(all_pts) if all_pts else ph / 2
                # Build SVG path data for all polygons
                svg_paths = []
                for path_pts in info["paths"]:
                    if len(path_pts) >= 3:
                        d = "M " + " L ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in path_pts) + " Z"
                        svg_paths.append(d)
                entries.append({
                    "code": label, "color": color_map[label],
                    "count": len(info["paths"]),
                    "scientific": db.get("scientific_name", ""),
                    "common": db.get("common_name", ""),
                    "origin": db.get("origin", ""),
                    "sun": db.get("sun_exposure", ""),
                    "cx": cx, "cy": cy,
                    "svg_paths": svg_paths,
                    "positions": [],
                    "image_path": find_image(first_code),
                })
            all_data[ptype] = {"entries": entries, "pw": pw, "ph": ph, "pdf": pdf_path}
        else:
            if ptype == "arbusto":
                raw = extract_shrub_positions(page)
            else:
                raw = extract_positions(page, "arvore")
            color_map = assign_colors(raw, ptype if ptype != "arvore" else "arvore")
            entries = []
            for code in sorted(raw.keys()):
                db = species_db.get(code, {})
                positions = raw[code]
                entries.append({
                    "code": code, "color": color_map[code],
                    "count": len(positions),
                    "scientific": db.get("scientific_name", ""),
                    "common": db.get("common_name", ""),
                    "origin": db.get("origin", ""),
                    "sun": db.get("sun_exposure", ""),
                    "cx": 0, "cy": 0,  # not used for circle types
                    "svg_paths": [],
                    "positions": [{"x": p["x"], "y": p["y"]} for p in positions],
                    "image_path": find_image(code),
                })
            all_data[ptype] = {"entries": entries, "pw": pw, "ph": ph, "pdf": pdf_path}
        doc.close()
    return all_data


def build_html(all_data):
    print("   Encoding images...")
    for ptype, tdata in all_data.items():
        for entry in tdata["entries"]:
            entry["img_b64"] = img_to_base64(entry.get("image_path"), max_dim=250)

    print("   Encoding maps...")
    maps_b64 = {}
    for ptype, tdata in all_data.items():
        maps_b64[ptype], _, _ = render_map_base64(tdata["pdf"], dpi=48)

    species_json = {}
    for ptype, tdata in all_data.items():
        species_json[ptype] = {
            "label": TYPE_LABELS.get(ptype, ptype),
            "map": maps_b64[ptype],
            "pw": tdata["pw"],
            "ph": tdata["ph"],
            "type": ptype,
            "entries": [{
                "code": e["code"], "color": e["color"], "count": e["count"],
                "scientific": e["scientific"], "common": e["common"],
                "origin": e["origin"], "sun": e["sun"],
                "img": e["img_b64"],
                "positions": e["positions"],
                "svg_paths": e["svg_paths"],
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
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f5f5f5;color:#222;overflow:hidden;height:100vh}}
.header{{background:#1a1d21;color:#fff;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}}
.header h1{{font-size:16px;font-weight:600;letter-spacing:1px}}
.header .stats{{display:flex;gap:20px}}
.header .stat .num{{font-size:20px;font-weight:700;color:#4CAF50}}
.header .stat .lbl{{font-size:9px;color:#888;text-transform:uppercase;letter-spacing:1px}}
.tabs{{display:flex;background:#242830}}
.tab{{padding:10px 24px;cursor:pointer;color:#888;font-size:12px;font-weight:600;letter-spacing:.5px;
      border-bottom:3px solid transparent;transition:all .15s}}
.tab:hover{{color:#ccc}}
.tab.active{{color:#4CAF50;border-bottom-color:#4CAF50;background:#1a1d21}}
.main{{display:flex;height:calc(100vh - 98px)}}
.map-wrap{{flex:1;position:relative;background:#fff;overflow:hidden}}
.map-wrap img{{display:block;width:100%;height:100%;object-fit:contain}}
.map-wrap svg{{position:absolute;top:0;left:0;width:100%;height:100%}}
.legend{{width:340px;overflow-y:auto;background:#fff;border-left:1px solid #e0e0e0}}
.legend-head{{padding:14px 16px 8px;font-size:10px;font-weight:700;color:#888;
              letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid #eee;
              position:sticky;top:0;background:#fff;z-index:2}}
.sp-row{{display:flex;align-items:center;gap:8px;padding:8px 16px;cursor:pointer;
         border-bottom:1px solid #f5f5f5;transition:background .1s;position:relative}}
.sp-row:hover,.sp-row.active{{background:#e8f5e9}}
.sp-dot{{width:12px;height:12px;border-radius:50%;flex-shrink:0;border:1px solid rgba(0,0,0,.1)}}
.sp-info{{flex:1;min-width:0}}
.sp-code{{font-weight:700;font-size:12px}}
.sp-name{{font-size:10px;color:#666;font-style:italic;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.sp-meta{{font-size:9px;color:#aaa}}
.sp-badge{{font-size:10px;color:#fff;padding:2px 7px;border-radius:10px;font-weight:600;flex-shrink:0}}
.tooltip{{position:fixed;z-index:1000;pointer-events:none;opacity:0;transition:opacity .12s;
          background:#fff;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.25);
          border:1px solid #e0e0e0;overflow:hidden;max-width:280px}}
.tooltip.show{{opacity:1}}
.tooltip img{{display:block;width:260px;height:auto;max-height:200px;object-fit:cover}}
.tooltip .ti{{padding:10px 14px}}
.tooltip .tc{{font-weight:700;font-size:13px}}
.tooltip .ts{{font-style:italic;font-size:11px;color:#555;margin-top:2px}}
.tooltip .tn{{font-size:10px;color:#888;margin-top:2px}}
.tooltip .tm{{font-size:9px;color:#aaa;margin-top:4px}}
.tooltip .noimg{{width:260px;height:80px;background:#f5f5f5;display:flex;
                 align-items:center;justify-content:center;color:#ccc;font-size:12px}}
@media(max-width:900px){{
  body{{overflow:auto;height:auto}}
  .header{{flex-direction:column;gap:6px;text-align:center;padding:12px 16px}}
  .header h1{{font-size:14px}}
  .header .stats{{justify-content:center}}
  .header .stat .num{{font-size:16px}}
  .tabs{{overflow-x:auto;-webkit-overflow-scrolling:touch;flex-wrap:nowrap}}
  .tab{{white-space:nowrap;padding:8px 16px;font-size:11px;flex-shrink:0}}
  .main{{flex-direction:column;height:auto;min-height:0}}
  .map-wrap{{width:100%;height:auto;aspect-ratio:16/11;flex:none;min-height:200px;max-height:55vh}}
  .legend{{width:100%;height:auto;border-left:none;border-top:1px solid #e0e0e0;
          overflow-y:visible;max-height:none}}
  .legend-head{{position:relative}}
  .sp-row{{padding:10px 12px}}
  .tooltip{{display:none !important}}
}}
@media(max-width:480px){{
  .header{{padding:10px 12px}}
  .header h1{{font-size:12px;letter-spacing:0.5px}}
  .header .stat .num{{font-size:14px}}
  .header .stat .lbl{{font-size:8px}}
  .tab{{padding:7px 12px;font-size:10px}}
  .sp-code{{font-size:11px}}
  .sp-name{{font-size:9px}}
  .sp-badge{{font-size:9px;padding:2px 5px}}
}}
</style>
</head>
<body>
<div class="header">
  <h1>LEGENDA DE ESPECIES</h1>
  <div class="stats">
    <div class="stat"><span class="num">{total_species}</span> <span class="lbl">especies</span></div>
    <div class="stat"><span class="num">{total_items}</span> <span class="lbl">itens</span></div>
  </div>
</div>
<div class="tabs" id="tabs"></div>
<div class="main">
  <div class="map-wrap" id="mapWrap">
    <img id="mapImg">
    <svg id="mapSvg" xmlns="http://www.w3.org/2000/svg"></svg>
  </div>
  <div class="legend" id="legend"></div>
</div>
<div class="tooltip" id="tooltip"></div>

<script>
const DATA = {json.dumps(species_json, ensure_ascii=False)};
const tabs = document.getElementById('tabs');
const mapImg = document.getElementById('mapImg');
const mapSvg = document.getElementById('mapSvg');
const legend = document.getElementById('legend');
const tooltip = document.getElementById('tooltip');
let curType = null, curCode = null;

Object.keys(DATA).forEach((type, i) => {{
  const d = DATA[type];
  const t = document.createElement('div');
  t.className = 'tab' + (i === 0 ? ' active' : '');
  t.textContent = d.label + ' (' + d.entries.length + ')';
  t.onclick = () => showType(type);
  tabs.appendChild(t);
}});

function showType(type) {{
  curType = type; curCode = null;
  document.querySelectorAll('.tab').forEach((t, i) =>
    t.classList.toggle('active', Object.keys(DATA)[i] === type));
  const d = DATA[type];
  mapImg.src = d.map;
  renderSvg(d);
  renderLegend(d);
}}

function renderSvg(d) {{
  const svgNS = 'http://www.w3.org/2000/svg';
  mapSvg.setAttribute('viewBox', '0 0 ' + d.pw + ' ' + d.ph);
  mapSvg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  mapSvg.innerHTML = '';

  const isForr = d.type === 'forracao';
  const r = d.pw * (d.type === 'arbusto' ? 0.006 : 0.0134);

  d.entries.forEach(e => {{
    const g = document.createElementNS(svgNS, 'g');
    g.dataset.code = e.code;
    g.style.cursor = 'pointer';

    if (isForr && e.svg_paths.length > 0) {{
      e.svg_paths.forEach(pathD => {{
        const p = document.createElementNS(svgNS, 'path');
        p.setAttribute('d', pathD);
        p.setAttribute('fill', e.color);
        p.setAttribute('fill-opacity', '0.55');
        p.setAttribute('stroke', e.color);
        p.setAttribute('stroke-width', '1');
        p.setAttribute('stroke-opacity', '0.3');
        g.appendChild(p);
      }});
    }} else {{
      e.positions.forEach(pos => {{
        const c = document.createElementNS(svgNS, 'circle');
        c.setAttribute('cx', pos.x);
        c.setAttribute('cy', pos.y);
        c.setAttribute('r', r);
        c.setAttribute('fill', e.color);
        c.setAttribute('fill-opacity', '0.75');
        c.setAttribute('stroke', '#fff');
        c.setAttribute('stroke-width', '2.5');
        g.appendChild(c);
      }});
    }}

    g.addEventListener('mouseenter', ev => {{ highlight(e.code); showTT(ev, e); }});
    g.addEventListener('mouseleave', () => {{ unhighlight(); hideTT(); }});
    mapSvg.appendChild(g);
  }});
}}

function renderLegend(d) {{
  legend.innerHTML = '<div class="legend-head">' + d.label + '</div>';
  d.entries.forEach(e => {{
    const row = document.createElement('div');
    row.className = 'sp-row';
    row.dataset.code = e.code;
    row.innerHTML =
      '<div class="sp-dot" style="background:' + e.color + '"></div>' +
      '<div class="sp-info">' +
        '<div class="sp-code">' + e.code + '</div>' +
        (e.scientific ? '<div class="sp-name">' + e.scientific + '</div>' : '') +
        (e.common ? '<div class="sp-meta">' + e.common + '</div>' : '') +
      '</div>' +
      '<div class="sp-badge" style="background:' + e.color + '">' + e.count + '</div>';
    row.addEventListener('mouseenter', ev => {{ highlight(e.code); showTT(ev, e); }});
    row.addEventListener('mouseleave', () => {{ unhighlight(); hideTT(); }});
    legend.appendChild(row);
  }});
}}

function highlight(code) {{
  curCode = code;
  mapSvg.querySelectorAll('g').forEach(g => {{
    g.style.opacity = g.dataset.code === code ? '1' : '0.15';
    if (g.dataset.code === code) {{
      g.querySelectorAll('circle,path').forEach(el => {{
        el.setAttribute('stroke-width', '4');
      }});
    }}
  }});
  legend.querySelectorAll('.sp-row').forEach(r =>
    r.classList.toggle('active', r.dataset.code === code));
}}

function unhighlight() {{
  curCode = null;
  mapSvg.querySelectorAll('g').forEach(g => {{
    g.style.opacity = '1';
    g.querySelectorAll('circle,path').forEach(el => {{
      el.setAttribute('stroke-width', el.tagName === 'path' ? '1' : '2.5');
    }});
  }});
  legend.querySelectorAll('.sp-row').forEach(r => r.classList.remove('active'));
}}

function showTT(ev, e) {{
  let h = '';
  if (e.img) h += '<img src="' + e.img + '">';
  else h += '<div class="noimg">sem foto</div>';
  h += '<div class="ti"><div class="tc">' + e.code + '</div>';
  if (e.scientific) h += '<div class="ts">' + e.scientific + '</div>';
  if (e.common) h += '<div class="tn">' + e.common + '</div>';
  const m = [e.origin, e.sun].filter(Boolean).join(' | ');
  h += '<div class="tm">' + (m ? m + ' | ' : '') + e.count + ' un.</div></div>';
  tooltip.innerHTML = h;
  tooltip.classList.add('show');
  posTT(ev);
}}
function posTT(ev) {{
  const r = tooltip.getBoundingClientRect();
  let x = ev.clientX + 16, y = ev.clientY - 10;
  if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - 16;
  if (y + r.height > window.innerHeight - 8) y = window.innerHeight - r.height - 8;
  if (y < 8) y = 8;
  tooltip.style.left = x + 'px'; tooltip.style.top = y + 'px';
}}
document.addEventListener('mousemove', ev => {{
  if (tooltip.classList.contains('show')) posTT(ev);
}});
function hideTT() {{ tooltip.classList.remove('show'); }}

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
        n = len(tdata['entries'])
        total = sum(e['count'] for e in tdata['entries'])
        print(f"   {ptype}: {n} especies, {total} itens")

    print("\n3. Gerando HTML...")
    html = build_html(all_data)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"\n=== HTML gerado: {OUTPUT} ({size_kb:.0f} KB) ===")


if __name__ == "__main__":
    main()
