#!/usr/bin/env python3
"""
Gera visualizacao HTML da implantacao de vegetacao a partir do PDF de paisagismo.
Extrai posicoes das arvores e renderiza mapa com circulos coloridos sobre
a planta arquitetonica em escala de cinza.
"""

import fitz  # PyMuPDF
import base64
import os
from PIL import Image, ImageDraw, ImageFont

# --- Configuracao ---

PDF_PATH = "/Users/leonhatori/Downloads/PINI-PSG-PE-0504-LAZ-R00_IA_arvores.pdf"
OUTPUT_DIR = "/Users/leonhatori/Downloads/abbud0"
OUTPUT_HTML = os.path.join(OUTPUT_DIR, "mapa_vegetacao.html")
OUTPUT_PNG = os.path.join(OUTPUT_DIR, "mapa_vegetacao.png")
OUTPUT_PDF = os.path.join(OUTPUT_DIR, "mapa_vegetacao.pdf")

EXPORT_DPI = 150  # DPI mais alto para PNG/PDF

SPECIES = {
    "PLRU": {
        "name": "Plumeria rubra",
        "common": "Jasmim-manga",
        "color": "#E91E63",
    },
    "PHDA": {
        "name": "Phoenix dactylifera",
        "common": "Tamareira",
        "color": "#4CAF50",
    },
    "NEDE": {
        "name": "Neodypsis decaryi",
        "common": "Palmeira-triangulo",
        "color": "#2196F3",
    },
}

CIRCLE_RADIUS = 45
CIRCLE_OPACITY = 0.75
RENDER_DPI = 72


def extract_tree_positions(page):
    """Extrai posicoes dos rotulos de arvores do PDF."""
    mediabox_w = page.mediabox.width  # 2384.0 (pre-rotacao)

    tree_data = {code: [] for code in SPECIES}
    text_dict = page.get_text("dict")

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span["text"].strip()
                if text in SPECIES:
                    bbox = span["bbox"]
                    # Centro do bounding box no espaco raw (pre-rotacao)
                    cx = (bbox[0] + bbox[2]) / 2
                    cy = (bbox[1] + bbox[3]) / 2
                    # Transformacao para espaco renderizado (rotacao 270)
                    rendered_x = cy
                    rendered_y = mediabox_w - cx
                    tree_data[text].append({
                        "x": round(rendered_x, 1),
                        "y": round(rendered_y, 1),
                    })

    return tree_data


def render_background(page):
    """Renderiza a pagina do PDF como PNG em base64."""
    pix = page.get_pixmap(dpi=RENDER_DPI)
    png_bytes = pix.tobytes("png")
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}", pix.width, pix.height


def generate_svg_circles(tree_data):
    """Gera elementos SVG <circle> para cada arvore."""
    circles = []
    for code, positions in tree_data.items():
        color = SPECIES[code]["color"]
        for i, pos in enumerate(positions):
            circles.append(
                f'    <circle cx="{pos["x"]}" cy="{pos["y"]}" r="{CIRCLE_RADIUS}" '
                f'fill="{color}" fill-opacity="{CIRCLE_OPACITY}" '
                f'stroke="white" stroke-width="2.5" '
                f'data-species="{code}" data-index="{i}"/>'
            )
    return "\n".join(circles)


def generate_legend_items(tree_data):
    """Gera itens HTML da legenda."""
    items = []
    for code, info in SPECIES.items():
        count = len(tree_data.get(code, []))
        items.append(f"""
            <div class="legend-item">
                <span class="legend-circle" style="background:{info['color']}"></span>
                <div class="legend-text">
                    <span class="species-code">{code}</span>
                    <span class="species-name">{info['name']}</span>
                    <span class="species-count">({count} un.)</span>
                </div>
            </div>""")
    return "\n".join(items)


def generate_html(bg_data_url, bg_width, bg_height, tree_data):
    """Gera o HTML completo da visualizacao."""
    svg_circles = generate_svg_circles(tree_data)
    legend_items = generate_legend_items(tree_data)
    total_trees = sum(len(v) for v in tree_data.values())
    total_species = sum(1 for v in tree_data.values() if len(v) > 0)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mapa de Implantacao de Vegetacao</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background: #1a1a1a;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            color: #333;
            padding: 20px;
        }}

        .page {{
            max-width: 1600px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            padding: 24px 20px 18px;
            background: #ffffff;
            border: 1px solid #ddd;
            margin-bottom: 2px;
        }}

        .header h1 {{
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 3px;
            color: #222;
            margin-bottom: 6px;
        }}

        .header .subtitle {{
            font-size: 13px;
            color: #777;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        .header .meta {{
            font-size: 12px;
            color: #aaa;
            margin-top: 8px;
        }}

        .map-container {{
            position: relative;
            width: 100%;
            background: #ffffff;
            border: 1px solid #ddd;
            border-top: none;
            overflow: hidden;
        }}

        .map-container .background {{
            display: block;
            width: 100%;
            height: auto;
            filter: grayscale(100%);
            opacity: 0.2;
        }}

        .map-container .overlay {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }}

        .legend-bar {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 50px;
            padding: 18px 20px;
            background: #ffffff;
            border: 1px solid #ddd;
            border-top: none;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .legend-circle {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: inline-block;
            flex-shrink: 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }}

        .legend-text {{
            display: flex;
            align-items: baseline;
            gap: 6px;
        }}

        .species-code {{
            font-weight: 700;
            font-size: 14px;
            color: #333;
        }}

        .species-name {{
            font-style: italic;
            font-size: 13px;
            color: #666;
        }}

        .species-count {{
            font-size: 11px;
            color: #999;
        }}

        .footer {{
            text-align: center;
            padding: 12px;
            font-size: 10px;
            color: #555;
            letter-spacing: 0.5px;
        }}

        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .map-container {{
                border: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="page">
        <div class="header">
            <h1>IMPLANTA&Ccedil;&Atilde;O DE VEGETA&Ccedil;&Atilde;O</h1>
            <p class="subtitle">Plano de Paisagismo &mdash; Mapa de Esp&eacute;cies Arb&oacute;reas</p>
            <p class="meta">{total_trees} &aacute;rvores &middot; {total_species} esp&eacute;cies</p>
        </div>

        <div class="map-container">
            <img class="background"
                 src="{bg_data_url}"
                 alt="Planta arquitetonica"
                 width="{bg_width}"
                 height="{bg_height}" />

            <svg class="overlay"
                 viewBox="0 0 {bg_width} {bg_height}"
                 preserveAspectRatio="xMidYMid meet"
                 xmlns="http://www.w3.org/2000/svg">
{svg_circles}
            </svg>
        </div>

        <div class="legend-bar">
{legend_items}
        </div>

        <p class="footer">
            PINI-PSG-PE-0504-LAZ-R00 &mdash; Implanta&ccedil;&atilde;o de &Aacute;rvores
        </p>
    </div>
</body>
</html>"""


def hex_to_rgb(hex_color):
    """Converte cor hex para tupla RGB."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def generate_png(page, tree_data):
    """Gera imagem PNG com fundo em cinza e circulos coloridos."""
    # Renderiza PDF em alta resolucao
    pix = page.get_pixmap(dpi=EXPORT_DPI)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    # Escala do PDF para pixels na imagem exportada
    scale = EXPORT_DPI / 72.0
    img_w, img_h = img.size

    # Converte para escala de cinza
    gray = img.convert("L").convert("RGB")

    # Aplica opacidade 20% (blend com fundo branco)
    white_bg = Image.new("RGB", (img_w, img_h), (255, 255, 255))
    base = Image.blend(white_bg, gray, 0.20)

    # Margem para titulo e legenda
    header_h = int(100 * scale)
    legend_h = int(70 * scale)
    total_h = header_h + img_h + legend_h
    canvas = Image.new("RGB", (img_w, total_h), (255, 255, 255))
    canvas.paste(base, (0, header_h))

    draw = ImageDraw.Draw(canvas)

    # Tenta carregar fonte; fallback para default
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
    total_trees = sum(len(v) for v in tree_data.values())
    title = "IMPLANTACAO DE VEGETACAO"
    subtitle = "Plano de Paisagismo - Mapa de Especies Arboreas"
    meta = f"{total_trees} arvores - 3 especies"

    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((img_w - (title_bbox[2] - title_bbox[0])) / 2, int(15 * scale)),
              title, fill=(34, 34, 34), font=font_title)

    sub_bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
    draw.text(((img_w - (sub_bbox[2] - sub_bbox[0])) / 2, int(50 * scale)),
              subtitle, fill=(119, 119, 119), font=font_sub)

    meta_bbox = draw.textbbox((0, 0), meta, font=font_footer)
    draw.text(((img_w - (meta_bbox[2] - meta_bbox[0])) / 2, int(72 * scale)),
              meta, fill=(170, 170, 170), font=font_footer)

    # Linha separadora abaixo do titulo
    draw.line([(int(50 * scale), header_h - 2), (img_w - int(50 * scale), header_h - 2)],
              fill=(221, 221, 221), width=2)

    # Desenha circulos das arvores
    circle_r = int(CIRCLE_RADIUS * scale)
    for code, positions in tree_data.items():
        rgb = hex_to_rgb(SPECIES[code]["color"])
        # Cria circulo semi-transparente
        for pos in positions:
            px = int(pos["x"] * scale)
            py = int(pos["y"] * scale) + header_h
            # Circulo com alpha blending manual
            overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            fill_color = rgb + (int(255 * CIRCLE_OPACITY),)
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
    legend_items = list(SPECIES.items())
    legend_total_w = img_w
    item_w = legend_total_w // len(legend_items)

    for i, (code, info) in enumerate(legend_items):
        count = len(tree_data.get(code, []))
        rgb = hex_to_rgb(info["color"])
        cx = int(item_w * i + item_w / 2)
        cy = legend_y + int(legend_h / 2)

        # Circulo da legenda
        cr = int(10 * scale)
        draw.ellipse([cx - item_w // 4 - cr, cy - cr, cx - item_w // 4 + cr, cy + cr],
                     fill=rgb, outline=(200, 200, 200), width=1)

        # Texto
        text_x = cx - item_w // 4 + cr + int(8 * scale)
        label = f"{code}  {info['name']}  ({count} un.)"
        draw.text((text_x, cy - int(8 * scale)), code, fill=(51, 51, 51), font=font_legend)
        name_offset = draw.textbbox((0, 0), code + "  ", font=font_legend)[2]
        draw.text((text_x + name_offset, cy - int(7 * scale)),
                  f"{info['name']}  ({count} un.)", fill=(119, 119, 119), font=font_legend_it)

    # Rodape
    footer_text = "PINI-PSG-PE-0504-LAZ-R00 - Implantacao de Arvores"
    ft_bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    draw.text(((img_w - (ft_bbox[2] - ft_bbox[0])) / 2, total_h - int(18 * scale)),
              footer_text, fill=(150, 150, 150), font=font_footer)

    canvas.save(OUTPUT_PNG, "PNG", dpi=(EXPORT_DPI, EXPORT_DPI))
    return canvas


def generate_pdf_output(page, tree_data):
    """Gera PDF com fundo em cinza e circulos coloridos usando PyMuPDF."""
    # Renderiza fundo em escala de cinza (DPI menor para PDF leve)
    pdf_bg_dpi = 96
    pix = page.get_pixmap(dpi=pdf_bg_dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    gray = img.convert("L").convert("RGB")
    white_bg = Image.new("RGB", img.size, (255, 255, 255))
    base = Image.blend(white_bg, gray, 0.20)

    # Salva fundo temporario como JPEG para reduzir tamanho
    tmp_bg = os.path.join(OUTPUT_DIR, "_tmp_bg.jpg")
    base.save(tmp_bg, "JPEG", quality=75)

    # Dimensoes da pagina renderizada (em pontos PDF a 72 DPI)
    page_w = page.rect.width   # 3370
    page_h = page.rect.height  # 2384

    # Margens para titulo e legenda
    header_pts = 60
    legend_pts = 50
    total_h = header_pts + page_h + legend_pts

    # Cria novo documento PDF
    out_doc = fitz.open()
    out_page = out_doc.new_page(width=page_w, height=total_h)

    # Fundo branco ja e padrao

    # Insere imagem de fundo
    bg_rect = fitz.Rect(0, header_pts, page_w, header_pts + page_h)
    out_page.insert_image(bg_rect, filename=tmp_bg)

    # Linha separadora abaixo do titulo
    out_page.draw_line(fitz.Point(30, header_pts - 2), fitz.Point(page_w - 30, header_pts - 2),
                       color=(0.87, 0.87, 0.87), width=1)

    # Titulo
    total_trees = sum(len(v) for v in tree_data.values())
    title_rect = fitz.Rect(0, 10, page_w, 38)
    out_page.insert_textbox(title_rect, "IMPLANTACAO DE VEGETACAO",
                            fontsize=22, fontname="helv", color=(0.13, 0.13, 0.13),
                            align=fitz.TEXT_ALIGN_CENTER)

    sub_rect = fitz.Rect(0, 34, page_w, 50)
    out_page.insert_textbox(sub_rect, "Plano de Paisagismo - Mapa de Especies Arboreas",
                            fontsize=10, fontname="helv", color=(0.47, 0.47, 0.47),
                            align=fitz.TEXT_ALIGN_CENTER)

    meta_rect = fitz.Rect(0, 47, page_w, 58)
    out_page.insert_textbox(meta_rect, f"{total_trees} arvores - 3 especies",
                            fontsize=8, fontname="helv", color=(0.67, 0.67, 0.67),
                            align=fitz.TEXT_ALIGN_CENTER)

    # Desenha circulos das arvores
    shape = out_page.new_shape()
    for code, positions in tree_data.items():
        rgb = hex_to_rgb(SPECIES[code]["color"])
        color = tuple(c / 255.0 for c in rgb)
        for pos in positions:
            center = fitz.Point(pos["x"], pos["y"] + header_pts)
            shape.draw_circle(center, CIRCLE_RADIUS)
            shape.finish(color=(1, 1, 1), fill=color, width=2.5,
                         fill_opacity=CIRCLE_OPACITY, stroke_opacity=0.9)
    shape.commit()

    # Linha separadora acima da legenda
    legend_y = header_pts + page_h
    out_page.draw_line(fitz.Point(30, legend_y + 2), fitz.Point(page_w - 30, legend_y + 2),
                       color=(0.87, 0.87, 0.87), width=1)

    # Legenda
    items = list(SPECIES.items())
    item_w = page_w / len(items)
    for i, (code, info) in enumerate(items):
        count = len(tree_data.get(code, []))
        rgb = hex_to_rgb(info["color"])
        color = tuple(c / 255.0 for c in rgb)
        cx = item_w * i + item_w / 2
        cy = legend_y + legend_pts / 2

        # Circulo da legenda
        leg_shape = out_page.new_shape()
        leg_shape.draw_circle(fitz.Point(cx - 120, cy), 8)
        leg_shape.finish(fill=color, color=(0.8, 0.8, 0.8), width=0.5)
        leg_shape.commit()

        # Texto da legenda
        txt_rect = fitz.Rect(cx - 105, cy - 8, cx + 200, cy + 10)
        label = f"{code}  {info['name']}  ({count} un.)"
        out_page.insert_textbox(txt_rect, label,
                                fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))

    # Rodape
    footer_rect = fitz.Rect(0, total_h - 15, page_w, total_h - 3)
    out_page.insert_textbox(footer_rect,
                            "PINI-PSG-PE-0504-LAZ-R00 - Implantacao de Arvores",
                            fontsize=7, fontname="helv", color=(0.6, 0.6, 0.6),
                            align=fitz.TEXT_ALIGN_CENTER)

    out_doc.save(OUTPUT_PDF)
    out_doc.close()

    # Limpa temporario
    if os.path.exists(tmp_bg):
        os.remove(tmp_bg)


def main():
    print("Abrindo PDF...")
    doc = fitz.open(PDF_PATH)
    page = doc[0]

    print(f"  Pagina: {page.rect.width}x{page.rect.height} (rotacao={page.rotation})")
    print(f"  MediaBox: {page.mediabox.width}x{page.mediabox.height}")

    print("Extraindo posicoes das arvores...")
    tree_data = extract_tree_positions(page)

    for code, positions in tree_data.items():
        print(f"  {code}: {len(positions)} arvores")
        for p in positions:
            print(f"    ({p['x']}, {p['y']})")

    total = sum(len(v) for v in tree_data.values())
    if total == 0:
        print("AVISO: Nenhuma arvore encontrada! Verifique os rotulos no PDF.")
        return

    # --- HTML ---
    print(f"Renderizando fundo a {RENDER_DPI} DPI...")
    bg_data_url, bg_w, bg_h = render_background(page)
    print(f"  Imagem: {bg_w}x{bg_h} pixels")

    print("Gerando HTML...")
    html = generate_html(bg_data_url, bg_w, bg_h, tree_data)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(OUTPUT_HTML) / 1024
    print(f"  -> {OUTPUT_HTML} ({size_kb:.0f} KB)")

    # --- PNG ---
    print(f"Gerando PNG a {EXPORT_DPI} DPI...")
    generate_png(page, tree_data)
    size_kb = os.path.getsize(OUTPUT_PNG) / 1024
    print(f"  -> {OUTPUT_PNG} ({size_kb:.0f} KB)")

    # --- PDF ---
    print(f"Gerando PDF a {EXPORT_DPI} DPI...")
    generate_pdf_output(page, tree_data)
    size_kb = os.path.getsize(OUTPUT_PDF) / 1024
    print(f"  -> {OUTPUT_PDF} ({size_kb:.0f} KB)")

    print(f"\nTotal: {total} arvores mapeadas em 3 formatos (HTML, PNG, PDF)")

    doc.close()


if __name__ == "__main__":
    main()
