"""
Vercel Python serverless function para extracao de dados de vegetacao de PDFs.
Recebe PDF + tipo via multipart form, retorna JSON com posicoes/areas extraidas.
"""

import json
import tempfile
import os
from http.server import BaseHTTPRequestHandler
import fitz  # PyMuPDF

try:
    from api.extraction import (
        SPECIES,
        extract_positions,
        extract_shrub_positions,
        extract_ground_cover_areas,
        assign_colors,
    )
except ImportError:
    from extraction import (
        SPECIES,
        extract_positions,
        extract_shrub_positions,
        extract_ground_cover_areas,
        assign_colors,
    )


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_type = self.headers.get("Content-Type", "")

            if "multipart/form-data" not in content_type:
                self._error(400, "Content-Type must be multipart/form-data")
                return

            # Parse multipart form data
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            boundary = content_type.split("boundary=")[1].strip()
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]

            parts = self._parse_multipart(body, boundary)

            pdf_data = parts.get("file")
            plant_type = parts.get("type", b"arvore").decode("utf-8") if isinstance(parts.get("type"), bytes) else parts.get("type", "arvore")

            if not pdf_data:
                self._error(400, "Missing 'file' field")
                return

            if plant_type not in ("arvore", "arbusto", "forracao"):
                self._error(400, f"Invalid type: {plant_type}. Must be arvore|arbusto|forracao")
                return

            # Save PDF to temp file and process
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_data)
                tmp_path = tmp.name

            try:
                doc = fitz.open(tmp_path)
                page = doc[0]

                page_width = page.rect.width
                page_height = page.rect.height

                if plant_type == "forracao":
                    data = extract_ground_cover_areas(page)
                    color_map = assign_colors(data, "forracao")

                    # Convert to JSON-serializable format
                    areas = {}
                    for label, area_info in data.items():
                        color = color_map[label]
                        paths = []
                        for path_points in area_info["paths"]:
                            paths.append([[round(p[0], 1), round(p[1], 1)] for p in path_points])
                        areas[label] = {
                            "color": color,
                            "paths": paths,
                        }

                    result = {
                        "type": "forracao",
                        "areas": areas,
                        "pageWidth": page_width,
                        "pageHeight": page_height,
                    }

                elif plant_type == "arbusto":
                    data = extract_shrub_positions(page)
                    color_map = assign_colors(data, "arbusto")

                    species = {}
                    for code, positions in data.items():
                        info = SPECIES.get(code, {})
                        species[code] = {
                            "positions": positions,
                            "color": color_map[code],
                            "name": info.get("name", code),
                            "common": info.get("common", ""),
                        }

                    result = {
                        "type": "arbusto",
                        "species": species,
                        "pageWidth": page_width,
                        "pageHeight": page_height,
                    }

                else:  # arvore
                    data = extract_positions(page, "arvore")
                    color_map = assign_colors(data, "arvore")

                    species = {}
                    for code, positions in data.items():
                        info = SPECIES.get(code, {})
                        species[code] = {
                            "positions": positions,
                            "color": color_map[code],
                            "name": info.get("name", code),
                            "common": info.get("common", ""),
                        }

                    result = {
                        "type": "arvore",
                        "species": species,
                        "pageWidth": page_width,
                        "pageHeight": page_height,
                    }

                doc.close()
            finally:
                os.unlink(tmp_path)

            self._json_response(200, result)

        except Exception as e:
            self._error(500, str(e))

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _parse_multipart(self, body, boundary):
        """Parse multipart form data manually."""
        parts = {}
        boundary_bytes = f"--{boundary}".encode()
        sections = body.split(boundary_bytes)

        for section in sections:
            if not section or section == b"--\r\n" or section == b"--":
                continue

            # Split headers from content
            if b"\r\n\r\n" in section:
                header_part, content = section.split(b"\r\n\r\n", 1)
            elif b"\n\n" in section:
                header_part, content = section.split(b"\n\n", 1)
            else:
                continue

            # Remove trailing \r\n
            if content.endswith(b"\r\n"):
                content = content[:-2]

            header_str = header_part.decode("utf-8", errors="replace")

            # Extract field name
            name = None
            if 'name="' in header_str:
                name = header_str.split('name="')[1].split('"')[0]

            if name:
                parts[name] = content

        return parts

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json_response(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, message):
        self._json_response(status, {"error": message})
