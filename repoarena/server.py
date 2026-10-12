"""Dependency-free development server and streaming arena API."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .harness import ArenaError, CONTEXT, ISSUE, Ollama, run_arena

WEB = Path(__file__).resolve().parent.parent / "web"
SLOTS = threading.BoundedSemaphore(2)
MAX_BODY = 40000


class Handler(BaseHTTPRequestHandler):
    server_version = "RepoArena/1.0"

    def send_body_headers(self, status, content_type, length=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def json_response(self, status, data):
        body = json.dumps(data).encode()
        self.send_body_headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            self.json_response(200, {"status": "ok", "app": "RepoArena"})
        elif path == "/api/models":
            try:
                self.json_response(200, {"available": True, "models": Ollama().models()})
            except ArenaError as exc:
                self.json_response(200, {"available": False, "models": [], "error": str(exc)})
        elif path == "/api/example":
            self.json_response(200, {"issue": ISSUE, "context": CONTEXT})
        elif path in ("/", "/styles.css", "/theme.css", "/app.js", "/icon.svg"):
            name = "index.html" if path == "/" else path[1:]
            mime = {"html": "text/html", "css": "text/css", "js": "text/javascript", "svg": "image/svg+xml"}[name.rsplit(".", 1)[-1]]
            body = (WEB / name).read_bytes()
            self.send_body_headers(200, mime + "; charset=utf-8", len(body))
            self.wfile.write(body)
        else:
            self.json_response(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/arena":
            self.json_response(404, {"error": "Not found"})
            return
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            self.json_response(403, {"error": "Cross-origin requests are not allowed."})
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
            self.json_response(415, {"error": "Use application/json."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                self.json_response(413, {"error": "Request must be between 1 and 40,000 bytes."})
                return
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected an object.")
            mode = data.get("mode", "live")
            if mode not in ("live", "sample"):
                raise ValueError("Mode must be live or sample.")
            issue, context, model = data.get("issue", ""), data.get("context", ""), data.get("model", "")
            if mode == "live":
                if not isinstance(issue, str) or not 10 <= len(issue.strip()) <= 8000:
                    raise ValueError("Describe your issue in 10–8,000 characters.")
                if not isinstance(context, str) or len(context) > 16000:
                    raise ValueError("Context must be text under 16,000 characters.")
                if not isinstance(model, str) or not model.strip() or len(model) > 200:
                    raise ValueError("Select an installed Ollama model.")
                issue, model = issue.strip(), model.strip()
        except (ValueError, UnicodeError) as exc:
            self.json_response(400, {"error": str(exc)})
            return
        if not SLOTS.acquire(blocking=False):
            self.json_response(429, {"error": "Two arenas are already running. Wait for a run to finish."})
            return
        try:
            self.headers_response_stream()
            try:
                for event in run_arena(issue, context, model, sample=mode == "sample"):
                    self.write_event(event)
            except ArenaError as exc:
                self.write_event({"type": "error", "error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            SLOTS.release()

    def headers_response_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    def write_event(self, event):
        self.wfile.write((json.dumps(event) + "\n").encode())
        self.wfile.flush()

    def log_message(self, fmt, *args):
        # Do not log user prompts or model outputs.
        super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description="Run RepoArena with local Ollama")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"RepoArena listening on {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
