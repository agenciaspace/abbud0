#!/usr/bin/env python3
"""
Generates a professional executive presentation consolidating all vegetation
types (trees, shrubs, ground covers) from the landscaping PDFs.
Includes cover slide, summary, and species slides with photos.
"""

import os
import sys
import json

import fitz  # PyMuPDF

sys.path.insert(0, os.path.dirname(__file__))
from api.extraction import (
    SPECIES, extract_positions, extract_shrub_positions,
    extract_ground_cover_areas, assign_colors, COLOR_PALETTE,
)
from api.species import get_species_database

# --- Config ---
BASE_DIR = os.path.dirname(__file__)
ARQUIVOS = os.path.join(BASE_DIR, "arquivos")
IMG_DIR = os.path.join(BASE_DIR, "especies_img")
OUTPUT = os.path.join(BASE_DIR, "teste_apresentacao_arvores.pdf")

SLIDE_W = 1120
SLIDE_H = 630
SPECIES_PER_SLIDE = 5

# Colors
C_WHITE = (1, 1, 1)
C_BG = (0.97, 0.97, 0.97)
C_DARK = (0.12, 0.14, 0.16)
C_MID = (0.4, 0.42, 0.45)
C_LIGHT = (0.7, 0.72, 0.74)
C_LINE = (0.88, 0.88, 0.88)
C_ACCENT = (0.18, 0.55, 0.34)  # Dark green
C_ACCENT_LIGHT = (0.22, 0.65, 0.42)

TYPE_LABELS = {
    "arvore": "Arvores / Palmeiras",
    "arbusto": "Arbustos",
    "forracao": "Forracoes",
}
TYPE_PDFS = {
    "arvore": os.path.join(ARQUIVOS, "PINI-PSG-PE-0504-LAZ-R00_IA_arvores.pdf"),
    "arbusto": os.path.join(ARQUIVOS, "PINI-PSG-PE-0504-LAZ-R00_IA_arbustos.pdf"),
    "forracao": os.path.join(ARQUIVOS, "PINI-PSG-PE-0504-LAZ-R00_IA_forrações.pdf"),
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def find_image(code):
    """Find species image file by code."""
    for ext in [".png", ".jpeg", ".jpg"]:
        p = os.path.join(IMG_DIR, code + ext)
        if os.path.exists(p):
            return p
    return None


def fit_image_rect(path, area_x, area_y, max_w, max_h):
    """Calculate proportional fit rect for an image."""
    try:
        pix = fitz.Pixmap(path)
        iw, ih = pix.width, pix.height
    except:
        iw, ih = 200, 200
    scale = min(max_w / max(iw, 1), max_h / max(ih, 1), 1)
    dw, dh = iw * scale, ih * scale
    ix = area_x + (max_w - dw) / 2
    iy = area_y + (max_h - dh) / 2
    return fitz.Rect(ix, iy, ix + dw, iy + dh)


def render_map_highlighted(pdf_path, all_species, highlight_codes, color_map, plant_type):
    """Render PDF map with highlighted species only."""
    doc = fitz.open(pdf_path)
    page = doc[0]
    page_w, page_h = page.rect.width, page.rect.height

    # Fade background
    shape = page.new_shape()
    shape.draw_rect(page.rect)
    shape.finish(color=None, fill=C_WHITE, fill_opacity=0.82)
    shape.commit()

    if plant_type == "forracao":
        for label in highlight_codes:
            if label not in all_species:
                continue
            info = all_species[label]
            rgb = hex_to_rgb(color_map[label])
            for path_pts in info["paths"]:
                if len(path_pts) < 3:
                    continue
                shape = page.new_shape()
                shape.draw_polyline([fitz.Point(p[0], p[1]) for p in path_pts])
                shape.finish(color=None, fill=rgb, fill_opacity=0.6, closePath=True)
                shape.commit()
    else:
        radius = page_w * (0.0134 if plant_type == "arvore" else 0.006)
        for code in highlight_codes:
            if code not in all_species:
                continue
            positions = all_species[code]
            rgb = hex_to_rgb(color_map[code])
            for pos in positions:
                shape = page.new_shape()
                shape.draw_circle(fitz.Point(pos["x"], pos["y"]), radius)
                shape.finish(color=C_WHITE, fill=rgb, fill_opacity=0.75, width=2)
                shape.commit()

    pix = page.get_pixmap(dpi=72)
    doc.close()
    return pix, page_w, page_h


# ============================================================
# SLIDE BUILDERS
# ============================================================

def build_cover(doc, project_name, total_species, total_plants, type_counts):
    """Build a professional cover slide."""
    page = doc.new_page(width=SLIDE_W, height=SLIDE_H)

    # Background gradient effect - dark top bar
    page.draw_rect(fitz.Rect(0, 0, SLIDE_W, SLIDE_H), color=None, fill=C_WHITE)
    page.draw_rect(fitz.Rect(0, 0, SLIDE_W, 220), color=None, fill=C_DARK)

    # Accent stripe
    page.draw_rect(fitz.Rect(0, 220, SLIDE_W, 226), color=None, fill=C_ACCENT)

    # Title
    page.insert_text(fitz.Point(60, 90), "LEGENDA DE ESPECIES",
                     fontname="helv", fontsize=28, color=C_WHITE)
    page.insert_text(fitz.Point(60, 120), "IMPLANTACAO DE VEGETACAO",
                     fontname="helv", fontsize=14, color=(0.6, 0.7, 0.65))

    # Project name
    page.insert_text(fitz.Point(60, 170), project_name,
                     fontname="helv", fontsize=11, color=(0.5, 0.55, 0.52))

    # Date
    page.insert_text(fitz.Point(60, 195), "Abril 2026",
                     fontname="helv", fontsize=10, color=(0.45, 0.5, 0.48))

    # Stats cards
    card_y = 270
    card_h = 110
    card_gap = 20
    cards = [
        (str(total_species), "Especies", C_ACCENT),
        (str(total_plants), "Plantas / Areas", (0.13, 0.39, 0.67)),
        (str(len(type_counts)), "Categorias", (0.55, 0.27, 0.52)),
    ]
    card_w = (SLIDE_W - 120 - card_gap * (len(cards) - 1)) / len(cards)

    for i, (num, label, color) in enumerate(cards):
        cx = 60 + i * (card_w + card_gap)
        # Card background
        page.draw_rect(fitz.Rect(cx, card_y, cx + card_w, card_y + card_h),
                       color=None, fill=(0.98, 0.98, 0.98))
        # Top accent
        page.draw_rect(fitz.Rect(cx, card_y, cx + card_w, card_y + 4),
                       color=None, fill=color)
        # Number
        tw = fitz.get_text_length(num, fontname="helv", fontsize=36)
        page.insert_text(fitz.Point(cx + (card_w - tw) / 2, card_y + 55),
                         num, fontname="helv", fontsize=36, color=color)
        # Label
        tw = fitz.get_text_length(label, fontname="helv", fontsize=10)
        page.insert_text(fitz.Point(cx + (card_w - tw) / 2, card_y + 80),
                         label, fontname="helv", fontsize=10, color=C_MID)

    # Type breakdown
    by = 420
    page.insert_text(fitz.Point(60, by), "COMPOSICAO",
                     fontname="helv", fontsize=10, color=C_LIGHT)
    page.draw_line(fitz.Point(60, by + 6), fitz.Point(SLIDE_W - 60, by + 6),
                   color=C_LINE, width=0.5)
    by += 30
    for tname, tdata in type_counts.items():
        label = TYPE_LABELS.get(tname, tname)
        page.insert_text(fitz.Point(80, by), label,
                         fontname="helv", fontsize=11, color=C_DARK)
        count_text = f"{tdata['species']} especies  |  {tdata['items']} itens"
        page.insert_text(fitz.Point(300, by), count_text,
                         fontname="helv", fontsize=10, color=C_MID)
        by += 24

    # Footer
    page.draw_line(fitz.Point(60, SLIDE_H - 30), fitz.Point(SLIDE_W - 60, SLIDE_H - 30),
                   color=C_LINE, width=0.5)
    page.insert_text(fitz.Point(60, SLIDE_H - 16),
                     "Escritorio Benedito Abbud  |  Paisagismo Tecnico",
                     fontname="helv", fontsize=7, color=C_LIGHT)


def build_type_divider(doc, type_name, type_data, slide_count, species_db):
    """Build a divider slide for a vegetation type section."""
    page = doc.new_page(width=SLIDE_W, height=SLIDE_H)
    page.draw_rect(fitz.Rect(0, 0, SLIDE_W, SLIDE_H), color=None, fill=C_WHITE)

    label = TYPE_LABELS.get(type_name, type_name)

    # Left accent bar
    page.draw_rect(fitz.Rect(0, 0, 8, SLIDE_H), color=None, fill=C_ACCENT)

    # Section title
    page.insert_text(fitz.Point(60, 100), label.upper(),
                     fontname="helv", fontsize=32, color=C_DARK)

    # Stats line
    page.insert_text(fitz.Point(60, 135),
                     f"{type_data['species']} especies  |  {type_data['items']} itens  |  {slide_count} slides",
                     fontname="helv", fontsize=12, color=C_MID)

    page.draw_line(fitz.Point(60, 155), fitz.Point(400, 155),
                   color=C_ACCENT, width=2)

    # Species list preview (compact, 2 columns)
    entries = type_data["entries"]
    col_w = 480
    cols = 2
    items_per_col = (len(entries) + cols - 1) // cols
    start_y = 190

    for i, entry in enumerate(entries):
        col = i // items_per_col
        row = i % items_per_col
        x = 60 + col * col_w
        y = start_y + row * 18

        if y > SLIDE_H - 50:
            break

        rgb = hex_to_rgb(entry["color"])
        page.draw_circle(fitz.Point(x + 5, y - 3), 4, color=None, fill=rgb)
        page.insert_text(fitz.Point(x + 16, y),
                         entry["code"], fontname="helv", fontsize=8, color=C_DARK)

        sci = entry.get("scientific", "")
        if len(sci) > 30:
            sci = sci[:28] + ".."
        page.insert_text(fitz.Point(x + 60, y),
                         sci, fontname="helv", fontsize=7, color=C_MID)

    # Footer
    page.draw_line(fitz.Point(60, SLIDE_H - 30), fitz.Point(SLIDE_W - 60, SLIDE_H - 30),
                   color=C_LINE, width=0.5)


def build_species_slide(doc, entries, all_species, color_map, pdf_path, plant_type,
                        slide_num, total_slides, section_label):
    """Build a species slide with map + photos (reference-style layout)."""
    page = doc.new_page(width=SLIDE_W, height=SLIDE_H)
    page.draw_rect(fitz.Rect(0, 0, SLIDE_W, SLIDE_H), color=None, fill=C_WHITE)

    highlight_codes = [e["code"] for e in entries]

    # --- Thin header ---
    page.draw_rect(fitz.Rect(0, 0, SLIDE_W, 36), color=None, fill=(0.96, 0.96, 0.96))
    page.draw_line(fitz.Point(0, 36), fitz.Point(SLIDE_W, 36), color=C_LINE, width=0.5)

    page.insert_text(fitz.Point(16, 24), section_label,
                     fontname="helv", fontsize=9, color=C_DARK)
    counter = f"{slide_num}/{total_slides}"
    tw = fitz.get_text_length(counter, fontname="helv", fontsize=9)
    page.insert_text(fitz.Point(SLIDE_W - 16 - tw, 24), counter,
                     fontname="helv", fontsize=9, color=C_LIGHT)

    content_top = 44
    content_h = SLIDE_H - content_top - 16

    # --- LEFT: Map (55% width) ---
    map_w_ratio = 0.55
    map_area_w = SLIDE_W * map_w_ratio
    right_x = map_area_w + 8

    map_pix, page_w, page_h = render_map_highlighted(
        pdf_path, all_species, highlight_codes, color_map, plant_type
    )

    map_max_w = map_area_w - 24
    map_max_h = content_h - 8
    map_ratio = map_pix.width / max(map_pix.height, 1)
    map_disp_w = map_max_w
    map_disp_h = map_disp_w / map_ratio
    if map_disp_h > map_max_h:
        map_disp_h = map_max_h
        map_disp_w = map_disp_h * map_ratio

    map_x = 12 + (map_area_w - 24 - map_disp_w) / 2
    map_y = content_top + (content_h - map_disp_h) / 2
    map_rect = fitz.Rect(map_x, map_y, map_x + map_disp_w, map_y + map_disp_h)

    # Map shadow/border
    page.draw_rect(fitz.Rect(map_rect.x0 - 1, map_rect.y0 - 1,
                              map_rect.x1 + 1, map_rect.y1 + 1),
                   color=(0.82, 0.82, 0.82), width=0.5)
    page.insert_image(map_rect, pixmap=map_pix)

    # --- Legend overlay on map (bottom-left) ---
    leg_x = map_rect.x0 + 6
    leg_y = map_rect.y1 - len(entries) * 14 - 10
    # Semi-transparent background for legend
    leg_bg = fitz.Rect(leg_x - 4, leg_y - 6,
                        leg_x + 160, map_rect.y1 - 2)
    page.draw_rect(leg_bg, color=None, fill=C_WHITE, fill_opacity=0.85)

    for i, entry in enumerate(entries):
        ly = leg_y + i * 14
        rgb = hex_to_rgb(entry["color"])
        page.draw_circle(fitz.Point(leg_x + 5, ly + 3), 4, color=None, fill=rgb)
        page.insert_text(fitz.Point(leg_x + 14, ly + 6),
                         entry["code"], fontname="helv", fontsize=7, color=C_DARK)
        page.insert_text(fitz.Point(leg_x + 52, ly + 6),
                         f"{entry['count']} un.", fontname="helv", fontsize=6, color=C_MID)

    # --- RIGHT: Photos + info ---
    right_w = SLIDE_W - right_x - 12
    n = len(entries)
    slot_h = content_h / max(n, 1)
    photo_max_h = slot_h - 28  # leave space for label
    photo_max_w = right_w - 8

    for i, entry in enumerate(entries):
        slot_y = content_top + i * slot_h
        rgb = hex_to_rgb(entry["color"])

        if entry.get("image_path") and os.path.exists(entry["image_path"]):
            try:
                img_rect = fit_image_rect(entry["image_path"],
                                          right_x + 4, slot_y + 2,
                                          photo_max_w, photo_max_h)
                # Colored border around photo
                border = fitz.Rect(img_rect.x0 - 2, img_rect.y0 - 2,
                                   img_rect.x1 + 2, img_rect.y1 + 2)
                page.draw_rect(border, color=rgb, width=2)
                page.insert_image(img_rect, filename=entry["image_path"])

                # Name label below photo (centered, with colored background)
                common = entry.get("common", "") or entry.get("scientific", "") or entry["code"]
                if len(common) > 25:
                    common = common[:23] + ".."
                label_text = common.upper()
                ltw = fitz.get_text_length(label_text, fontname="helv", fontsize=8)
                label_x = img_rect.x0 + (img_rect.width - ltw) / 2 - 4
                label_y = img_rect.y1 + 4
                # Label background bar
                label_bg = fitz.Rect(img_rect.x0 - 2, label_y - 1,
                                     img_rect.x1 + 2, label_y + 12)
                page.draw_rect(label_bg, color=None, fill=rgb)
                page.insert_text(fitz.Point(label_x + 4, label_y + 9),
                                 label_text, fontname="helv", fontsize=8, color=C_WHITE)
            except Exception as e:
                print(f"  Warning: image error for {entry['code']}: {e}")
        else:
            # No image - show code + info card
            card_rect = fitz.Rect(right_x + 8, slot_y + 4,
                                  right_x + right_w - 8, slot_y + slot_h - 8)
            page.draw_rect(card_rect, color=C_LINE, fill=(0.99, 0.99, 0.99), width=0.5)
            page.draw_rect(fitz.Rect(card_rect.x0, card_rect.y0,
                                     card_rect.x0 + 4, card_rect.y1),
                           color=None, fill=rgb)
            cy = card_rect.y0 + 18
            page.insert_text(fitz.Point(card_rect.x0 + 14, cy),
                             entry["code"], fontname="helv", fontsize=12, color=C_DARK)
            if entry.get("scientific"):
                cy += 16
                page.insert_text(fitz.Point(card_rect.x0 + 14, cy),
                                 entry["scientific"], fontname="helv", fontsize=9, color=C_MID)
            if entry.get("common"):
                cy += 13
                page.insert_text(fitz.Point(card_rect.x0 + 14, cy),
                                 entry["common"], fontname="helv", fontsize=8, color=C_LIGHT)


def extract_all_types(species_db):
    """Extract species data from all 3 vegetation PDFs."""
    all_data = {}

    for plant_type, pdf_path in TYPE_PDFS.items():
        if not os.path.exists(pdf_path):
            print(f"  Skipping {plant_type}: PDF not found")
            continue

        doc = fitz.open(pdf_path)
        page = doc[0]

        if plant_type == "forracao":
            raw = extract_ground_cover_areas(page)
            color_map = assign_colors(raw, "forracao")
            entries = []
            for label in sorted(raw.keys()):
                info = raw[label]
                codes = label.replace("(", "").replace(")", "").split("+")
                first_code = codes[0].strip().split()[0] if codes else label
                db = species_db.get(first_code, {})
                entries.append({
                    "code": label,
                    "color": color_map[label],
                    "count": len(info["paths"]),
                    "scientific": db.get("scientific_name", ""),
                    "common": db.get("common_name", ""),
                    "origin": db.get("origin", ""),
                    "sun": db.get("sun_exposure", ""),
                    "image_path": find_image(first_code),
                })
            all_data[plant_type] = {
                "entries": entries,
                "raw": raw,
                "color_map": color_map,
                "pdf_path": pdf_path,
                "species": len(entries),
                "items": sum(e["count"] for e in entries),
            }
        elif plant_type == "arbusto":
            raw = extract_shrub_positions(page)
            color_map = assign_colors(raw, "arbusto")
            entries = []
            for code in sorted(raw.keys()):
                db = species_db.get(code, {})
                entries.append({
                    "code": code,
                    "color": color_map[code],
                    "count": len(raw[code]),
                    "scientific": db.get("scientific_name", ""),
                    "common": db.get("common_name", ""),
                    "origin": db.get("origin", ""),
                    "sun": db.get("sun_exposure", ""),
                    "image_path": find_image(code),
                })
            all_data[plant_type] = {
                "entries": entries,
                "raw": raw,
                "color_map": color_map,
                "pdf_path": pdf_path,
                "species": len(entries),
                "items": sum(e["count"] for e in entries),
            }
        else:  # arvore
            raw = extract_positions(page, "arvore")
            color_map = assign_colors(raw, "arvore")
            entries = []
            for code in sorted(raw.keys()):
                db = species_db.get(code, {})
                entries.append({
                    "code": code,
                    "color": color_map[code],
                    "count": len(raw[code]),
                    "scientific": db.get("scientific_name", ""),
                    "common": db.get("common_name", ""),
                    "origin": db.get("origin", ""),
                    "sun": db.get("sun_exposure", ""),
                    "image_path": find_image(code),
                })
            all_data[plant_type] = {
                "entries": entries,
                "raw": raw,
                "color_map": color_map,
                "pdf_path": pdf_path,
                "species": len(entries),
                "items": sum(e["count"] for e in entries),
            }

        doc.close()
        with_img = sum(1 for e in entries if e["image_path"])
        print(f"  {plant_type}: {len(entries)} especies, {sum(e['count'] for e in entries)} itens, {with_img} fotos")

    return all_data


def main():
    print("=== Geracao de Apresentacao Executiva ===\n")

    # 1. Load species DB
    print("1. Carregando banco de especies...")
    species_db = get_species_database()
    print(f"   {len(species_db)} especies no banco\n")

    # 2. Extract all types
    print("2. Extraindo dados dos 3 PDFs...")
    all_data = extract_all_types(species_db)

    if not all_data:
        print("   Nenhum dado extraido!")
        return

    # 3. Calculate totals
    total_species = sum(d["species"] for d in all_data.values())
    total_items = sum(d["items"] for d in all_data.values())
    print(f"\n   Total: {total_species} especies, {total_items} itens\n")

    # 4. Generate PDF
    print("3. Gerando apresentacao...")
    out_doc = fitz.open()
    global_slide = 0

    # Calculate total slides
    total_slides = 2  # cover + summary are not counted in species slides
    for tname, tdata in all_data.items():
        n_entries = len(tdata["entries"])
        n_slides = (n_entries + SPECIES_PER_SLIDE - 1) // SPECIES_PER_SLIDE
        total_slides += 1 + n_slides  # divider + species slides

    # --- COVER ---
    print("   Slide CAPA")
    build_cover(out_doc, "PINI - Projeto de Paisagismo",
                total_species, total_items, all_data)

    # --- For each type: divider + species slides ---
    running_slide = 1
    for tname in ["arvore", "arbusto", "forracao"]:
        if tname not in all_data:
            continue
        tdata = all_data[tname]
        entries = tdata["entries"]
        n_slides = (len(entries) + SPECIES_PER_SLIDE - 1) // SPECIES_PER_SLIDE

        # Divider
        print(f"   Slide DIVISOR: {TYPE_LABELS.get(tname, tname)}")
        build_type_divider(out_doc, tname, tdata, n_slides, species_db)
        running_slide += 1

        # Species slides
        for s in range(n_slides):
            start = s * SPECIES_PER_SLIDE
            chunk = entries[start:start + SPECIES_PER_SLIDE]
            running_slide += 1
            codes_str = ", ".join(e["code"] for e in chunk)
            print(f"   Slide {running_slide}: {codes_str}")

            section_label = (
                f"{TYPE_LABELS.get(tname, tname)}  |  "
                f"Especies {start + 1}-{start + len(chunk)} de {len(entries)}"
            )

            build_species_slide(
                out_doc, chunk, tdata["raw"], tdata["color_map"],
                tdata["pdf_path"], tname,
                running_slide, total_slides, section_label
            )

    # Save
    out_doc.save(OUTPUT)
    out_doc.close()
    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"\n=== Apresentacao gerada: {OUTPUT} ({size_kb:.0f} KB, {running_slide} slides) ===")


if __name__ == "__main__":
    main()
