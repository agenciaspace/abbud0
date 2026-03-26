"""
Vercel Python serverless function para parsing de documentos com LlamaParse.
Recebe PDF via multipart form, retorna conteudo extraido em markdown.
"""

import json
import tempfile
import os
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

LLAMA_CLOUD_API_KEY = os.environ.get("LLAMA_CLOUD_API_KEY", "")
LLAMA_PARSE_BASE_URL = "https://api.cloud.llamaindex.ai/api/v1/parsing"


def _api_request(path, method="GET", data=None, headers=None, content_type=None):
    """Faz requisicao HTTP para a API do LlamaParse."""
    url = f"{LLAMA_PARSE_BASE_URL}{path}"
    hdrs = {"Authorization": f"Bearer {LLAMA_CLOUD_API_KEY}"}
    if headers:
        hdrs.update(headers)

    if data is not None:
        if content_type:
            hdrs["Content-Type"] = content_type
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        else:
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    else:
        req = urllib.request.Request(url, headers=hdrs, method=method)

    with urllib.request.urlopen(req, timeout=55) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _upload_and_parse(pdf_path, language="pt"):
    """Envia PDF para LlamaParse e aguarda resultado."""
    boundary = "----LlamaParseFormBoundary"
    filename = os.path.basename(pdf_path)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Build multipart form data
    parts = []

    # File part
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    parts.append(b"Content-Type: application/pdf\r\n\r\n")
    parts.append(pdf_bytes)
    parts.append(b"\r\n")

    # Language part
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="language"\r\n\r\n')
    parts.append(language.encode())
    parts.append(b"\r\n")

    # Parsing instruction
    parsing_instruction = (
        "Este e um documento de paisagismo/arquitetura paisagistica. "
        "Extraia todas as informacoes sobre especies de plantas, "
        "incluindo codigos (siglas), nomes cientificos, nomes populares, "
        "quantidades, e quaisquer tabelas ou legendas presentes. "
        "Mantenha a formatacao de tabelas em markdown."
    )
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="parsing_instruction"\r\n\r\n')
    parts.append(parsing_instruction.encode())
    parts.append(b"\r\n")

    parts.append(f"--{boundary}--\r\n".encode())

    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"

    # Upload and start parsing
    result = _api_request(
        "/upload",
        method="POST",
        data=body,
        content_type=content_type,
    )

    job_id = result.get("id")
    if not job_id:
        raise Exception(f"LlamaParse nao retornou job_id: {result}")

    # Poll for completion (max ~50s to stay within Vercel timeout)
    for _ in range(25):
        time.sleep(2)
        status = _api_request(f"/job/{job_id}")
        if status.get("status") == "SUCCESS":
            # Get markdown result
            md_result = _api_request(f"/job/{job_id}/result/markdown")
            return {
                "job_id": job_id,
                "status": "SUCCESS",
                "markdown": md_result.get("markdown", ""),
                "pages": md_result.get("pages", []),
            }
        elif status.get("status") == "ERROR":
            raise Exception(f"LlamaParse erro: {status.get('error', 'unknown')}")

    # Timeout - return job_id for async retrieval
    return {
        "job_id": job_id,
        "status": "PENDING",
        "markdown": "",
        "pages": [],
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            if not LLAMA_CLOUD_API_KEY:
                self._error(500, "LLAMA_CLOUD_API_KEY nao configurada")
                return

            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._error(400, "Content-Type must be multipart/form-data")
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            boundary = content_type.split("boundary=")[1].strip()
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]

            parts = self._parse_multipart(body, boundary)
            pdf_data = parts.get("file")

            if not pdf_data:
                self._error(400, "Missing 'file' field")
                return

            # Save PDF to temp file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_data)
                tmp_path = tmp.name

            try:
                result = _upload_and_parse(tmp_path)
            finally:
                os.unlink(tmp_path)

            self._json_response(200, result)

        except Exception as e:
            self._error(500, str(e))

    def do_GET(self):
        """GET /api/parse?job_id=xxx - verifica status de um job pendente."""
        try:
            if not LLAMA_CLOUD_API_KEY:
                self._error(500, "LLAMA_CLOUD_API_KEY nao configurada")
                return

            path = self.path
            job_id = None
            if "?" in path:
                query = path.split("?", 1)[1]
                for param in query.split("&"):
                    if param.startswith("job_id="):
                        job_id = param.split("=", 1)[1]

            if not job_id:
                self._error(400, "Missing job_id parameter")
                return

            status = _api_request(f"/job/{job_id}")
            if status.get("status") == "SUCCESS":
                md_result = _api_request(f"/job/{job_id}/result/markdown")
                self._json_response(200, {
                    "job_id": job_id,
                    "status": "SUCCESS",
                    "markdown": md_result.get("markdown", ""),
                    "pages": md_result.get("pages", []),
                })
            else:
                self._json_response(200, {
                    "job_id": job_id,
                    "status": status.get("status", "UNKNOWN"),
                    "markdown": "",
                    "pages": [],
                })

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

            if b"\r\n\r\n" in section:
                header_part, content = section.split(b"\r\n\r\n", 1)
            elif b"\n\n" in section:
                header_part, content = section.split(b"\n\n", 1)
            else:
                continue

            if content.endswith(b"\r\n"):
                content = content[:-2]

            header_str = header_part.decode("utf-8", errors="replace")

            name = None
            if 'name="' in header_str:
                name = header_str.split('name="')[1].split('"')[0]

            if name:
                parts[name] = content

        return parts

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
