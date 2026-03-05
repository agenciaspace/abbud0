#!/usr/bin/env python3
"""
Gera visualizacoes HTML/PNG/PDF da implantacao de vegetacao a partir de PDFs de paisagismo.
Processa 3 camadas separadas: arvores, arbustos e forracoes.
Cada camada gera seus proprios arquivos de saida (HTML, PNG, PDF).
"""

import fitz  # PyMuPDF
import base64
import os
import re
from PIL import Image, ImageDraw, ImageFont

# --- Configuracao ---

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVOS_DIR = os.path.join(BASE_DIR, "arquivos")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

PDF_ARVORES = os.path.join(ARQUIVOS_DIR, "PINI-PSG-PE-0504-LAZ-R00_IA_arvores.pdf")
PDF_ARBUSTOS = os.path.join(ARQUIVOS_DIR, "PINI-PSG-PE-0504-LAZ-R00_IA_arbustos.pdf")
PDF_FORRACOES = os.path.join(ARQUIVOS_DIR, "PINI-PSG-PE-0504-LAZ-R00_IA_forrações.pdf")

EXPORT_DPI = 150
RENDER_DPI = 72
CIRCLE_OPACITY = 0.75

# Raios por tipo de planta
RADIUS_ARVORE = 45
RADIUS_ARBUSTO = 20

# --- Banco de especies ---

SPECIES = {
    # Arvores
    "PLRU": {"name": "Plumeria rubra", "common": "Jasmim-manga", "type": "arvore"},
    "PHDA": {"name": "Phoenix dactylifera", "common": "Tamareira", "type": "arvore"},
    "NEDE": {"name": "Neodypsis decaryi", "common": "Palmeira-triangulo", "type": "arvore"},
    # Arbustos
    "ALGP": {"name": "Alpinia giant pink shell", "common": "Alpinia rosa gigante", "type": "arbusto"},
    "ALMA": {"name": "Alocasia macrorrhizos", "common": "Alocasia", "type": "arbusto"},
    "ALZE": {"name": "Alpinia zerumbet variegata", "common": "Alpinia variegata", "type": "arbusto"},
    "CALU": {"name": "Calathea lutea", "common": "Calateia charuto", "type": "arbusto"},
    "CHLU": {"name": "Chrysalidocarpus lutescens", "common": "Areca s/ folhas embaixo", "type": "arbusto"},
    "CYLA": {"name": "Cyrtostachys lakka", "common": "Laka", "type": "arbusto"},
    "DRAR": {"name": "Dracaena arborea", "common": "Dracena arborea", "type": "arbusto"},
    "DRAV": {"name": "Dracaena arborea", "common": "Dracena arborea", "type": "arbusto"},
    "DRAT": {"name": "Dracaena arborea", "common": "Dracena arborea", "type": "arbusto"},
    "HEBI": {"name": "Heliconia bihai", "common": "Heliconia alta", "type": "arbusto"},
    "HIND": {"name": "Heliconia indica", "common": "Heliconia", "type": "arbusto"},
    "PHRO": {"name": "Phoenix roebelinii", "common": "Tamareira ana", "type": "arbusto"},
    "PLRE": {"name": "Pleomele reflexa", "common": "Pleomele", "type": "arbusto"},
    "PLRV": {"name": "Pleomele reflexa variegata", "common": "Pleomele variegata", "type": "arbusto"},
    "THGR": {"name": "Thunbergia grandiflora", "common": "Tumbergia", "type": "arbusto"},
    "ZAFU": {"name": "Zamia furfuracea", "common": "Zamia", "type": "arbusto"},
    "CLFL": {"name": "Clusia fluminensis", "common": "Clusia", "type": "arbusto"},
    "PURE": {"name": "Plumeria rubra", "common": "Plumeria", "type": "arbusto"},
}

# Forracoes: mapeamento cor -> identificacao
# Cada forracao e identificada pela cor de preenchimento no PDF
FORRACOES_COLOR_MAP = {
    (0.576, 0.400, 0.898): {"label": "PESE(BZ) + CAAR", "codes": ["PESE", "CAAR"]},
    (0.886, 0.976, 0.886): {"label": "ARRE", "codes": ["ARRE"]},
    (0.529, 0.769, 0.667): {"label": "WEPA + PHBI", "codes": ["WEPA", "PHBI"]},
    (0.306, 0.475, 0.651): {"label": "WEPA + CLFL", "codes": ["WEPA", "CLFL"]},
    (0.761, 1.000, 0.878): {"label": "WEPA + PHDN", "codes": ["WEPA", "PHDN"]},
    (0.965, 0.886, 0.435): {"label": "CAAR + DIEN", "codes": ["CAAR", "DIEN"]},
    (0.706, 0.682, 0.592): {"label": "CAAR + PHIB", "codes": ["CAAR", "PHIB"]},
    (0.651, 0.788, 0.827): {"label": "EVGL", "codes": ["EVGL"]},
    (1.000, 0.867, 0.820): {"label": "CAAR + PHRN", "codes": ["CAAR", "PHRN"]},
    (0.922, 0.612, 0.259): {"label": "NERV", "codes": ["NERV"]},
    (0.871, 0.616, 0.529): {"label": "WEPA + THWI", "codes": ["WEPA", "THWI"]},
    (0.690, 0.847, 0.690): {"label": "OPJB(VD)", "codes": ["OPJB"]},
    # Cores identificadas pela analise do PDF PINI-PSG-PE-0504-LAZ-R00
    (0.384, 0.443, 0.294): {"label": "MOIR + CAAR", "codes": ["MOIR", "CAAR"]},
    (1.000, 1.000, 0.000): {"label": "MOIR + CAAR", "codes": ["MOIR", "CAAR"]},
    (1.000, 0.000, 0.000): {"label": "WEPA + CLFL", "codes": ["WEPA", "CLFL"]},
    (0.867, 0.000, 0.000): {"label": "WEPA + CLFL", "codes": ["WEPA", "CLFL"]},
    (0.867, 0.431, 0.000): {"label": "WEPA + PHBI", "codes": ["WEPA", "PHBI"]},
}

# Paleta de cores para visualizacao
COLOR_PALETTE = [
    "#E91E63", "#4CAF50", "#2196F3", "#FF9800", "#9C27B0",
    "#00BCD4", "#F44336", "#8BC34A", "#3F51B5", "#FFEB3B",
    "#795548", "#607D8B", "#FF5722", "#009688", "#673AB7",
    "#CDDC39", "#03A9F4", "#E040FB", "#76FF03", "#FF6D00",
]

PLANT_TYPE_CONFIG = {
    "arvore": {
        "label": "Arvores",
        "label_full": "Implantacao de Arvores",
        "unit": "arvores",
    },
    "arbusto": {
        "label": "Arbustos",
        "label_full": "Implantacao de Arbustos",
        "unit": "arbustos",
    },
    "forracao": {
        "label": "Forracoes",
        "label_full": "Implantacao de Forracoes",
        "unit": "areas",
    },
}


def hex_to_rgb(hex_color):
    """Converte cor hex para tupla RGB."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_distance(c1, c2):
    """Distancia euclidiana entre duas cores RGB (0-1)."""
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def match_forracao_color(fill_color):
    """Encontra a forracao mais proxima pela cor de preenchimento."""
    best_match = None
    best_dist = float("inf")
    for ref_color, info in FORRACOES_COLOR_MAP.items():
        dist = color_distance(fill_color, ref_color)
        if dist < best_dist:
            best_dist = dist
            best_match = (ref_color, info)
    if best_dist < 0.15:  # tolerancia de cor
        return best_match
    return None


# --- Extracao de dados ---

def _extract_text_labels(page, valid_codes):
    """Extrai todos os labels de texto com coordenadas transformadas."""
    mediabox_w = page.mediabox.width
    labels = []
    text_dict = page.get_text("dict")

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span["text"].strip()
                base_code = re.sub(r'\([^)]*\)', '', text).strip()
                if base_code in valid_codes:
                    bbox = span["bbox"]
                    cx = (bbox[0] + bbox[2]) / 2
                    cy = (bbox[1] + bbox[3]) / 2
                    rendered_x = cy
                    rendered_y = mediabox_w - cx
                    labels.append({
                        "code": base_code,
                        "x": round(rendered_x, 1),
                        "y": round(rendered_y, 1),
                    })

    return labels


def extract_positions(page, plant_type):
    """Extrai posicoes dos rotulos de plantas do PDF por tipo (arvores)."""
    rendered_w = page.rect.width
    rendered_h = page.rect.height

    # Margem para filtrar labels de borda (% da dimensao da pagina)
    margin_pct = 0.05
    margin_x = rendered_w * margin_pct
    margin_y = rendered_h * margin_pct

    valid_codes = {code for code, info in SPECIES.items() if info["type"] == plant_type}
    labels = _extract_text_labels(page, valid_codes)

    plant_data = {}
    for l in labels:
        # Filtra labels de borda
        if (l["x"] < margin_x or l["x"] > rendered_w - margin_x or
                l["y"] < margin_y or l["y"] > rendered_h - margin_y):
            continue
        code = l["code"]
        if code not in plant_data:
            plant_data[code] = []
        plant_data[code].append({"x": l["x"], "y": l["y"]})

    return plant_data


def extract_shrub_positions(page):
    """Extrai posicoes de arbustos detectando simbolos triangulares no PDF.

    Arbustos sao representados por pequenos triangulos pretos no PDF.
    Cada triangulo e associado a especie do label de texto mais proximo.
    """
    import math
    mediabox_w = page.mediabox.width
    rendered_w = page.rect.width
    rendered_h = page.rect.height

    # Margem para filtrar elementos fora da area util
    margin_pct = 0.03
    margin_x = rendered_w * margin_pct
    margin_y = rendered_h * margin_pct

    # 1. Obter todos os labels de especies (inclusive borda, para associacao)
    valid_codes = {code for code, info in SPECIES.items() if info["type"] == "arbusto"}
    labels = _extract_text_labels(page, valid_codes)

    if not labels:
        return {}

    # 2. Detectar simbolos triangulares (pequenos shapes pretos)
    drawings = page.get_drawings()
    triangles = []
    for d in drawings:
        fill = d.get("fill")
        if fill is None:
            continue
        r, g, b = fill
        # Apenas shapes pretos (triangulos de arbusto)
        if not (r < 0.1 and g < 0.1 and b < 0.1):
            continue
        rect = d.get("rect")
        if not rect:
            continue
        w = abs(rect.x1 - rect.x0)
        h = abs(rect.y1 - rect.y0)
        # Tamanho tipico de simbolo de arbusto
        if w > 20 or h > 20 or w < 3 or h < 3:
            continue

        # Transforma coordenadas (rotacao 270)
        cx_raw = (rect.x0 + rect.x1) / 2
        cy_raw = (rect.y0 + rect.y1) / 2
        tx = cy_raw
        ty = mediabox_w - cx_raw

        # Filtra fora dos limites
        if tx < margin_x or tx > rendered_w - margin_x:
            continue
        if ty < margin_y or ty > rendered_h - margin_y:
            continue

        triangles.append({"x": round(tx, 1), "y": round(ty, 1)})

    if not triangles:
        return {}

    # 3. Associa cada triangulo ao label mais proximo
    def dist(a, b):
        return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)

    plant_data = {}
    for tri in triangles:
        nearest = min(labels, key=lambda l: dist(l, tri))
        d = dist(nearest, tri)
        # Distancia maxima de associacao (evita falsos positivos)
        if d > 500:
            continue
        code = nearest["code"]
        if code not in plant_data:
            plant_data[code] = []
        plant_data[code].append({"x": tri["x"], "y": tri["y"]})

    return plant_data


def extract_ground_cover_areas(page):
    """Extrai areas de forracao do PDF baseado nas cores dos desenhos."""
    mediabox_w = page.mediabox.width
    rendered_w = page.rect.width
    rendered_h = page.rect.height

    drawings = page.get_drawings()
    areas_by_label = {}  # {label: {"color": hex, "paths": [...], "ref_color": (r,g,b)}}

    for d in drawings:
        fill = d.get("fill")
        if not fill:
            continue
        # Ignora preto puro e branco puro (mas nao cores claras mapeadas como ARRE)
        if all(c < 0.1 for c in fill):
            continue
        if all(c > 0.95 for c in fill):
            continue

        match = match_forracao_color(fill)
        if not match:
            continue

        ref_color, info = match
        label = info["label"]

        if label not in areas_by_label:
            areas_by_label[label] = {
                "ref_color": ref_color,
                "paths": [],
            }

        # Extrai pontos do caminho e aplica rotacao 270
        # Coordenadas de get_drawings() estao no espaco mediabox (raw)
        # Transformacao: rendered_x = raw_y, rendered_y = mediabox_w - raw_x
        raw_points = []
        for item in d.get("items", []):
            op = item[0]
            if op == "l":  # linha
                p1, p2 = item[1], item[2]
                raw_points.append((p1.x, p1.y))
                raw_points.append((p2.x, p2.y))
            elif op == "re":  # retangulo
                rect = item[1]
                raw_points.append((rect.x0, rect.y0))
                raw_points.append((rect.x1, rect.y0))
                raw_points.append((rect.x1, rect.y1))
                raw_points.append((rect.x0, rect.y1))
            elif op == "c":  # curva bezier
                p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                raw_points.extend([(p1.x, p1.y), (p2.x, p2.y), (p3.x, p3.y), (p4.x, p4.y)])
            elif op == "qu":  # quadratica
                for p in item[1:]:
                    raw_points.append((p.x, p.y))

        if not raw_points:
            continue

        # Aplica transformacao de rotacao 270
        path_points = [(ry, mediabox_w - rx) for rx, ry in raw_points]

        # Filtra pontos fora dos limites do mapa
        if all(px < 0 or px > rendered_w or py < 0 or py > rendered_h
               for px, py in path_points):
            continue

        areas_by_label[label]["paths"].append(path_points)

    return areas_by_label


# --- Renderizacao ---

def render_background(page):
    """Renderiza a pagina do PDF como PNG em base64."""
    pix = page.get_pixmap(dpi=RENDER_DPI)
    png_bytes = pix.tobytes("png")
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}", pix.width, pix.height


def assign_colors(data, plant_type):
    """Atribui cores da paleta para cada especie/area detectada."""
    color_map = {}
    if plant_type == "forracao":
        for i, label in enumerate(sorted(data.keys())):
            ref_color = data[label]["ref_color"]
            # Usa a cor original do PDF convertida para hex
            r, g, b = ref_color
            color_map[label] = "#{:02x}{:02x}{:02x}".format(
                int(r * 255), int(g * 255), int(b * 255)
            )
    else:
        for i, code in enumerate(sorted(data.keys())):
            color_map[code] = COLOR_PALETTE[i % len(COLOR_PALETTE)]
    return color_map


# --- Geracao SVG ---

def generate_svg_elements(data, color_map, plant_type):
    """Gera elementos SVG para cada tipo de planta."""
    elements = []
    if plant_type == "forracao":
        for label, area_info in data.items():
            color = color_map[label]
            for path_points in area_info["paths"]:
                if len(path_points) < 2:
                    continue
                d_attr = "M " + " L ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in path_points) + " Z"
                elements.append(
                    f'    <path d="{d_attr}" fill="{color}" fill-opacity="0.6" '
                    f'stroke="{color}" stroke-width="0.5" stroke-opacity="0.3" '
                    f'data-forracao="{label}"/>'
                )
    else:
        radius = RADIUS_ARVORE if plant_type == "arvore" else RADIUS_ARBUSTO
        stroke_dash = "" if plant_type == "arvore" else ' stroke-dasharray="4,2"'
        for code, positions in data.items():
            color = color_map[code]
            for i, pos in enumerate(positions):
                elements.append(
                    f'    <circle cx="{pos["x"]}" cy="{pos["y"]}" r="{radius}" '
                    f'fill="{color}" fill-opacity="{CIRCLE_OPACITY}" '
                    f'stroke="white" stroke-width="2.5"{stroke_dash} '
                    f'data-species="{code}" data-index="{i}"/>'
                )
    return "\n".join(elements)


def generate_legend_items(data, color_map, plant_type):
    """Gera itens HTML da legenda."""
    items = []
    if plant_type == "forracao":
        for label in sorted(data.keys()):
            color = color_map[label]
            count = len(data[label]["paths"])
            symbol_style = f"background:{color};border-radius:4px;"
            items.append(f"""
            <div class="legend-item">
                <span class="legend-circle" style="{symbol_style}"></span>
                <div class="legend-text">
                    <span class="species-code">{label}</span>
                    <span class="species-count">({count} areas)</span>
                </div>
            </div>""")
    else:
        for code in sorted(data.keys()):
            color = color_map[code]
            count = len(data[code])
            info = SPECIES.get(code, {})
            name = info.get("name", code)
            items.append(f"""
            <div class="legend-item">
                <span class="legend-circle" style="background:{color}"></span>
                <div class="legend-text">
                    <span class="species-code">{code}</span>
                    <span class="species-name">{name}</span>
                    <span class="species-count">({count} un.)</span>
                </div>
            </div>""")
    return "\n".join(items)


# --- HTML ---

def generate_html(bg_data_url, bg_width, bg_height, data, color_map, plant_type, output_path):
    """Gera o HTML completo da visualizacao."""
    config = PLANT_TYPE_CONFIG[plant_type]
    svg_elements = generate_svg_elements(data, color_map, plant_type)
    legend_items = generate_legend_items(data, color_map, plant_type)

    if plant_type == "forracao":
        total = sum(len(v["paths"]) for v in data.values())
        total_species = len(data)
        meta_text = f"{total} areas &middot; {total_species} composicoes"
    else:
        total = sum(len(v) for v in data.values())
        total_species = sum(1 for v in data.values() if len(v) > 0)
        meta_text = f"{total} {config['unit']} &middot; {total_species} especies"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config['label_full']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #1a1a1a;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            color: #333;
            padding: 20px;
        }}
        .page {{ max-width: 1600px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 24px 20px 18px;
            background: #ffffff;
            border: 1px solid #ddd;
            margin-bottom: 2px;
        }}
        .header h1 {{
            font-size: 22px; font-weight: 700;
            letter-spacing: 3px; color: #222; margin-bottom: 6px;
        }}
        .header .subtitle {{
            font-size: 13px; color: #777;
            letter-spacing: 1px; text-transform: uppercase;
        }}
        .header .meta {{
            font-size: 12px; color: #aaa; margin-top: 8px;
        }}
        .map-container {{
            position: relative; width: 100%;
            background: #ffffff;
            border: 1px solid #ddd; border-top: none;
            overflow: hidden;
        }}
        .map-container .background {{
            display: block; width: 100%; height: auto;
            filter: grayscale(100%); opacity: 0.2;
        }}
        .map-container .overlay {{
            position: absolute; top: 0; left: 0;
            width: 100%; height: 100%;
        }}
        .legend-bar {{
            display: flex; flex-wrap: wrap;
            justify-content: center; align-items: center;
            gap: 30px;
            padding: 18px 20px;
            background: #ffffff;
            border: 1px solid #ddd; border-top: none;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 10px; }}
        .legend-circle {{
            width: 20px; height: 20px;
            border-radius: 50%; display: inline-block;
            flex-shrink: 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }}
        .legend-text {{ display: flex; align-items: baseline; gap: 6px; }}
        .species-code {{ font-weight: 700; font-size: 14px; color: #333; }}
        .species-name {{ font-style: italic; font-size: 13px; color: #666; }}
        .species-count {{ font-size: 11px; color: #999; }}
        .footer {{
            text-align: center; padding: 12px;
            font-size: 10px; color: #555; letter-spacing: 0.5px;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .map-container {{ border: none; }}
        }}
    </style>
</head>
<body>
    <div class="page">
        <div class="header">
            <h1>IMPLANTA&Ccedil;&Atilde;O DE VEGETA&Ccedil;&Atilde;O</h1>
            <p class="subtitle">Plano de Paisagismo &mdash; {config['label_full']}</p>
            <p class="meta">{meta_text}</p>
        </div>
        <div class="map-container">
            <img class="background"
                 src="{bg_data_url}"
                 alt="Planta arquitetonica"
                 width="{bg_width}" height="{bg_height}" />
            <svg class="overlay"
                 viewBox="0 0 {bg_width} {bg_height}"
                 preserveAspectRatio="xMidYMid meet"
                 xmlns="http://www.w3.org/2000/svg">
{svg_elements}
            </svg>
        </div>
        <div class="legend-bar">
{legend_items}
        </div>
        <p class="footer">
            PINI-PSG-PE-0504-LAZ-R00 &mdash; {config['label_full']}
        </p>
    </div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# --- PNG ---

def generate_png(page, data, color_map, plant_type, output_path):
    """Gera imagem PNG com fundo em cinza e elementos coloridos."""
    config = PLANT_TYPE_CONFIG[plant_type]
    pix = page.get_pixmap(dpi=EXPORT_DPI)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    scale = EXPORT_DPI / 72.0
    img_w, img_h = img.size

    # Escala de cinza com opacidade 20%
    gray = img.convert("L").convert("RGB")
    white_bg = Image.new("RGB", (img_w, img_h), (255, 255, 255))
    base = Image.blend(white_bg, gray, 0.20)

    # Margens
    header_h = int(100 * scale)
    legend_h = int(90 * scale)
    total_h = header_h + img_h + legend_h
    canvas = Image.new("RGB", (img_w, total_h), (255, 255, 255))
    canvas.paste(base, (0, header_h))

    draw = ImageDraw.Draw(canvas)

    # Fontes
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(28 * scale))
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(14 * scale))
        font_legend = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(11 * scale))
        font_legend_it = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(10 * scale))
        font_footer = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(10 * scale))
    except (OSError, IOError):
        try:
            font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(28 * scale))
            font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(14 * scale))
            font_legend = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(13 * scale))
            font_legend_it = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(12 * scale))
            font_footer = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(10 * scale))
        except (OSError, IOError):
            font_title = ImageFont.load_default()
            font_sub = font_title
            font_legend = font_title
            font_legend_it = font_title
            font_footer = font_title

    # Titulo
    if plant_type == "forracao":
        total = sum(len(v["paths"]) for v in data.values())
        total_species = len(data)
        meta = f"{total} areas - {total_species} composicoes"
    else:
        total = sum(len(v) for v in data.values())
        total_species = sum(1 for v in data.values() if len(v) > 0)
        meta = f"{total} {config['unit']} - {total_species} especies"

    title = "IMPLANTACAO DE VEGETACAO"
    subtitle = f"Plano de Paisagismo - {config['label_full']}"

    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((img_w - (title_bbox[2] - title_bbox[0])) / 2, int(15 * scale)),
              title, fill=(34, 34, 34), font=font_title)

    sub_bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
    draw.text(((img_w - (sub_bbox[2] - sub_bbox[0])) / 2, int(50 * scale)),
              subtitle, fill=(119, 119, 119), font=font_sub)

    meta_bbox = draw.textbbox((0, 0), meta, font=font_footer)
    draw.text(((img_w - (meta_bbox[2] - meta_bbox[0])) / 2, int(72 * scale)),
              meta, fill=(170, 170, 170), font=font_footer)

    # Linha separadora
    draw.line([(int(50 * scale), header_h - 2), (img_w - int(50 * scale), header_h - 2)],
              fill=(221, 221, 221), width=2)

    # Desenha elementos - usa um unico overlay para performance
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    if plant_type == "forracao":
        for label, area_info in data.items():
            color = color_map[label]
            rgb = hex_to_rgb(color)
            fill_color = rgb + (int(255 * 0.6),)
            for path_points in area_info["paths"]:
                if len(path_points) < 3:
                    continue
                scaled_points = [
                    (int(p[0] * scale), int(p[1] * scale) + header_h)
                    for p in path_points
                ]
                overlay_draw.polygon(scaled_points, fill=fill_color)
    else:
        radius = RADIUS_ARVORE if plant_type == "arvore" else RADIUS_ARBUSTO
        circle_r = int(radius * scale)
        for code, positions in data.items():
            color = color_map[code]
            rgb = hex_to_rgb(color)
            fill_color = rgb + (int(255 * CIRCLE_OPACITY),)
            for pos in positions:
                px = int(pos["x"] * scale)
                py = int(pos["y"] * scale) + header_h
                overlay_draw.ellipse(
                    [px - circle_r, py - circle_r, px + circle_r, py + circle_r],
                    fill=fill_color,
                    outline=(255, 255, 255, 230),
                    width=max(2, int(2.5 * scale))
                )

    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # Linha separadora acima da legenda
    legend_y = header_h + img_h
    draw.line([(int(50 * scale), legend_y + 2), (img_w - int(50 * scale), legend_y + 2)],
              fill=(221, 221, 221), width=2)

    # Legenda
    if plant_type == "forracao":
        legend_items = sorted(data.keys())
    else:
        legend_items = sorted(data.keys())

    if legend_items:
        items_per_row = min(len(legend_items), 6)
        item_w = img_w // items_per_row

        for i, key in enumerate(legend_items):
            row = i // items_per_row
            col = i % items_per_row
            color = color_map[key]
            rgb = hex_to_rgb(color)

            if plant_type == "forracao":
                count = len(data[key]["paths"])
                label_text = key
                count_text = f"({count} areas)"
            else:
                count = len(data[key])
                info = SPECIES.get(key, {})
                label_text = f"{key}  {info.get('name', '')}"
                count_text = f"({count} un.)"

            cx = int(item_w * col + item_w / 2)
            cy = legend_y + int(20 * scale) + int(row * 30 * scale)

            # Simbolo da legenda
            cr = int(8 * scale)
            if plant_type == "forracao":
                draw.rectangle([cx - item_w // 4 - cr, cy - cr, cx - item_w // 4 + cr, cy + cr],
                               fill=rgb, outline=(200, 200, 200), width=1)
            else:
                draw.ellipse([cx - item_w // 4 - cr, cy - cr, cx - item_w // 4 + cr, cy + cr],
                             fill=rgb, outline=(200, 200, 200), width=1)

            text_x = cx - item_w // 4 + cr + int(8 * scale)
            draw.text((text_x, cy - int(8 * scale)), label_text, fill=(51, 51, 51), font=font_legend)
            name_w = draw.textbbox((0, 0), label_text + "  ", font=font_legend)[2]
            draw.text((text_x + name_w, cy - int(7 * scale)),
                      count_text, fill=(119, 119, 119), font=font_legend_it)

    # Rodape
    footer_text = f"PINI-PSG-PE-0504-LAZ-R00 - {config['label_full']}"
    ft_bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    draw.text(((img_w - (ft_bbox[2] - ft_bbox[0])) / 2, total_h - int(18 * scale)),
              footer_text, fill=(150, 150, 150), font=font_footer)

    canvas.save(output_path, "PNG", dpi=(EXPORT_DPI, EXPORT_DPI))


# --- PDF ---

def generate_pdf_output(page, data, color_map, plant_type, output_path):
    """Gera PDF com fundo em cinza e elementos coloridos usando PyMuPDF."""
    config = PLANT_TYPE_CONFIG[plant_type]

    pdf_bg_dpi = 96
    pix = page.get_pixmap(dpi=pdf_bg_dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    gray = img.convert("L").convert("RGB")
    white_bg = Image.new("RGB", img.size, (255, 255, 255))
    base = Image.blend(white_bg, gray, 0.20)

    tmp_bg = output_path + "_tmp_bg.jpg"
    base.save(tmp_bg, "JPEG", quality=75)

    page_w = page.rect.width
    page_h = page.rect.height

    header_pts = 60
    legend_pts = 70
    total_h = header_pts + page_h + legend_pts

    out_doc = fitz.open()
    out_page = out_doc.new_page(width=page_w, height=total_h)

    bg_rect = fitz.Rect(0, header_pts, page_w, header_pts + page_h)
    out_page.insert_image(bg_rect, filename=tmp_bg)

    # Linha separadora
    out_page.draw_line(fitz.Point(30, header_pts - 2), fitz.Point(page_w - 30, header_pts - 2),
                       color=(0.87, 0.87, 0.87), width=1)

    # Titulo
    if plant_type == "forracao":
        total = sum(len(v["paths"]) for v in data.values())
        total_species = len(data)
        meta = f"{total} areas - {total_species} composicoes"
    else:
        total = sum(len(v) for v in data.values())
        total_species = sum(1 for v in data.values() if len(v) > 0)
        meta = f"{total} {config['unit']} - {total_species} especies"

    title_rect = fitz.Rect(0, 10, page_w, 38)
    out_page.insert_textbox(title_rect, "IMPLANTACAO DE VEGETACAO",
                            fontsize=22, fontname="helv", color=(0.13, 0.13, 0.13),
                            align=fitz.TEXT_ALIGN_CENTER)

    sub_rect = fitz.Rect(0, 34, page_w, 50)
    out_page.insert_textbox(sub_rect, f"Plano de Paisagismo - {config['label_full']}",
                            fontsize=10, fontname="helv", color=(0.47, 0.47, 0.47),
                            align=fitz.TEXT_ALIGN_CENTER)

    meta_rect = fitz.Rect(0, 47, page_w, 58)
    out_page.insert_textbox(meta_rect, meta,
                            fontsize=8, fontname="helv", color=(0.67, 0.67, 0.67),
                            align=fitz.TEXT_ALIGN_CENTER)

    # Desenha elementos
    shape = out_page.new_shape()
    if plant_type == "forracao":
        for label, area_info in data.items():
            color = color_map[label]
            rgb = hex_to_rgb(color)
            pdf_color = tuple(c / 255.0 for c in rgb)
            for path_points in area_info["paths"]:
                if len(path_points) < 3:
                    continue
                first = True
                for px, py in path_points:
                    point = fitz.Point(px, py + header_pts)
                    if first:
                        shape.draw_line(point, point)
                        first = False
                    else:
                        shape.draw_line(shape.last_point, point)
                shape.draw_line(shape.last_point, fitz.Point(path_points[0][0], path_points[0][1] + header_pts))
                shape.finish(color=pdf_color, fill=pdf_color, width=0.5,
                             fill_opacity=0.6, stroke_opacity=0.3)
    else:
        radius = RADIUS_ARVORE if plant_type == "arvore" else RADIUS_ARBUSTO
        for code, positions in data.items():
            color = color_map[code]
            rgb = hex_to_rgb(color)
            pdf_color = tuple(c / 255.0 for c in rgb)
            for pos in positions:
                center = fitz.Point(pos["x"], pos["y"] + header_pts)
                shape.draw_circle(center, radius)
                shape.finish(color=(1, 1, 1), fill=pdf_color, width=2.5,
                             fill_opacity=CIRCLE_OPACITY, stroke_opacity=0.9)
    shape.commit()

    # Linha acima da legenda
    legend_y = header_pts + page_h
    out_page.draw_line(fitz.Point(30, legend_y + 2), fitz.Point(page_w - 30, legend_y + 2),
                       color=(0.87, 0.87, 0.87), width=1)

    # Legenda
    if plant_type == "forracao":
        items = sorted(data.keys())
    else:
        items = sorted(data.keys())

    if items:
        items_per_row = min(len(items), 6)
        item_w = page_w / items_per_row

        for i, key in enumerate(items):
            row = i // items_per_row
            col = i % items_per_row
            color = color_map[key]
            rgb = hex_to_rgb(color)
            pdf_color = tuple(c / 255.0 for c in rgb)

            if plant_type == "forracao":
                count = len(data[key]["paths"])
                label = f"{key}  ({count} areas)"
            else:
                count = len(data[key])
                info = SPECIES.get(key, {})
                label = f"{key}  {info.get('name', '')}  ({count} un.)"

            cx = item_w * col + item_w / 2
            cy = legend_y + 20 + row * 22

            # Simbolo
            leg_shape = out_page.new_shape()
            if plant_type == "forracao":
                leg_shape.draw_rect(fitz.Rect(cx - 130, cy - 6, cx - 118, cy + 6))
            else:
                leg_shape.draw_circle(fitz.Point(cx - 120, cy), 8)
            leg_shape.finish(fill=pdf_color, color=(0.8, 0.8, 0.8), width=0.5)
            leg_shape.commit()

            txt_rect = fitz.Rect(cx - 105, cy - 8, cx + 250, cy + 10)
            out_page.insert_textbox(txt_rect, label,
                                    fontsize=8, fontname="helv", color=(0.3, 0.3, 0.3))

    # Rodape
    footer_rect = fitz.Rect(0, total_h - 15, page_w, total_h - 3)
    out_page.insert_textbox(footer_rect,
                            f"PINI-PSG-PE-0504-LAZ-R00 - {config['label_full']}",
                            fontsize=7, fontname="helv", color=(0.6, 0.6, 0.6),
                            align=fitz.TEXT_ALIGN_CENTER)

    out_doc.save(output_path)
    out_doc.close()

    if os.path.exists(tmp_bg):
        os.remove(tmp_bg)


# --- Main ---

def process_layer(pdf_path, plant_type):
    """Processa uma camada de vegetacao e gera os 3 formatos de saida."""
    config = PLANT_TYPE_CONFIG[plant_type]
    suffix_map = {"arvore": "arvores", "arbusto": "arbustos", "forracao": "forracoes"}
    suffix = suffix_map[plant_type]

    output_html = os.path.join(OUTPUT_DIR, f"mapa_{suffix}.html")
    output_png = os.path.join(OUTPUT_DIR, f"mapa_{suffix}.png")
    output_pdf = os.path.join(OUTPUT_DIR, f"mapa_{suffix}.pdf")

    print(f"\n{'=' * 60}")
    print(f"  {config['label'].upper()}")
    print(f"{'=' * 60}")

    print(f"Abrindo PDF: {os.path.basename(pdf_path)}")
    doc = fitz.open(pdf_path)
    page = doc[0]
    print(f"  Pagina: {page.rect.width}x{page.rect.height} (rotacao={page.rotation})")

    # Extrair dados
    if plant_type == "forracao":
        print("Extraindo areas de forracao...")
        data = extract_ground_cover_areas(page)
        for label, info in sorted(data.items()):
            print(f"  {label}: {len(info['paths'])} areas")
    elif plant_type == "arbusto":
        print("Extraindo posicoes dos arbustos (simbolos triangulares)...")
        data = extract_shrub_positions(page)
        for code, positions in sorted(data.items()):
            print(f"  {code}: {len(positions)} arbustos")
    else:
        print(f"Extraindo posicoes dos {config['unit']}...")
        data = extract_positions(page, plant_type)
        for code, positions in sorted(data.items()):
            print(f"  {code}: {len(positions)} {config['unit']}")

    if not data:
        print(f"AVISO: Nenhum dado encontrado para {config['label']}!")
        doc.close()
        return

    # Atribuir cores
    color_map = assign_colors(data, plant_type)

    # HTML
    print(f"Renderizando fundo a {RENDER_DPI} DPI...")
    bg_data_url, bg_w, bg_h = render_background(page)
    print(f"Gerando HTML...")
    generate_html(bg_data_url, bg_w, bg_h, data, color_map, plant_type, output_html)
    size_kb = os.path.getsize(output_html) / 1024
    print(f"  -> {output_html} ({size_kb:.0f} KB)")

    # PNG
    print(f"Gerando PNG a {EXPORT_DPI} DPI...")
    generate_png(page, data, color_map, plant_type, output_png)
    size_kb = os.path.getsize(output_png) / 1024
    print(f"  -> {output_png} ({size_kb:.0f} KB)")

    # PDF
    print(f"Gerando PDF...")
    generate_pdf_output(page, data, color_map, plant_type, output_pdf)
    size_kb = os.path.getsize(output_pdf) / 1024
    print(f"  -> {output_pdf} ({size_kb:.0f} KB)")

    if plant_type == "forracao":
        total = sum(len(v["paths"]) for v in data.values())
        print(f"\nTotal: {total} areas de forracao mapeadas")
    else:
        total = sum(len(v) for v in data.values())
        print(f"\nTotal: {total} {config['unit']} mapeados")

    doc.close()


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("  MAPA DE IMPLANTACAO DE VEGETACAO")
    print("  Arvores | Arbustos | Forracoes")
    print("=" * 60)

    # Processa cada camada
    if os.path.exists(PDF_ARVORES):
        process_layer(PDF_ARVORES, "arvore")
    else:
        print(f"\nAVISO: PDF de arvores nao encontrado: {PDF_ARVORES}")

    if os.path.exists(PDF_ARBUSTOS):
        process_layer(PDF_ARBUSTOS, "arbusto")
    else:
        print(f"\nAVISO: PDF de arbustos nao encontrado: {PDF_ARBUSTOS}")

    if os.path.exists(PDF_FORRACOES):
        process_layer(PDF_FORRACOES, "forracao")
    else:
        print(f"\nAVISO: PDF de forracoes nao encontrado: {PDF_FORRACOES}")

    print(f"\n{'=' * 60}")
    print(f"  Concluido! Arquivos em: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
