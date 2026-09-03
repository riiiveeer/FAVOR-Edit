"""Loopback-only cooperative blind review service with an explicit route allowlist."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field

from w1_pipeline.hashing import sha256_file

from .annotation_models import Answers, DraftAnswers, Strict
from .annotation_store import AnnotationStore, Conflict, presentation_for
from .ingest import _package_file


class SubmitRequest(Strict):
    view: str = Field(pattern=r"^[0-9a-f]{32}$")
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{16,80}$")
    answers: Answers


class DraftRequest(Strict):
    view: str = Field(pattern=r"^[0-9a-f]{32}$")
    revision: int = Field(ge=0)
    answers: DraftAnswers


class MediaState(Strict):
    view: str = Field(pattern=r"^[0-9a-f]{32}$")
    ready: bool


def byte_range(header: str, size: int) -> tuple:
    if header is None:
        return 0, size - 1, 200
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
    if match is None or size <= 0:
        raise ValueError("invalid range")
    first, last = match.groups()
    if not first:
        if not last or int(last) <= 0:
            raise ValueError("invalid suffix")
        start, end = max(0, size - int(last)), size - 1
    else:
        start, end = int(first), min(int(last), size - 1) if last else size - 1
    if start > end or start >= size:
        raise ValueError("unsatisfiable range")
    return start, end, 206


class AnnotationHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, store: AnnotationStore, port: int = 8765):
        self.store = store
        self.entry_token = secrets.token_urlsafe(32)
        self.cookie_token = secrets.token_urlsafe(32)
        self.cookie_name = "review_" + secrets.token_hex(12)
        self.csrf = secrets.token_urlsafe(32)
        self.prefix = f"/review/{secrets.token_hex(16)}/"
        self.entry_used = False
        self.html = Path(__file__).with_name("annotation_ui.html").read_bytes()
        self.html = self.html.replace(b"/* MEDIA_LOADER */", Path(__file__).with_name("annotation_playback.js").read_bytes())
        script = re.search(rb"<script>(.*?)</script>", self.html, flags=re.S).group(1)
        digest = base64.b64encode(hashlib.sha256(script).digest()).decode("ascii")
        self.csp = (f"default-src 'none'; script-src 'sha256-{digest}'; style-src 'unsafe-inline'; "
                    "media-src 'self' blob:; connect-src 'self'; img-src 'self' data:; "
                    "base-uri 'none'; frame-ancestors 'none'; object-src 'none'; form-action 'none'")
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"

    @property
    def entry_url(self):
        return f"{self.origin}/entry/{self.entry_token}"


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalReview"
    sys_version = ""

    def log_message(self, *_):
        # HTTP logs must never persist entry/session tokens or private file paths.
        pass

    def _headers(self, status, content_type, length, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", self.server.csp)
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def _json(self, payload, status=200, extra=None):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body), extra)
        if self.command != "HEAD":
            self.wfile.write(body)

    def _error(self, status, code):
        print(f"Local review: {status} {code}", flush=True)
        self._json({"error": code}, status)

    def send_error(self, code, message=None, explain=None):
        self._error(code, "request_rejected")

    def _gate(self, write=False):
        if self.headers.get("Host") != urlsplit(self.server.origin).netloc:
            self._error(403, "origin_rejected")
            return False
        origin = self.headers.get("Origin")
        if (write and origin != self.server.origin) or (origin and origin != self.server.origin):
            self._error(403, "origin_rejected")
            return False
        if self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
            self._error(403, "origin_rejected")
            return False
        return True

    def _authenticated(self, write=False):
        if not self._gate(write):
            return False
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            token = cookie[self.server.cookie_name].value if self.server.cookie_name in cookie else ""
        except Exception:
            token = ""
        if not secrets.compare_digest(token, self.server.cookie_token):
            self._error(403, "session_rejected")
            return False
        if write and not secrets.compare_digest(self.headers.get("X-Review-CSRF", ""), self.server.csrf):
            self._error(403, "session_rejected")
            return False
        return True

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            parsed = urlsplit(self.path)
            if parsed.query or parsed.fragment:
                return self._error(404, "not_found")
            path = parsed.path
            if path.startswith("/entry/") and self.command == "GET":
                if not self._gate():
                    return
                with self.server.store.mutex:
                    if self.server.entry_used or not secrets.compare_digest(path[7:], self.server.entry_token):
                        return self._error(403, "session_rejected")
                    self.server.entry_used = True
                self._headers(303, "text/plain", 0, {
                    "Location": self.server.prefix,
                    "Set-Cookie": f"{self.server.cookie_name}={self.server.cookie_token}; HttpOnly; SameSite=Strict; Path={self.server.prefix}",
                })
                return
            if not path.startswith(self.server.prefix):
                return self._error(404, "not_found")
            path = "/" + path[len(self.server.prefix):]
            if not self._authenticated():
                return
            if path == "/":
                self._headers(200, "text/html; charset=utf-8", len(self.server.html))
                if self.command != "HEAD":
                    self.wfile.write(self.server.html)
            elif path == "/api/current" and self.command == "GET":
                store = self.server.store
                with store.mutex:
                    view = store.open_view()
                    if view.get("complete"):
                        return self._json({"complete": True})
                    c = next(c for c in store.bundle["comparisons"] if c["comparison_id"] == view["comparison_id"])
                    draft = store.drafts.get(view["comparison_id"])
                    self._json({"complete": False, "view": view["handle"], "csrf": self.server.csrf,
                                "progress": {"position": view["position"], "total": len(store.mapping)},
                                "instruction": c["instruction"], "practice": store.session.mode == "practice",
                                "media": {r: f"{self.server.prefix}media/{view['handle']}/{r}" for r in ("source", "A", "B")},
                                "draft": draft.answers.model_dump() if draft else None,
                                "revision": draft.revision if draft else 0})
            else:
                match = re.fullmatch(r"/media/([0-9a-f]{32})/(source|A|B)", path)
                if match:
                    self._media(*match.groups())
                else:
                    self._error(404, "not_found")
        except Conflict:
            self._error(409, "stale_view")
        except (ConnectionError, BrokenPipeError):
            pass
        except Exception:
            self._error(422, "media_or_session_unavailable")

    def _media(self, handle, label):
        store = self.server.store
        with store.mutex:
            view = store.current_view(handle)
            side = "source" if label == "source" else "X" if label == view["x_as"] else "Y"
            ref = presentation_for(store.bundle, view["comparison_id"])[side]
            path = _package_file(Path(store.bundle["presentation_root"]), ref["relative_path"])
            if sha256_file(path) != ref["sha256"]:
                view["ready"] = False
                raise ValueError("media changed")
            size = path.stat().st_size
            try:
                start, end, status = byte_range(self.headers.get("Range"), size)
            except ValueError:
                return self._error(416, "invalid_range") if size == 0 else self._json(
                    {"error": "invalid_range"}, 416, {"Content-Range": f"bytes */{size}"})
            extra = {"Accept-Ranges": "bytes"}
            if status == 206:
                extra["Content-Range"] = f"bytes {start}-{end}/{size}"
            mime = "video/webm" if store.bundle["presentation_mode"] == "lossless-vp9-yuv420p-v1" else "video/mp4"
            self._headers(status, mime, end - start + 1, extra)
            if self.command == "HEAD":
                return
            view["media_served"].add(label)
        with path.open("rb") as stream:
            stream.seek(start)
            remaining = end - start + 1
            while remaining:
                block = stream.read(min(65536, remaining))
                if not block:
                    break
                self.wfile.write(block)
                remaining -= len(block)

    def do_POST(self):
        if not self.path.startswith(self.server.prefix):
            return self._error(404, "not_found")
        path = "/" + self.path[len(self.server.prefix):]
        if not self._authenticated(write=True):
            return
        try:
            if path not in ("/api/draft", "/api/submit", "/api/media-state"):
                return self._error(404, "not_found")
            if self.headers.get("Content-Type") != "application/json":
                return self._error(415, "json_required")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384 or self.headers.get("Transfer-Encoding"):
                return self._error(413, "invalid_body_size")
            raw = json.loads(self.rfile.read(length))
            store = self.server.store
            if path == "/api/draft":
                req = DraftRequest.model_validate(raw)
                revision = store.save_draft(req.view, req.answers.model_dump(), req.revision)
                self._json({"saved": "draft", "revision": revision})
            elif path == "/api/media-state":
                req = MediaState.model_validate(raw)
                with store.mutex:
                    view = store.current_view(req.view)
                    view["ready"] = req.ready and view["media_served"] == {"source", "A", "B"}
                self._json({"ready": view["ready"]})
            else:
                req = SubmitRequest.model_validate(raw)
                store.submit(req.view, req.answers.model_dump(), req.request_id)
                self._json({"saved": "confirmed"})
        except Conflict:
            self._error(409, "conflict_refresh_required")
        except OSError:
            self._error(503, "save_failed_retry_same_request")
        except Exception:
            self._error(422, "invalid_fields_or_media_not_ready")


def serve_annotation(bundle: Path, annotator: str, output: Path, resume: bool, port: int):
    with AnnotationStore(bundle, annotator, output, resume) as store:
        with AnnotationHTTPServer(store, port) as server:
            print("仅此评审使用；退出按 Ctrl+C，随后关闭页面。", flush=True)
            print(server.entry_url, flush=True)
            print("工作页面（需先打开上方入口）：" + server.origin + server.prefix, flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
