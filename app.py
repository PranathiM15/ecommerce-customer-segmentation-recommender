"""Local web server for the E-Commerce Customer Intelligence dashboard.

Run with: py app.py
Then open: http://127.0.0.1:8000
"""
from __future__ import annotations

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import os
import threading

from analytics import AnalyticsEngine, DataValidationError

BASE_DIR = Path(__file__).resolve().parent
DEMO_FILE = BASE_DIR / "online_retail_sample.csv"
UPLOAD_FILE = BASE_DIR / "uploaded_transactions.csv"
TEMP_UPLOAD = BASE_DIR / "upload_candidate.csv"
MAX_UPLOAD_BYTES = 80 * 1024 * 1024
ENGINE = None
ENGINE_LOCK = threading.RLock()


def initialize_engine() -> AnalyticsEngine:
    source = "Uploaded retail CSV" if UPLOAD_FILE.exists() else "Included demo dataset · synthetic sample"
    path = UPLOAD_FILE if UPLOAD_FILE.exists() else DEMO_FILE
    engine = AnalyticsEngine(path, source_label=source).run()
    return engine


def current_engine() -> AnalyticsEngine:
    global ENGINE
    with ENGINE_LOCK:
        if ENGINE is None:
            ENGINE = initialize_engine()
        return ENGINE


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format, *args):
        # Keep the terminal readable while still showing a compact request log.
        print(f"[{self.log_date_time_string()}] {format % args}")

    def send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_csv(self, content: str, filename: str):
        body = content.encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/api/health":
                self.send_json({"ok": True, "message": "Customer Intelligence server is running."})
                return
            if path == "/api/dashboard":
                self.send_json(current_engine().dashboard_payload())
                return
            if path == "/api/customers":
                limit = int(query.get("limit", ["250"])[0])
                search = query.get("search", [""])[0].strip()
                self.send_json({"customers": current_engine().customer_payload(limit=limit, search=search)})
                return
            if path == "/api/recommend":
                customer_id = query.get("customer", [""])[0].strip()
                if not customer_id:
                    self.send_json({"error": "Choose a customer to generate recommendations."}, 400)
                    return
                self.send_json(current_engine().recommendation_payload(customer_id))
                return
            if path == "/api/transactions":
                limit = int(query.get("limit", ["25"])[0])
                self.send_json({"transactions": current_engine().recent_transactions(limit=limit)})
                return
            if path.startswith("/api/export/"):
                kind = path.rsplit("/", 1)[-1].replace(".csv", "")
                names = {
                    "segments": "customer_segments.csv",
                    "profiles": "segment_profiles.csv",
                    "cleaned": "cleaned_transactions.csv",
                }
                if kind not in names:
                    self.send_json({"error": "Export not found."}, 404)
                    return
                self.send_csv(current_engine().export_csv(kind), names[kind])
                return
            if path == "/":
                self.path = "/index.html"
            return super().do_GET()
        except DataValidationError as exc:
            self.send_json({"error": str(exc)}, 422)
        except Exception as exc:
            self.send_json({"error": f"The request could not be completed: {exc}"}, 500)

    def do_POST(self):
        global ENGINE
        parsed = urlparse(self.path)
        if parsed.path != "/api/upload":
            self.send_json({"error": "Endpoint not found."}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                self.send_json({"error": "The uploaded file is empty."}, 400)
                return
            if length > MAX_UPLOAD_BYTES:
                self.send_json({"error": "The CSV is larger than the 80 MB upload limit."}, 413)
                return
            raw_body = self.rfile.read(length)
            try:
                csv_text = raw_body.decode("utf-8-sig")
            except UnicodeDecodeError:
                csv_text = raw_body.decode("latin-1")
            if not csv_text.strip():
                self.send_json({"error": "The uploaded CSV is empty."}, 400)
                return
            TEMP_UPLOAD.write_text(csv_text, encoding="utf-8-sig")

            # Validate and analyze the candidate before replacing the active dataset.
            source_label = "Uploaded retail CSV"
            candidate = AnalyticsEngine(TEMP_UPLOAD, source_label=source_label).run()
            os.replace(TEMP_UPLOAD, UPLOAD_FILE)
            candidate.data_path = UPLOAD_FILE
            with ENGINE_LOCK:
                ENGINE = candidate
            self.send_json({
                "ok": True,
                "message": "Dataset uploaded and analyzed successfully.",
                "dashboard": candidate.dashboard_payload(),
            })
        except DataValidationError as exc:
            TEMP_UPLOAD.unlink(missing_ok=True)
            self.send_json({"error": str(exc)}, 422)
        except Exception as exc:
            TEMP_UPLOAD.unlink(missing_ok=True)
            self.send_json({"error": f"Upload failed: {exc}"}, 500)


def main():
    global ENGINE
    print("\n  ORBIT / CUSTOMER INTELLIGENCE")
    print("  --------------------------------")
    print("  Preparing the customer dataset and K-Means model...")
    try:
        ENGINE = initialize_engine()
    except Exception as exc:
        print(f"\n  DATA ERROR: {exc}")
        print("  Check online_retail_sample.csv and try again. See README.md for help.\n")
        raise

    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"  Ready: http://127.0.0.1:{port}")
    print("  Press CTRL + C in this terminal to stop the server.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped. Your files are safe.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
