"""Kernel single-writer lock and immutable per-question annotation facts."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from w1_pipeline.hashing import canonical_sha256, sha256_file

from .annotation_bundle import load_bundle, now, read_json, source_evidence, stage
from .annotation_models import (
    ANNOTATORS, CONFIG, PROTOCOL, Annotation, Answers, Draft, DraftAnswers, Session, canonical_answers,
)
from .ingest import _package_file
from .io import rename_noreplace, write_json


class Conflict(ValueError):
    """Stale tab, immutable answer conflict, or held writer lock."""


class WriterLock:
    """The kernel, not PID age, decides whether a previous process is still alive."""

    def __init__(self, directory: Path):
        self.handle = (Path(directory) / "writer.lock").open("r+b")
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.handle.close()
            raise Conflict("another process holds the session") from exc
        if self.handle.read() != b"\0":
            self.close()
            raise ValueError("unknown or damaged writer lock")

    def close(self):
        if self.handle.closed:
            return
        self.handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def atomic_json(path: Path, payload: dict, replace: bool = False) -> None:
    path = Path(path)
    temporary = path.parent.parent / "pending" / f"{uuid.uuid4().hex}.json"
    write_json(temporary, payload)
    if replace:
        os.replace(temporary, path)
    else:
        rename_noreplace(temporary, path)


def media_for(bundle: dict, comparison_id: str) -> dict:
    c = next(c for c in bundle["comparisons"] if c["comparison_id"] == comparison_id)
    return {"source": c["source_video"], "X": c["candidate_x"]["video"], "Y": c["candidate_y"]["video"]}


def check_media(bundle: dict, comparison_id: str) -> None:
    for ref in media_for(bundle, comparison_id).values():
        if sha256_file(_package_file(Path(bundle["delivery_root"]), ref["relative_path"])) != ref["sha256"]:
            raise ValueError("media changed")
    for ref in presentation_for(bundle, comparison_id).values():
        if sha256_file(_package_file(Path(bundle["presentation_root"]), ref["relative_path"])) != ref["sha256"]:
            raise ValueError("presentation media changed")


def presentation_for(bundle: dict, comparison_id: str) -> dict:
    return {k: bundle["presentation_media"][v["relative_path"]] for k, v in media_for(bundle, comparison_id).items()}


def validate_session(bundle: dict, raw: dict) -> Session:
    session = Session.model_validate(raw)
    if (session.bundle_sha256 != bundle["sha256"] or session.protocol_sha256 != bundle["protocol_sha256"]
            or session.mode != bundle["mode"]):
        raise ValueError("session bundle/protocol/mode mismatch")
    if datetime.fromisoformat(session.created_at).utcoffset() is None:
        raise ValueError("session timestamp must have timezone")
    return session


def validate_record(bundle: dict, session: Session, raw: dict) -> Annotation:
    record = Annotation.model_validate(raw)
    for name in ("protocol", "mode", "session_id", "annotator_id", "bundle_sha256", "protocol_sha256"):
        if getattr(record, name) != getattr(session, name):
            raise ValueError("annotation session identity mismatch")
    if record.source != ("human" if session.mode == "formal" else "practice"):
        raise ValueError("annotation source mismatch")
    mapping = bundle["mapping"][session.annotator_id]
    if record.position > len(mapping):
        raise ValueError("annotation position invalid")
    display = mapping[record.position - 1]
    if record.comparison_id != display["comparison_id"] or record.x_as != display["x_as"]:
        raise ValueError("annotation direction/comparison mismatch")
    if record.canonical != canonical_answers(record.screen, record.x_as):
        raise ValueError("annotation canonical mismatch")
    if {k: v.model_dump() for k, v in record.media.items()} != media_for(bundle, record.comparison_id):
        raise ValueError("annotation media mismatch")
    if (record.presentation_mode != bundle["presentation_mode"]
            or {k: v.model_dump() for k, v in record.presentation_media.items()} != presentation_for(bundle, record.comparison_id)):
        raise ValueError("annotation presentation mismatch")
    if record.content_sha256 != canonical_sha256({"comparison_id": record.comparison_id, "answers": record.screen.model_dump()}):
        raise ValueError("annotation content hash mismatch")
    started, ended, created = (datetime.fromisoformat(s) for s in
                               (record.view_started_at, record.submitted_at, session.created_at))
    if any(t.utcoffset() is None for t in (started, ended, created)) or not created <= started <= ended:
        raise ValueError("annotation timestamps invalid")
    # Wall clock can move; a backwards adjustment is rejected before publication.
    if abs((ended - started).total_seconds() - record.current_view_elapsed_seconds) > 5:
        raise ValueError("annotation elapsed time inconsistent")
    return record


def load_records(bundle: dict, session: Session, directory: Path) -> list:
    paths = sorted((directory / "records").iterdir())
    result, requests = [], set()
    for i, path in enumerate(paths):
        if path.name != f"{i + 1:04}.json" or path.is_symlink() or not path.is_file():
            raise ValueError("non-contiguous or unexpected annotation file")
        record = validate_record(bundle, session, read_json(path))
        if record.position != i + 1 or record.request_id in requests:
            raise ValueError("duplicate record/request")
        requests.add(record.request_id)
        result.append(record)
    return result


def load_drafts(bundle: dict, session: Session, directory: Path) -> dict:
    result = {}
    mapping = {d["comparison_id"]: d for d in bundle["mapping"][session.annotator_id]}
    for path in sorted((directory / "drafts").iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("unexpected draft file")
        draft = Draft.model_validate(read_json(path))
        display = mapping.get(draft.comparison_id)
        if (draft.session_id != session.session_id or draft.bundle_sha256 != bundle["sha256"] or display is None
                or path.name != f"{display['position']:04}.json"):
            raise ValueError("draft identity mismatch")
        result[draft.comparison_id] = draft
    return result


class AnnotationStore:
    def __init__(self, bundle_path: Path, annotator: str, directory: Path, resume: bool = False):
        self.bundle = load_bundle(bundle_path)
        self.directory = Path(directory).resolve()
        self.mutex = threading.RLock()
        self.lock = None
        self.views = {}
        if annotator not in ANNOTATORS or self.directory.name != annotator:
            raise ValueError("session directory basename must match annotator ID")
        if not resume:
            staging = stage(self.directory)
            meta = Session(protocol=PROTOCOL, mode=self.bundle["mode"], annotator_id=annotator,
                           bundle_sha256=self.bundle["sha256"], protocol_sha256=self.bundle["protocol_sha256"],
                           session_id=uuid.uuid4().hex, created_at=now())
            write_json(staging / "session.json", meta.model_dump())
            for name in ("records", "drafts", "pending", "runs"):
                (staging / name).mkdir()
            with (staging / "writer.lock").open("xb") as h:
                h.write(b"\0")
                h.flush()
                os.fsync(h.fileno())
            rename_noreplace(staging, self.directory)
        elif not self.directory.is_dir():
            raise ValueError("resume requires an existing session")
        allowed = {"session.json", "records", "drafts", "pending", "runs", "writer.lock"}
        if {p.name for p in self.directory.iterdir()} != allowed or any(p.is_symlink() for p in self.directory.rglob("*")):
            raise ValueError("unknown session layout")
        self.lock = WriterLock(self.directory)
        try:
            self.session = validate_session(self.bundle, read_json(self.directory / "session.json"))
            if self.session.annotator_id != annotator:
                raise ValueError("wrong annotator for resume")
            self.records = load_records(self.bundle, self.session, self.directory)
            self.drafts = load_drafts(self.bundle, self.session, self.directory)
            self.mapping = self.bundle["mapping"][annotator]
            write_json(self.directory / "runs" / f"{uuid.uuid4().hex}.json", {
                "started_at": now(), "pid": os.getpid(), "resume": resume,
                "pending_files": len(list((self.directory / "pending").iterdir())),
                "confirmed_records": len(self.records), "environment": source_evidence(),
            })
        except Exception:
            self.close()
            raise

    def close(self):
        if self.lock:
            self.lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def open_view(self) -> dict:
        with self.mutex:
            if len(self.records) == len(self.mapping):
                return {"complete": True}
            display = self.mapping[len(self.records)]
            view = {**display, "handle": uuid.uuid4().hex, "started_at": now(),
                    "started_clock": time.monotonic(), "media_served": set(), "ready": False}
            # Keep old views so exact network retries can be recognized, but cap memory.
            if len(self.views) >= 128:
                self.views.pop(next(iter(self.views)))
            self.views[view["handle"]] = view
            return view

    def current_view(self, handle: str) -> dict:
        view = self.views.get(handle)
        if view is None or view["position"] != len(self.records) + 1:
            raise Conflict("stale view")
        return view

    def save_draft(self, handle: str, answers: dict, revision: int) -> int:
        with self.mutex:
            view = self.current_view(handle)
            if type(revision) is not int or revision < 0:
                raise ValueError("invalid draft revision")
            old = self.drafts.get(view["comparison_id"])
            if revision != (old.revision if old else 0):
                raise Conflict("draft changed in another tab")
            draft = Draft(session_id=self.session.session_id, bundle_sha256=self.bundle["sha256"],
                          comparison_id=view["comparison_id"], revision=revision + 1,
                          answers=DraftAnswers.model_validate(answers), updated_at=now())
            atomic_json(self.directory / "drafts" / f"{view['position']:04}.json", draft.model_dump(), replace=True)
            self.drafts[view["comparison_id"]] = draft
            return draft.revision

    def submit(self, handle: str, answers: dict, request_id: str) -> Annotation:
        with self.mutex:
            screen = Answers.model_validate(answers)
            for record in self.records:
                if record.request_id == request_id:
                    attempted_view = self.views.get(handle)
                    if record.screen == screen and (attempted_view is None or attempted_view["comparison_id"] == record.comparison_id):
                        return record
                    raise Conflict("request already submitted with different content")
            view = self.views.get(handle)
            if view is None:
                raise Conflict("unknown view; restore current question")
            content = canonical_sha256({"comparison_id": view["comparison_id"], "answers": screen.model_dump()})
            self.current_view(handle)
            if not view["ready"] or view["media_served"] != {"source", "A", "B"}:
                raise ValueError("media not ready")
            check_media(self.bundle, view["comparison_id"])
            record = Annotation(
                protocol=PROTOCOL, mode=self.session.mode,
                source="human" if self.session.mode == "formal" else "practice", status="confirmed",
                session_id=self.session.session_id, annotator_id=self.session.annotator_id,
                bundle_sha256=self.bundle["sha256"], protocol_sha256=self.bundle["protocol_sha256"],
                comparison_id=view["comparison_id"], position=view["position"], x_as=view["x_as"],
                screen=screen, canonical=canonical_answers(screen, view["x_as"]),
                media=media_for(self.bundle, view["comparison_id"]), request_id=request_id,
                presentation_media=presentation_for(self.bundle, view["comparison_id"]),
                presentation_mode=self.bundle["presentation_mode"],
                content_sha256=content, view_started_at=view["started_at"], submitted_at=now(),
                current_view_elapsed_seconds=time.monotonic() - view["started_clock"], timing=CONFIG["timing"],
            )
            validate_record(self.bundle, self.session, record.model_dump())
            target = self.directory / "records" / f"{view['position']:04}.json"
            try:
                atomic_json(target, record.model_dump())
            except OSError:
                # A rename may have succeeded before a connection/interruption reported failure.
                # Reconcile the immutable fact, never overwrite it or duplicate the answer.
                if not target.is_file():
                    raise
                existing = validate_record(self.bundle, self.session, read_json(target))
                if existing.request_id != request_id or existing.content_sha256 != content:
                    raise Conflict("published record conflicts with request")
                record = existing
            self.records.append(record)
            return record
