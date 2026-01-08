#!/usr/bin/env python3
import json
import os
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse


ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ROOT, "workflow.json")


class WorkflowHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        if self._is_api():
            self._handle_get()
            return
        super().do_GET()

    def do_POST(self):
        if self._is_api():
            self._handle_post()
            return
        self.send_error(404, "Not Found")

    def _is_api(self) -> bool:
        return urlparse(self.path).path == "/api/workflow"

    def _handle_get(self) -> None:
        if not os.path.exists(DATA_FILE):
            self.send_error(404, "No workflow.json yet")
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            self.send_error(500, "Failed to read workflow.json")
            return
        self._send_json(payload)

    def _handle_post(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        tasks = payload.get("tasks", [])
        edges = payload.get("edges", [])
        if not isinstance(tasks, list) or not isinstance(edges, list):
            self.send_error(400, "Invalid payload")
            return
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"tasks": tasks, "edges": edges}, f, indent=2)
        except OSError:
            self.send_error(500, "Failed to write workflow.json")
            return
        self.send_response(204)
        self.end_headers()

    def _send_json(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def open_browser(url: str) -> None:
    def _open() -> None:
        webbrowser.open(url, new=1, autoraise=True)

    threading.Timer(0.4, _open).start()


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    url = f"http://127.0.0.1:{port}/workflow.html"
    server = HTTPServer(("127.0.0.1", port), WorkflowHandler)
    print(f"Serving on {url}")
    if os.environ.get("NO_OPEN") != "1":
        open_browser(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
