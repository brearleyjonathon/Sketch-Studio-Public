"""
Local server for Sketch Styler.
Serves static files, proxies Replicate API calls, and converts HEIC images.
"""
import http.server
import urllib.request
import urllib.error
import json
import os
import io
import subprocess
import tempfile

PORT = 8741
REPLICATE_BASE = "https://api.replicate.com"
ANTHROPIC_BASE = "https://api.anthropic.com"


class Handler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # suppress request noise

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path.startswith("/proxy/"):
            self._proxy("POST")
        elif self.path == "/convert":
            self._convert_heic()
        elif self.path == "/anthropic":
            self._anthropic_proxy()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path.startswith("/proxy/"):
            self._proxy("GET")
        elif self.path.startswith("/fetch?"):
            self._fetch_image()
        elif self.path == "/list-refs":
            self._list_refs()
        else:
            super().do_GET()

    def _list_refs(self):
        refs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img_ref")
        exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
        files = []
        if os.path.isdir(refs_dir):
            files = sorted(
                f for f in os.listdir(refs_dir)
                if os.path.splitext(f)[1].lower() in exts
            )
        body = json.dumps({"files": files}).encode()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _fetch_image(self):
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query)
        url = qs.get("url", [""])[0]
        if not url:
            self.send_error(400)
            return
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                ct = resp.headers.get("Content-Type", "image/png")
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", ct)
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self._json_error(500, str(e))

    def _convert_heic(self):
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)

        errors = []

        # Approach 1: pillow-heif (cross-platform)
        try:
            import pillow_heif
            from PIL import Image
            pillow_heif.register_heif_opener()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=95)
            return self._send_jpeg(out.getvalue())
        except ImportError as e:
            errors.append(f"pillow-heif: not installed ({e})")
        except Exception as e:
            errors.append(f"pillow-heif: {type(e).__name__}: {e}")

        # Approach 2: Windows PowerShell + System.Drawing (uses WIC + HEIF codec)
        if os.name == "nt":
            jpeg = self._convert_via_powershell(data, errors)
            if jpeg is not None:
                return self._send_jpeg(jpeg)

        msg = (
            "HEIC conversion failed. Install pillow-heif (pip install pillow-heif) "
            "or, on Windows 11, install 'HEIF Image Extensions' from the Microsoft Store. "
            "Diagnostics: " + " | ".join(errors)
        )
        self._json_error(500, msg)

    def _convert_via_powershell(self, data, errors):
        heic_path = jpg_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".heic", delete=False) as f:
                f.write(data)
                heic_path = f.name
            jpg_path = heic_path + ".jpg"

            ps_in = heic_path.replace("\\", "/")
            ps_out = jpg_path.replace("\\", "/")
            ps_script = (
                "Add-Type -AssemblyName System.Drawing; "
                f"$img = [System.Drawing.Image]::FromFile('{ps_in}'); "
                f"$img.Save('{ps_out}', [System.Drawing.Imaging.ImageFormat]::Jpeg); "
                "$img.Dispose()"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and os.path.exists(jpg_path):
                with open(jpg_path, "rb") as f:
                    return f.read()
            errors.append(f"PowerShell: {(result.stderr or result.stdout or 'unknown').strip()[:300]}")
        except Exception as e:
            errors.append(f"PowerShell: {type(e).__name__}: {e}")
        finally:
            for p in (heic_path, jpg_path):
                if p and os.path.exists(p):
                    try: os.unlink(p)
                    except OSError: pass
        return None

    def _send_jpeg(self, jpeg):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "image/jpeg")
        self.end_headers()
        self.wfile.write(jpeg)

    def _json_error(self, code, msg):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")

    def _anthropic_proxy(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        api_key = self.headers.get("X-Api-Key", "")

        req = urllib.request.Request(
            ANTHROPIC_BASE + "/v1/messages",
            data=body,
            method="POST",
        )
        req.add_header("x-api-key", api_key)
        req.add_header("anthropic-version", "2023-06-01")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

    def _proxy(self, method):
        # Strip /proxy prefix, forward to Replicate
        target = REPLICATE_BASE + self.path[len("/proxy"):]

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None

        auth = self.headers.get("Authorization", "")

        req = urllib.request.Request(target, data=body, method=method)
        req.add_header("Authorization", auth)
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Sketch Styler running at http://127.0.0.1:{PORT}/sketch_styler.html")
        httpd.serve_forever()
