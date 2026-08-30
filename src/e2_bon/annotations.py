"""Blind E2 N=4 versus N=1 annotation and complete third-party adjudication."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlparse

from e1_judge.annotations import cohen_kappa, read_media_range
from e1_judge.hashing import canonical_sha256
from e1_judge.models import MediaManifestV2

from .io import atomic_write_new_json, read_json
from .models import (
    E2AdjudicatedComparisonV1,
    E2HumanAnnotationV1,
    E2HumanComparisonV1,
    E2SelectionBundleV1,
)

DIMENSIONS = ("faithfulness", "preservation", "temporal_consistency", "visual_quality")
FIELDS = (*DIMENSIONS, "overall")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def display_direction(comparison_id: str, annotator_id: str, seed: int) -> str:
    digest = canonical_sha256({"comparison_id": comparison_id, "annotator_id": annotator_id, "seed": seed})
    return "a_vs_b" if int(digest, 16) % 2 == 0 else "b_vs_a"


def canonical_preference(screen_preference: str, direction: str) -> str:
    if screen_preference in {"tie", "uncertain"}:
        return screen_preference
    if screen_preference not in {"left", "right"}:
        raise ValueError(f"invalid screen preference: {screen_preference}")
    left_is_a = direction == "a_vs_b"
    chose_a = (screen_preference == "left" and left_is_a) or (
        screen_preference == "right" and not left_is_a
    )
    return "a" if chose_a else "b"


def _load_bundle(path: Path) -> E2SelectionBundleV1:
    return E2SelectionBundleV1.model_validate(read_json(path))


def _load_annotations(path: Path) -> List[E2HumanAnnotationV1]:
    if not Path(path).is_file():
        return []
    records = [
        E2HumanAnnotationV1.model_validate(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    ids = [item.comparison_id for item in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate E2 comparison annotations in {path}")
    return records


def _load_filter(path: Path) -> List[str]:
    payload = read_json(path)
    if isinstance(payload, dict):
        payload = payload.get("disputed_comparison_ids")
    if not isinstance(payload, list) or not payload or not all(isinstance(item, str) for item in payload):
        raise ValueError("comparison filter must be a non-empty list or adjudication report")
    if len(set(payload)) != len(payload):
        raise ValueError("comparison filter contains duplicates")
    return payload


def _media_tokens(
    manifest: MediaManifestV2, comparisons: List[E2HumanComparisonV1], annotator_id: str,
) -> Tuple[Dict[Tuple[str, str], str], Dict[str, Path]]:
    token_lookup: Dict[Tuple[str, str], str] = {}
    files: Dict[str, Path] = {}
    for comparison in comparisons:
        direction = display_direction(comparison.comparison_id, annotator_id, comparison.randomization_seed)
        canonical = [
            manifest.candidates[comparison.n4_candidate_id],
            manifest.candidates[comparison.n1_candidate_id],
        ]
        screen = canonical if direction == "a_vs_b" else list(reversed(canonical))
        source = manifest.sources[comparison.sample_id]
        paths = {
            "source-video": Path(source.video.path),
            "source-contact": Path(source.contact_sheet.path),
            "left-video": Path(screen[0].video.path),
            "left-contact": Path(screen[0].contact_sheet.path),
            "right-video": Path(screen[1].video.path),
            "right-contact": Path(screen[1].contact_sheet.path),
        }
        for role, path in paths.items():
            token = canonical_sha256({
                "comparison": comparison.comparison_id, "annotator": annotator_id, "role": role,
            })[:24]
            token_lookup[(comparison.comparison_id, role)] = token
            files[token] = path
    return token_lookup, files


def _select(name: str) -> str:
    return (
        f"<select name='{name}' required><option value='uncertain' selected>uncertain</option>"
        "<option value='left'>Left</option><option value='right'>Right</option>"
        "<option value='tie'>tie</option></select>"
    )


def render_annotation_page(
    comparison: E2HumanComparisonV1, index: int, total: int,
    tokens: Dict[Tuple[str, str], str], already_saved: bool,
) -> str:
    def media_url(role: str) -> str:
        return f"/media/{quote(tokens[(comparison.comparison_id, role)])}"

    rows = "".join(f"<tr><th>{html.escape(field)}</th><td>{_select(field)}</td></tr>" for field in FIELDS)
    saved = "<p class='saved'>This comparison is already saved.</p>" if already_saved else ""
    form = "" if already_saved else f"""
    <form method='POST' id='e2-form'>
      <input type='hidden' name='comparison_index' value='{index}'>
      <input type='hidden' name='started_at' value='{_utc_now()}'>
      <table>{rows}</table>
      <label>Confidence <input type='number' name='confidence' min='0' max='1' step='0.05' value='0.8' required></label>
      <label>Notes <textarea name='notes'></textarea></label>
      <button type='submit'>Save and continue</button>
    </form>
    """
    previous = max(0, index - 1)
    following = min(total - 1, index + 1)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>E2 blind comparison</title>
    <style>body{{font-family:sans-serif;max-width:1200px;margin:auto}}.media{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
    video,img{{width:100%}}table{{border-collapse:collapse}}th,td{{padding:6px;border:1px solid #bbb}}label{{display:block;margin:8px}}.saved{{color:#075}}</style>
    </head><body><h2>Blind comparison {index + 1} / {total}</h2>
    <p><b>Instruction:</b> {html.escape(comparison.instruction)}</p>
    <p><b>Target caption:</b> {html.escape(comparison.target_caption)}</p>
    <div class='media'>
      <figure><video controls preload='metadata' src='{media_url('source-video')}'></video><img src='{media_url('source-contact')}'><figcaption>Source</figcaption></figure>
      <figure><video controls preload='metadata' src='{media_url('left-video')}'></video><img src='{media_url('left-contact')}'><figcaption>Candidate Left</figcaption></figure>
      <figure><video controls preload='metadata' src='{media_url('right-video')}'></video><img src='{media_url('right-contact')}'><figcaption>Candidate Right</figcaption></figure>
    </div>{saved}{form}<nav><a href='/?index={previous}'>Previous</a> · <a href='/?index={following}'>Next</a></nav>
    </body></html>"""


def run_annotation_server(
    selection: Path, packets: Path, annotator_id: str, output: Path,
    host: str = "127.0.0.1", port: int = 8766, comparison_filter: Optional[Path] = None,
) -> None:
    bundle = _load_bundle(selection)
    comparisons = [item for item in bundle.human_comparisons if not item.identical_selection]
    if comparison_filter is not None:
        requested = set(_load_filter(comparison_filter))
        known = {item.comparison_id for item in comparisons}
        if not requested <= known:
            raise ValueError("comparison filter contains unknown or automatic-tie IDs")
        comparisons = [item for item in comparisons if item.comparison_id in requested]
    if not comparisons:
        raise ValueError("E2 annotation has no non-identical comparisons to label")
    manifest = MediaManifestV2.model_validate(read_json(Path(packets) / "media-manifest.json"))
    existing = {item.comparison_id: item for item in _load_annotations(output)}
    if not set(existing) <= {item.comparison_id for item in comparisons}:
        raise ValueError("existing annotation file does not match the selected E2 comparison set")
    token_lookup, token_files = _media_tokens(manifest, comparisons, annotator_id)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path.startswith("/media/"):
                path = token_files.get(parsed.path.rsplit("/", 1)[-1])
                if path is None or not path.is_file():
                    self.send_error(404)
                    return
                try:
                    status, headers, body = read_media_range(path, self.headers.get("Range"))
                except (ValueError, OSError):
                    self.send_error(416)
                    return
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)
                return
            query = parse_qs(parsed.query)
            if "index" in query:
                index = max(0, min(len(comparisons) - 1, int(query["index"][0])))
            else:
                index = next(
                    (position for position, item in enumerate(comparisons) if item.comparison_id not in existing),
                    len(comparisons) - 1,
                )
            comparison = comparisons[index]
            body = render_annotation_page(
                comparison, index, len(comparisons), token_lookup, comparison.comparison_id in existing,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # noqa: N802
            fields = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            try:
                index = int(fields["comparison_index"][0])
                comparison = comparisons[index]
                if comparison.comparison_id in existing:
                    self.send_error(409, "annotation already saved")
                    return
                direction = display_direction(
                    comparison.comparison_id, annotator_id, comparison.randomization_seed,
                )
                record = E2HumanAnnotationV1(
                    annotation_id=canonical_sha256({
                        "comparison": comparison.comparison_id, "annotator": annotator_id,
                    })[:20],
                    comparison_id=comparison.comparison_id, annotator_id=annotator_id,
                    display_direction=direction,
                    faithfulness_preference=canonical_preference(fields["faithfulness"][0], direction),
                    preservation_preference=canonical_preference(fields["preservation"][0], direction),
                    temporal_consistency_preference=canonical_preference(fields["temporal_consistency"][0], direction),
                    visual_quality_preference=canonical_preference(fields["visual_quality"][0], direction),
                    overall_preference=canonical_preference(fields["overall"][0], direction),
                    confidence=float(fields["confidence"][0]), notes=fields.get("notes", [""])[0],
                    started_at=fields["started_at"][0], submitted_at=_utc_now(),
                )
            except (IndexError, KeyError, ValueError) as exc:
                self.send_error(400, str(exc))
                return
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with Path(output).open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
            existing[comparison.comparison_id] = record
            next_index = next(
                (position for position, item in enumerate(comparisons) if item.comparison_id not in existing), index,
            )
            self.send_response(303)
            self.send_header("Location", f"/?index={next_index}")
            self.end_headers()

        def log_message(self, *_args) -> None:
            pass

    server = HTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _field(record: E2HumanAnnotationV1, field: str) -> str:
    return str(getattr(record, f"{field}_preference"))


def _agreement(left: E2HumanAnnotationV1, right: E2HumanAnnotationV1) -> bool:
    return all(_field(left, field) == _field(right, field) for field in FIELDS)


def _outcome(preference: str) -> str:
    return {"a": "n4", "b": "n1", "tie": "tie", "uncertain": "uncertain"}[preference]


def _write_jsonl_new(path: Path, records: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def adjudicate_e2(
    selection: Path, annotations: List[Path], third: Optional[Path], output: Path, report: Path,
) -> List[dict]:
    if len(annotations) != 2:
        raise ValueError("E2 adjudication requires exactly two primary annotation files")
    if Path(output).exists() or Path(report).exists():
        raise FileExistsError("E2 adjudication output/report must be absent")
    bundle = _load_bundle(selection)
    comparisons = {item.comparison_id: item for item in bundle.human_comparisons}
    expected = {item.comparison_id for item in bundle.human_comparisons if not item.identical_selection}
    primary = [_load_annotations(path) for path in annotations]
    primary_maps = [{item.comparison_id: item for item in records} for records in primary]
    primary_ids = []
    for path, records, record_map in zip(annotations, primary, primary_maps):
        if set(record_map) != expected:
            raise ValueError(f"primary annotator file {path} must cover every non-identical comparison")
        annotator_ids = {item.annotator_id for item in records}
        if len(annotator_ids) != 1:
            raise ValueError(f"primary annotator file {path} mixes annotator identities")
        annotator_id = next(iter(annotator_ids))
        for record in records:
            comparison = comparisons[record.comparison_id]
            expected_direction = display_direction(
                record.comparison_id, annotator_id, comparison.randomization_seed,
            )
            if record.display_direction != expected_direction:
                raise ValueError(f"annotation display direction mismatch in {path}")
        primary_ids.append(annotator_id)
    if len(set(primary_ids)) != 2:
        raise ValueError("E2 primary annotations must come from two distinct annotators")
    disputed = {
        comparison_id for comparison_id in expected
        if not _agreement(primary_maps[0][comparison_id], primary_maps[1][comparison_id])
    }
    agreement = {}
    for field in FIELDS:
        ordered = sorted(expected)
        values_a = [_field(primary_maps[0][comparison_id], field) for comparison_id in ordered]
        values_b = [_field(primary_maps[1][comparison_id], field) for comparison_id in ordered]
        agreement[field] = {
            "agreement_rate": sum(a == b for a, b in zip(values_a, values_b)) / len(ordered) if ordered else 1.0,
            "cohen_kappa": cohen_kappa(values_a, values_b) if ordered else 1.0,
        }
    third_records = _load_annotations(third) if third else []
    third_map = {item.comparison_id: item for item in third_records}
    if third_records:
        third_ids = {item.annotator_id for item in third_records}
        if len(third_ids) != 1 or next(iter(third_ids)) in set(primary_ids):
            raise ValueError("third annotations must come from one distinct annotator")
        third_id = next(iter(third_ids))
        for record in third_records:
            comparison = comparisons.get(record.comparison_id)
            if comparison is None or record.display_direction != display_direction(
                record.comparison_id, third_id, comparison.randomization_seed,
            ):
                raise ValueError("third annotation display direction mismatch")
    report_payload = {
        "schema_version": "1", "status": "complete", "primary_annotators": primary_ids,
        "non_identical_comparisons": len(expected),
        "identical_selection_ties": 80 - len(expected), "agreement": agreement,
        "disputed_comparisons": len(disputed), "disputed_comparison_ids": sorted(disputed),
        "third_annotator_labels": len(third_records),
    }
    if set(third_map) != disputed:
        report_payload["status"] = "needs_third_annotator" if not third_records else "invalid_third_coverage"
        atomic_write_new_json(report, report_payload)
        raise ValueError(
            "third annotator must cover every and only disputed non-identical comparison; "
            f"missing={len(disputed - set(third_map))} extra={len(set(third_map) - disputed)}"
        )

    adjudicated = []
    for comparison_id in sorted(comparisons):
        comparison = comparisons[comparison_id]
        if comparison.identical_selection:
            record = E2AdjudicatedComparisonV1(
                comparison_id=comparison_id, trial_id=comparison.trial_id,
                sample_id=comparison.sample_id, replicate=comparison.replicate,
                n4_candidate_id=comparison.n4_candidate_id, n1_candidate_id=comparison.n1_candidate_id,
                identical_selection=True, automatic_tie=True, annotator_ids=[], primary_agreement=None,
                faithfulness_outcome="tie", preservation_outcome="tie",
                temporal_consistency_outcome="tie", visual_quality_outcome="tie",
                overall_outcome="tie", adjudicated_at=_utc_now(),
            )
        else:
            left = primary_maps[0][comparison_id]
            right = primary_maps[1][comparison_id]
            agreed = _agreement(left, right)
            selected = left if agreed else third_map[comparison_id]
            record = E2AdjudicatedComparisonV1(
                comparison_id=comparison_id, trial_id=comparison.trial_id,
                sample_id=comparison.sample_id, replicate=comparison.replicate,
                n4_candidate_id=comparison.n4_candidate_id, n1_candidate_id=comparison.n1_candidate_id,
                identical_selection=False, automatic_tie=False, annotator_ids=primary_ids,
                primary_agreement=agreed, third_annotator_id=None if agreed else selected.annotator_id,
                faithfulness_outcome=_outcome(selected.faithfulness_preference),
                preservation_outcome=_outcome(selected.preservation_preference),
                temporal_consistency_outcome=_outcome(selected.temporal_consistency_preference),
                visual_quality_outcome=_outcome(selected.visual_quality_preference),
                overall_outcome=_outcome(selected.overall_preference), adjudicated_at=_utc_now(),
            )
        adjudicated.append(record.model_dump(mode="json"))
    _write_jsonl_new(output, adjudicated)
    report_payload["tie_rate"] = sum(item["overall_outcome"] == "tie" for item in adjudicated) / 80
    report_payload["uncertain_rate"] = sum(item["overall_outcome"] == "uncertain" for item in adjudicated) / 80
    atomic_write_new_json(report, report_payload)
    return adjudicated
