#!/usr/bin/env python3
"""
Test script: generates a species slides presentation from an existing PDF.
Uses the extraction pipeline + species database + image assets.
"""

import os
import sys
import json
import math

import fitz  # PyMuPDF

sys.path.insert(0, os.path.dirname(__file__))
from api.extraction import (
    SPECIES, extract_positions, extract_shrub_positions,
    extract_ground_cover_areas, assign_colors, COLOR_PALETTE,
)
from api.species import get_species_database

# --- Config ---
BASE_DIR = os.path.dirname(__file__)
PDF_ARVORES = os.path.join(BASE_DIR, "arquivos", "PINI-PSG-PE-0504-LAZ-R00_IA_arvores.pdf")
IMG_DIR = os.path.join(BASE_DIR, "especies_img")
OUTPUT = os.path.join(BASE_DIR, "teste_apresentacao_arvores.pdf")

SLIDE_W = 1120
SLIDE_H = 630
SPECIES_PER_SLIDE = 5


def hex_to_rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def render_base_map(pdf_path, dpi=72):
    """Render the PDF page as a grayscale pixmap for background."""
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi)
    # Convert to grayscale with low opacity
    for i in range(pix.width * pix.height):
        offset = i * pix.n
        r, g, b = pix.samples[offset], pix.samples[offset + 1], pix.samples[offset + 2]
        gray = int(0.299 * r + 0.587 * g + 0.114 * b)
        faded = int(255 * 0.8 + gray * 0.2)
        pix.samples[offset] = faded
        pix.samples[offset + 1] = faded
        pix.samples[offset + 2] = faded
    doc.close()
    return pix


def render_highlighted_map(pdf_path, species_data, highlight_codes, color_map, page_w, page_h, dpi=72):
    """Render base map with only highlighted species circles drawn on it."""
    doc = fitz.open(pdf_path)
    page = doc[0]

    # Draw directly on the PDF page, then render
    # First, cover everything with a semi-transparent white rect for fade
    shape = page.new_shape()
    shape.draw_rect(page.rect)
    shape.finish(color=None, fill=(1, 1, 1), fill_opacity=0.8)
    shape.commit()

    # Draw circles for highlighted species
    radius = page_w * 0.0134

    for code in highlight_codes:
        if code not in species_data:
            continue
        positions = species_data[code]
        rgb = hex_to_rgb(color_map[code])
        for pos in positions:
            cx = pos["x"]
            cy = pos["y"]
            shape = page.new_shape()
            shape.draw_circle(fitz.Point(cx, cy), radius)
            shape.finish(
                color=(1, 1, 1),
                fill=rgb,
                fill_opacity=0.75,
                width=2,
            )
            shape.commit()

    # Render to pixmap
    result_pix = page.get_pixmap(dpi=dpi)
    doc.close()
    return result_pix


def build_slide(doc, page_idx, entries, species_data, color_map, species_db,
                pdf_path, page_w, page_h, total_entries, total_slides):
    """Build a single slide page in the output PDF."""
    page = doc.new_page(width=SLIDE_W, height=SLIDE_H)
    slide_num = page_idx + 1
    start_num = page_idx * SPECIES_PER_SLIDE + 1
    end_num = start_num + len(entries) - 1

    # --- White background ---
    page.draw_rect(page.rect, color=None, fill=(1, 1, 1))

    # --- Header bar ---
    header_rect = fitz.Rect(0, 0, SLIDE_W, 48)
    page.draw_rect(header_rect, color=None, fill=(0.96, 0.96, 0.96))
    page.draw_line(fitz.Point(0, 48), fitz.Point(SLIDE_W, 48),
                   color=(0.86, 0.86, 0.86), width=0.5)

    page.insert_text(fitz.Point(24, 32), "IMPLANTACAO DE VEGETACAO",
                     fontname="helv", fontsize=14, color=(0.13, 0.13, 0.13))
    page.insert_text(fitz.Point(24, 44),
                     f"Implantacao de Arvores  |  Especies {start_num}-{end_num} de {total_entries}",
                     fontname="helv", fontsize=9, color=(0.5, 0.5, 0.5))

    # Slide counter (right aligned)
    counter_text = f"Slide {slide_num}/{total_slides}"
    tw = fitz.get_text_length(counter_text, fontname="helv", fontsize=9)
    page.insert_text(fitz.Point(SLIDE_W - 24 - tw, 32), counter_text,
                     fontname="helv", fontsize=9, color=(0.63, 0.63, 0.63))

    # --- Layout ---
    content_top = 60
    content_h = SLIDE_H - content_top - 30
    highlight_codes = [e["code"] for e in entries]
    has_images = any(e.get("image_path") for e in entries)

    if has_images:
        map_area_w = SLIDE_W * 0.40
        list_area_x = map_area_w + 12
        list_area_w = SLIDE_W * 0.28
        img_area_x = list_area_x + list_area_w + 8
        img_area_w = SLIDE_W - img_area_x - 16
    else:
        map_area_w = SLIDE_W * 0.52
        list_area_x = map_area_w + 16
        list_area_w = SLIDE_W - list_area_x - 24
        img_area_x = 0
        img_area_w = 0

    # --- Render highlighted map ---
    map_pix = render_highlighted_map(
        pdf_path, species_data, highlight_codes, color_map, page_w, page_h
    )

    map_disp_w = map_area_w - 32
    map_disp_h = map_disp_w * (map_pix.height / map_pix.width)
    if map_disp_h > content_h:
        map_disp_h = content_h
        map_disp_w = map_disp_h * (map_pix.width / map_pix.height)
    map_x = 16 + (map_area_w - 32 - map_disp_w) / 2
    map_y = content_top + (content_h - map_disp_h) / 2

    map_rect = fitz.Rect(map_x, map_y, map_x + map_disp_w, map_y + map_disp_h)
    page.draw_rect(fitz.Rect(map_x - 2, map_y - 2, map_x + map_disp_w + 2, map_y + map_disp_h + 2),
                   color=(0.78, 0.78, 0.78), width=0.5)
    page.insert_image(map_rect, pixmap=map_pix)

    # --- Species list ---
    list_y = content_top + 8
    entry_height = min(100, (content_h - 28) / max(len(entries), 1))

    page.insert_text(fitz.Point(list_area_x, list_y + 10), "ESPECIES",
                     fontname="helv", fontsize=10, color=(0.24, 0.24, 0.24))
    list_y += 20

    for e_idx, entry in enumerate(entries):
        ey = list_y + e_idx * entry_height
        rgb = hex_to_rgb(entry["color"])

        # Color stripe
        page.draw_rect(fitz.Rect(list_area_x, ey - 2, list_area_x + 4, ey + entry_height - 12),
                       color=None, fill=rgb)

        # Color circle
        page.draw_circle(fitz.Point(list_area_x + 18, ey + 7), 6,
                         color=(1, 1, 1), fill=rgb, width=1)

        text_x = list_area_x + 30
        line_y = ey

        # Code
        page.insert_text(fitz.Point(text_x, line_y + 10), entry["code"],
                         fontname="helv", fontsize=10, color=(0.13, 0.13, 0.13))

        # Count badge
        count_text = f"{entry['count']} un."
        code_w = fitz.get_text_length(entry["code"], fontname="helv", fontsize=10)
        badge_w = fitz.get_text_length(count_text, fontname="helv", fontsize=7) + 8
        badge_rect = fitz.Rect(text_x + code_w + 6, line_y + 1, text_x + code_w + 6 + badge_w, line_y + 12)
        page.draw_rect(badge_rect, color=None, fill=rgb)
        page.insert_text(fitz.Point(badge_rect.x0 + 4, line_y + 9.5), count_text,
                         fontname="helv", fontsize=7, color=(1, 1, 1))

        line_y += 15

        # Scientific name
        if entry.get("scientific"):
            sci_text = entry["scientific"]
            if len(sci_text) > 38:
                sci_text = sci_text[:36] + "..."
            page.insert_text(fitz.Point(text_x, line_y + 4), sci_text,
                             fontname="helv", fontsize=8, color=(0.31, 0.31, 0.31))
            line_y += 11

        # Common name
        if entry.get("common"):
            page.insert_text(fitz.Point(text_x, line_y + 4), entry["common"],
                             fontname="helv", fontsize=7, color=(0.47, 0.47, 0.47))
            line_y += 10

        # Origin + sun
        meta = []
        if entry.get("origin"):
            meta.append(entry["origin"])
        if entry.get("sun"):
            meta.append(entry["sun"])
        if meta:
            page.insert_text(fitz.Point(text_x, line_y + 3), " | ".join(meta),
                             fontname="helv", fontsize=6, color=(0.63, 0.63, 0.63))

        # Separator
        if e_idx < len(entries) - 1:
            sep_y = ey + entry_height - 8
            page.draw_line(fitz.Point(list_area_x + 10, sep_y),
                           fitz.Point(list_area_x + list_area_w - 4, sep_y),
                           color=(0.92, 0.92, 0.92), width=0.3)

    # --- Species images (right column) ---
    if has_images:
        page.insert_text(fitz.Point(img_area_x, content_top + 8 + 10), "FOTOS",
                         fontname="helv", fontsize=10, color=(0.24, 0.24, 0.24))

        img_slot_h = (content_h - 28) / max(len(entries), 1)
        img_max_w = img_area_w - 8
        img_max_h = img_slot_h - 20

        for e_idx, entry in enumerate(entries):
            slot_y = content_top + 28 + e_idx * img_slot_h

            if entry.get("image_path") and os.path.exists(entry["image_path"]):
                try:
                    img_rect_fit = _fit_image(entry["image_path"], img_area_x, slot_y, img_max_w, img_max_h)
                    # Border
                    page.draw_rect(fitz.Rect(img_rect_fit.x0 - 1, img_rect_fit.y0 - 1,
                                             img_rect_fit.x1 + 1, img_rect_fit.y1 + 1),
                                   color=(0.86, 0.86, 0.86), width=0.5)
                    page.insert_image(img_rect_fit, filename=entry["image_path"])

                    # Code label below
                    rgb = hex_to_rgb(entry["color"])
                    lw = fitz.get_text_length(entry["code"], fontname="helv", fontsize=7)
                    lx = img_rect_fit.x0 + (img_rect_fit.width - lw) / 2
                    page.insert_text(fitz.Point(lx, img_rect_fit.y1 + 10), entry["code"],
                                     fontname="helv", fontsize=7, color=rgb)
                except Exception as e:
                    print(f"  Warning: could not insert image for {entry['code']}: {e}")
            else:
                # Placeholder
                ph_w = min(img_max_w, img_max_h * 0.8)
                ph_h = ph_w
                ph_x = img_area_x + (img_max_w - ph_w) / 2
                ph_y = slot_y + (img_max_h - ph_h) / 2
                page.draw_rect(fitz.Rect(ph_x, ph_y, ph_x + ph_w, ph_y + ph_h),
                               color=(0.9, 0.9, 0.9), width=0.3)
                tw = fitz.get_text_length("sem foto", fontname="helv", fontsize=7)
                page.insert_text(fitz.Point(ph_x + (ph_w - tw) / 2, ph_y + ph_h / 2 + 2),
                                 "sem foto", fontname="helv", fontsize=7, color=(0.78, 0.78, 0.78))

    # --- Footer ---
    page.draw_line(fitz.Point(24, SLIDE_H - 20), fitz.Point(SLIDE_W - 24, SLIDE_H - 20),
                   color=(0.86, 0.86, 0.86), width=0.5)
    footer = "Gerado por Mapa de Vegetacao - Paisagismo Tecnico"
    fw = fitz.get_text_length(footer, fontname="helv", fontsize=7)
    page.insert_text(fitz.Point((SLIDE_W - fw) / 2, SLIDE_H - 10), footer,
                     fontname="helv", fontsize=7, color=(0.7, 0.7, 0.7))


def _fit_image(path, area_x, area_y, max_w, max_h):
    """Calculate a proportional fit rect for an image."""
    img_doc = fitz.open(path)
    if img_doc.page_count > 0:
        p = img_doc[0]
        iw, ih = p.rect.width, p.rect.height
    else:
        iw, ih = 100, 100
    img_doc.close()

    # Fallback: read as image
    try:
        pix = fitz.Pixmap(path)
        iw, ih = pix.width, pix.height
    except:
        pass

    scale = min(max_w / max(iw, 1), max_h / max(ih, 1), 1)
    dw = iw * scale
    dh = ih * scale
    ix = area_x + (max_w - dw) / 2
    iy = area_y + (max_h - dh) / 2
    return fitz.Rect(ix, iy, ix + dw, iy + dh)


def main():
    print("=== Teste de Geracao de Slides ===\n")

    # 1. Load species database
    print("1. Carregando banco de especies...")
    species_db = get_species_database()
    print(f"   {len(species_db)} especies no banco")

    # 2. Extract positions from PDF
    print(f"2. Extraindo posicoes de arvores de {os.path.basename(PDF_ARVORES)}...")
    doc = fitz.open(PDF_ARVORES)
    page = doc[0]
    page_w = page.rect.width
    page_h = page.rect.height

    species_data = extract_positions(page, "arvore")
    color_map = assign_colors(species_data, "arvore")
    doc.close()

    total_plants = sum(len(v) for v in species_data.values())
    print(f"   {len(species_data)} especies detectadas, {total_plants} plantas no total")

    # 3. Build entries enriched with DB info
    print("3. Enriquecendo com dados do banco...")
    all_entries = []
    for code in sorted(species_data.keys()):
        positions = species_data[code]
        db_info = species_db.get(code, {})
        img_file = None
        # Check for image
        for ext in [".png", ".jpeg", ".jpg"]:
            candidate = os.path.join(IMG_DIR, code + ext)
            if os.path.exists(candidate):
                img_file = candidate
                break

        all_entries.append({
            "code": code,
            "color": color_map[code],
            "count": len(positions),
            "scientific": db_info.get("scientific_name", ""),
            "common": db_info.get("common_name", ""),
            "origin": db_info.get("origin", ""),
            "sun": db_info.get("sun_exposure", ""),
            "image_path": img_file,
        })

    with_img = sum(1 for e in all_entries if e["image_path"])
    print(f"   {len(all_entries)} especies, {with_img} com foto")

    for e in all_entries:
        img_status = "com foto" if e["image_path"] else "sem foto"
        print(f"   {e['code']:6s} | {e['scientific'][:35]:35s} | {e['count']:3d} un. | {img_status}")

    # 4. Group into slides
    slides = []
    for i in range(0, len(all_entries), SPECIES_PER_SLIDE):
        slides.append(all_entries[i:i + SPECIES_PER_SLIDE])

    total_slides = len(slides)
    print(f"\n4. Gerando {total_slides} slides...")

    # 5. Generate PDF
    out_doc = fitz.open()
    for s_idx, slide_entries in enumerate(slides):
        codes_str = ", ".join(e["code"] for e in slide_entries)
        print(f"   Slide {s_idx + 1}/{total_slides}: {codes_str}")
        build_slide(
            out_doc, s_idx, slide_entries, species_data, color_map, species_db,
            PDF_ARVORES, page_w, page_h, len(all_entries), total_slides
        )

    out_doc.save(OUTPUT)
    out_doc.close()

    file_size = os.path.getsize(OUTPUT) / 1024
    print(f"\n=== Apresentacao gerada: {OUTPUT} ({file_size:.0f} KB, {total_slides} slides) ===")


if __name__ == "__main__":
    main()
