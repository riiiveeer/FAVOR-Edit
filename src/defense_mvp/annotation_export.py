"""Immutable exports and coverage verification only; no preference statistics."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from w1_pipeline.hashing import canonical_sha256, sha256_file

from .annotation_bundle import (
    automatic_ties, load_bundle, now, read_json, source_evidence, stage, verify_sums, write_sums,
)
from .annotation_models import ANNOTATORS, PROTOCOL, Coverage
from .annotation_store import WriterLock, load_drafts, load_records, validate_record, validate_session
from .io import rename_noreplace, write_json


def coverage_for(bundle: dict, annotator: str, records: list) -> dict:
    expected = {r["comparison_id"] for r in bundle["mapping"][annotator]}
    actual = [r.comparison_id for r in records]
    auto = [r["comparison_id"] for r in automatic_ties(bundle["comparisons"])]
    if len(actual) != len(set(actual)) or not set(actual) <= expected or set(auto) & expected:
        raise ValueError("invalid coverage identity")
    if len(expected) + len(auto) != 42:
        raise ValueError("invalid coverage denominator")
    missing = sorted(expected - set(actual))
    return Coverage(protocol=PROTOCOL, mode=bundle["mode"], bundle_sha256=bundle["sha256"],
                    annotator_id=annotator, status="incomplete" if missing else "complete",
                    human_comparison_ids=sorted(actual), automatic_comparison_ids=auto,
                    missing_comparison_ids=missing, covered=len(actual) + len(auto), total=42).model_dump()


def export_annotations(bundle_path: Path, session_path: Path, output: Path) -> dict:
    bundle = load_bundle(bundle_path)
    session_path, output = Path(session_path), Path(output)
    if os.path.lexists(output):
        raise FileExistsError("export output already exists")
    with WriterLock(session_path):
        session = validate_session(bundle, read_json(session_path / "session.json"))
        if session_path.name != session.annotator_id:
            raise ValueError("session directory identity mismatch")
        records = load_records(bundle, session, session_path)
        load_drafts(bundle, session, session_path)
        coverage = coverage_for(bundle, session.annotator_id, records)
        staging = stage(output)
        ordered = sorted(records, key=lambda r: r.comparison_id)
        with (staging / "answers.jsonl").open("x", encoding="utf-8", newline="\n") as handle:
            for record in ordered:
                handle.write(json.dumps(record.model_dump(), ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        write_json(staging / "session.json", session.model_dump())
        write_json(staging / "coverage.json", coverage)
        write_json(staging / "automatic-ties.json", automatic_ties(bundle["comparisons"]))
        facts = [{"position": r.position, "comparison_id": r.comparison_id,
                  "file_sha256": sha256_file(session_path / "records" / f"{r.position:04}.json"),
                  "canonical_sha256": canonical_sha256(r.model_dump())} for r in ordered]
        write_json(staging / "records-manifest.json", facts)
        receipt = {"status": coverage["status"], "mode": bundle["mode"], "protocol": PROTOCOL,
                   "bundle_sha256": bundle["sha256"], "session_id": session.session_id,
                   "annotator_id": session.annotator_id, "exported_answers": len(records),
                   "automatic_ties_shared": len(coverage["automatic_comparison_ids"]), "exported_at": now(),
                   "environment": source_evidence()}
        write_json(staging / "export-receipt.json", receipt)
        write_sums(staging)
        rename_noreplace(staging, output)
        return receipt


def verify_export(bundle: dict, directory: Path) -> dict:
    directory = Path(directory)
    inventory = verify_sums(directory)
    if set(inventory) != {"answers.jsonl", "coverage.json", "session.json", "automatic-ties.json",
                          "records-manifest.json", "export-receipt.json"}:
        raise ValueError("unexpected export inventory")
    session = validate_session(bundle, read_json(directory / "session.json"))
    lines = (directory / "answers.jsonl").read_text(encoding="utf-8").splitlines()
    records = [validate_record(bundle, session, json.loads(line)) for line in lines]
    if [r.comparison_id for r in records] != sorted({r.comparison_id for r in records}):
        raise ValueError("export rows must be unique and sorted")
    if sorted(r.position for r in records) != list(range(1, len(records) + 1)):
        raise ValueError("export positions must form a prefix")
    if len({r.request_id for r in records}) != len(records):
        raise ValueError("duplicate request identity")
    expected_facts = [{"position": r.position, "comparison_id": r.comparison_id,
                       "file_sha256": hashlib.sha256((json.dumps(
                           r.model_dump(), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest(),
                       "canonical_sha256": canonical_sha256(r.model_dump())} for r in records]
    if read_json(directory / "records-manifest.json") != expected_facts:
        raise ValueError("export fact chain mismatch")
    if read_json(directory / "automatic-ties.json") != automatic_ties(bundle["comparisons"]):
        raise ValueError("automatic tie rules mismatch")
    coverage = coverage_for(bundle, session.annotator_id, records)
    if read_json(directory / "coverage.json") != coverage:
        raise ValueError("export coverage mismatch")
    receipt = read_json(directory / "export-receipt.json")
    expected = {"status": coverage["status"], "mode": bundle["mode"], "protocol": PROTOCOL,
                "bundle_sha256": bundle["sha256"], "session_id": session.session_id,
                "annotator_id": session.annotator_id, "exported_answers": len(records),
                "automatic_ties_shared": len(coverage["automatic_comparison_ids"])}
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("export receipt mismatch")
    return coverage


def verify_annotations(bundle_path: Path, exports: list = None, allow_practice: bool = False) -> dict:
    bundle = load_bundle(bundle_path)
    if bundle["mode"] == "practice" and not allow_practice:
        raise ValueError("practice is not accepted as formal evidence; explicit --allow-practice required")
    exports = exports or []
    if len(exports) > 2:
        raise ValueError("at most two independent annotators")
    coverages = [verify_export(bundle, p) for p in exports]
    ids = [c["annotator_id"] for c in coverages]
    if len(ids) != len(set(ids)) or (len(ids) == 2 and set(ids) != set(ANNOTATORS)):
        raise ValueError("two independent annotator identities required")
    complete = bool(coverages) and all(c["status"] == "complete" for c in coverages)
    return {"status": "complete" if complete else "incomplete", "mode": bundle["mode"],
            "scope": "dual" if len(exports) == 2 else "single" if exports else "prepared_bundle",
            "bundle_sha256": bundle["sha256"], "comparisons_per_annotator": 42,
            "manual_per_annotator": len(bundle["mapping"][ANNOTATORS[0]]),
            "automatic_ties_shared": len(automatic_ties(bundle["comparisons"])),
            "exported_answers": sum(len(c["human_comparison_ids"]) for c in coverages),
            "coverages": coverages}
