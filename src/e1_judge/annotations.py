"""Human annotation UI, canonical mapping, adjudication, and agreement metrics."""

from __future__ import annotations

import html
import json
import mimetypes
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlparse

from .hashing import canonical_sha256
from .models import (
    AdjudicatedLabelV2, HumanAnnotationV2, MediaManifestV2, PairRecordV2,
)

DIMENSIONS = ("faithfulness", "preservation", "temporal_consistency", "visual_quality")
FIELDS = (*DIMENSIONS, "overall")
FAILURE_TAGS = (
    "under_edit", "over_edit", "identity_loss", "background_change",
    "flicker", "motion_break", "artifact", "crop_failure", "cannot_judge",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def display_direction(pair_id: str, annotator_id: str, seed: int) -> str:
    digest = canonical_sha256({"pair_id": pair_id, "annotator_id": annotator_id, "seed": seed})
    return "a_vs_b" if int(digest, 16) % 2 == 0 else "b_vs_a"


def canonical_preference(screen_preference: str, direction: str) -> str:
    if screen_preference in {"tie", "uncertain"}:
        return screen_preference
    if screen_preference not in {"left", "right"}:
        raise ValueError(f"invalid screen preference: {screen_preference}")
    left_is_a = direction == "a_vs_b"
    chose_a = (screen_preference == "left" and left_is_a) or (screen_preference == "right" and not left_is_a)
    return "a" if chose_a else "b"


def _canonical_tags(left: List[str], right: List[str], direction: str) -> Tuple[List[str], List[str]]:
    return (left, right) if direction == "a_vs_b" else (right, left)


def _read_pairs(path: Path) -> List[PairRecordV2]:
    return [
        PairRecordV2.model_validate(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _load_annotations(path: Path) -> List[HumanAnnotationV2]:
    if not Path(path).exists():
        return []
    records = [
        HumanAnnotationV2.model_validate(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    ids = [record.pair_id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate pair annotations in {path}")
    return records


def _load_pair_filter(path: Path) -> List[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("disputed_pair_ids")
    if not isinstance(payload, list) or not payload or not all(isinstance(item, str) for item in payload):
        raise ValueError("pair filter must be a non-empty JSON list or report with disputed_pair_ids")
    if len(payload) != len(set(payload)):
        raise ValueError("pair filter contains duplicate pair IDs")
    return payload


def _asset_paths(manifest: MediaManifestV2, pair: PairRecordV2, direction: str) -> Dict[str, Path]:
    source = manifest.sources[pair.sample_id]
    canonical = [manifest.candidates[pair.candidate_a.candidate_id], manifest.candidates[pair.candidate_b.candidate_id]]
    screen = canonical if direction == "a_vs_b" else list(reversed(canonical))
    packet = manifest.pairs[pair.pair_id]
    paths = {
        "source-video": Path(source.video.path),
        "source-contact": Path(source.contact_sheet.path),
        "left-video": Path(screen[0].video.path),
        "left-contact": Path(screen[0].contact_sheet.path),
        "right-video": Path(screen[1].video.path),
        "right-contact": Path(screen[1].contact_sheet.path),
    }
    if packet.mask_overlay:
        paths["mask-overlay"] = Path(packet.mask_overlay.path)
    return paths


def media_tokens(
    manifest: MediaManifestV2, pairs: Iterable[PairRecordV2], annotator_id: str
) -> Tuple[Dict[Tuple[str, str], str], Dict[str, Path]]:
    lookup: Dict[Tuple[str, str], str] = {}
    files: Dict[str, Path] = {}
    for pair in pairs:
        direction = display_direction(pair.pair_id, annotator_id, pair.randomization_seed)
        for role, path in _asset_paths(manifest, pair, direction).items():
            token = canonical_sha256({"pair": pair.pair_id, "annotator": annotator_id, "role": role})[:24]
            lookup[(pair.pair_id, role)] = token
            files[token] = path
    return lookup, files


def read_media_range(path: Path, range_header: Optional[str]) -> Tuple[int, Dict[str, str], bytes]:
    """Read a complete or single byte range for browser video playback."""
    size = path.stat().st_size
    start, end, status = 0, size - 1, 200
    if range_header:
        if not range_header.startswith("bytes=") or "," in range_header:
            raise ValueError("only one bytes range is supported")
        raw_start, raw_end = range_header[6:].split("-", 1)
        if not raw_start and not raw_end:
            raise ValueError("empty byte range")
        if raw_start:
            start = int(raw_start)
            end = int(raw_end) if raw_end else size - 1
        else:
            suffix = int(raw_end)
            start = max(0, size - suffix)
            end = size - 1
        if start < 0 or start >= size or end < start:
            raise ValueError("invalid byte range")
        end = min(end, size - 1)
        status = 206
    length = end - start + 1
    with path.open("rb") as handle:
        handle.seek(start)
        body = handle.read(length)
    headers = {
        "Content-Type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "Content-Length": str(length),
        "Accept-Ranges": "bytes",
    }
    if status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return status, headers, body


def _select(name: str) -> str:
    return (
        f"<select name='{name}' required>"
        "<option value='uncertain' selected>uncertain</option>"
        "<option value='left'>Left</option><option value='right'>Right</option>"
        "<option value='tie'>tie</option></select>"
    )


def _render_page(
    pair: PairRecordV2,
    index: int,
    total: int,
    tokens: Dict[Tuple[str, str], str],
    already_saved: bool,
) -> str:
    instruction = html.escape(pair.instruction)
    target = html.escape(pair.target_caption)
    def url(role: str) -> str:
        return f"/media/{quote(tokens[(pair.pair_id, role)])}"
    mask_html = ""
    if (pair.pair_id, "mask-overlay") in tokens:
        mask_html = f"<figure><img src='{url('mask-overlay')}'><figcaption>Target mask</figcaption></figure>"
    dimension_rows = "".join(
        f"<tr><th>{html.escape(dimension)}</th><td>{_select(dimension)}</td></tr>" for dimension in DIMENSIONS
    )
    tag_boxes = "".join(
        f"<label><input type='checkbox' name='failure_tags_{{side}}' value='{tag}'>{tag}</label>"
        for tag in FAILURE_TAGS
    )
    tag_left = tag_boxes.replace("{side}", "left")
    tag_right = tag_boxes.replace("{side}", "right")
    disabled = "<p class='saved'>This pair is already saved and cannot be submitted twice.</p>" if already_saved else ""
    form = "" if already_saved else f"""
      <form method='POST' id='annotation-form'>
        <input type='hidden' name='pair_index' value='{index}'>
        <input type='hidden' name='started_at' value='{_utc_now()}'>
        <table>{dimension_rows}<tr><th>overall</th><td>{_select('overall')}</td></tr></table>
        <h3>Left failure tags</h3><div>{tag_left}</div>
        <h3>Right failure tags</h3><div>{tag_right}</div>
        <label>Confidence <input type='number' name='confidence' min='0' max='1' step='0.05' value='0.8' required></label>
        <label>Notes <textarea name='notes'></textarea></label>
        <button type='submit'>Save and continue</button>
      </form>
      <script>
        const form=document.getElementById('annotation-form'); const key='e1-draft-{index}';
        const saved=localStorage.getItem(key); if(saved){{const data=JSON.parse(saved); for(const [k,v] of Object.entries(data)){{
          const el=form.elements[k]; if(el && el.type!=='hidden' && el.type!=='checkbox') el.value=v;
        }}}}
        form.addEventListener('change',()=>{{const data={{}}; new FormData(form).forEach((v,k)=>data[k]=v); localStorage.setItem(key,JSON.stringify(data));}});
        form.addEventListener('submit',()=>localStorage.removeItem(key));
      </script>
    """
    previous = max(0, index - 1)
    next_index = min(total - 1, index + 1)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>E1 annotation</title>
    <style>body{{font-family:sans-serif;max-width:1200px;margin:auto}}.media{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
    video,img{{width:100%}}table{{border-collapse:collapse}}th,td{{padding:6px;border:1px solid #bbb}}label{{margin:6px;display:inline-block}}.saved{{color:#075}}</style></head><body>
    <h2>Pair {index + 1} / {total}</h2><p><b>Instruction:</b> {instruction}</p><p><b>Target caption:</b> {target}</p>
    <div class='media'>
      <figure><video controls preload='metadata' src='{url('source-video')}'></video><img src='{url('source-contact')}'><figcaption>Source</figcaption></figure>
      <figure><video controls preload='metadata' src='{url('left-video')}'></video><img src='{url('left-contact')}'><figcaption>Left candidate</figcaption></figure>
      <figure><video controls preload='metadata' src='{url('right-video')}'></video><img src='{url('right-contact')}'><figcaption>Right candidate</figcaption></figure>
    </div>{mask_html}{disabled}{form}
    <nav><a href='/?index={previous}'>Previous</a> · <a href='/?index={next_index}'>Next</a></nav></body></html>"""


def run_annotation_server(
    pairs: Path, packets: Path, annotator_id: str, output: Path, host: str, port: int,
    pair_filter: Optional[Path] = None,
) -> None:
    pair_records = _read_pairs(pairs)
    if len(pair_records) != 100:
        raise ValueError("formal E1 annotation requires exactly 100 pairs")
    if pair_filter is not None:
        requested = set(_load_pair_filter(pair_filter))
        known = {pair.pair_id for pair in pair_records}
        if not requested <= known:
            raise ValueError(f"pair filter contains {len(requested - known)} unknown pair IDs")
        pair_records = [pair for pair in pair_records if pair.pair_id in requested]
    manifest = MediaManifestV2.model_validate(
        json.loads((Path(packets) / "media-manifest.json").read_text(encoding="utf-8"))
    )
    existing = {record.pair_id: record for record in _load_annotations(output)}
    token_lookup, token_files = media_tokens(manifest, pair_records, annotator_id)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path.startswith("/media/"):
                token = parsed.path.rsplit("/", 1)[-1]
                path = token_files.get(token)
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
                index = max(0, min(len(pair_records) - 1, int(query["index"][0])))
            else:
                index = next((i for i, pair in enumerate(pair_records) if pair.pair_id not in existing), len(pair_records) - 1)
            pair = pair_records[index]
            body = _render_page(pair, index, len(pair_records), token_lookup, pair.pair_id in existing).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            fields = parse_qs(self.rfile.read(length).decode("utf-8"))
            try:
                index = int(fields["pair_index"][0])
                pair = pair_records[index]
                if pair.pair_id in existing:
                    self.send_error(409, "annotation already saved")
                    return
                direction = display_direction(pair.pair_id, annotator_id, pair.randomization_seed)
                left_tags = fields.get("failure_tags_left", [])
                right_tags = fields.get("failure_tags_right", [])
                tags_a, tags_b = _canonical_tags(left_tags, right_tags, direction)
                annotation = HumanAnnotationV2(
                    annotation_id=canonical_sha256({"pair": pair.pair_id, "annotator": annotator_id})[:20],
                    pair_id=pair.pair_id, annotator_id=annotator_id, display_direction=direction,
                    faithfulness_preference=canonical_preference(fields["faithfulness"][0], direction),
                    preservation_preference=canonical_preference(fields["preservation"][0], direction),
                    temporal_consistency_preference=canonical_preference(fields["temporal_consistency"][0], direction),
                    visual_quality_preference=canonical_preference(fields["visual_quality"][0], direction),
                    overall_preference=canonical_preference(fields["overall"][0], direction),
                    confidence=float(fields["confidence"][0]), failure_tags_a=tags_a, failure_tags_b=tags_b,
                    notes=fields.get("notes", [""])[0], started_at=fields["started_at"][0], submitted_at=_utc_now(),
                )
            except (KeyError, ValueError, IndexError) as exc:
                self.send_error(400, str(exc))
                return
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with Path(output).open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(annotation.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
            existing[pair.pair_id] = annotation
            next_index = next((i for i, item in enumerate(pair_records) if item.pair_id not in existing), index)
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


def _field_value(record: HumanAnnotationV2, field: str) -> str:
    return str(getattr(record, f"{field}_preference"))


def _agreement(a: HumanAnnotationV2, b: HumanAnnotationV2) -> bool:
    return all(_field_value(a, field) == _field_value(b, field) for field in FIELDS)


def cohen_kappa(values_a: List[str], values_b: List[str]) -> float:
    if len(values_a) != len(values_b) or not values_a:
        raise ValueError("kappa requires two non-empty equal-length sequences")
    labels = sorted(set(values_a) | set(values_b))
    n = len(values_a)
    observed = sum(a == b for a, b in zip(values_a, values_b)) / n
    expected = sum((values_a.count(label) / n) * (values_b.count(label) / n) for label in labels)
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return (observed - expected) / (1 - expected)


def adjudicate(
    annotations: List[Path], third: Optional[Path], output: Path, report: Path
) -> List[dict]:
    if len(annotations) != 2:
        raise ValueError("formal adjudication requires exactly two primary annotator files")
    if Path(output).exists() or Path(report).exists():
        raise FileExistsError("adjudication output/report must not already exist")
    primary = [_load_annotations(path) for path in annotations]
    for path, records in zip(annotations, primary):
        if len(records) != 100:
            raise ValueError(f"primary annotator file {path} must contain exactly 100 pairs")
        if len({record.annotator_id for record in records}) != 1:
            raise ValueError(f"primary annotator file {path} mixes annotator IDs")
    primary_ids = {primary[0][0].annotator_id, primary[1][0].annotator_id}
    if len(primary_ids) != 2:
        raise ValueError("primary annotation files must come from two distinct annotators")
    by_primary = [{record.pair_id: record for record in records} for records in primary]
    if set(by_primary[0]) != set(by_primary[1]):
        raise ValueError("primary annotators must cover identical pair IDs")
    disputed = {
        pair_id for pair_id in by_primary[0]
        if not _agreement(by_primary[0][pair_id], by_primary[1][pair_id])
    }

    agreement_by_field = {}
    for field in FIELDS:
        values_a = [_field_value(by_primary[0][pair_id], field) for pair_id in sorted(by_primary[0])]
        values_b = [_field_value(by_primary[1][pair_id], field) for pair_id in sorted(by_primary[1])]
        agreement_by_field[field] = {
            "agreement_rate": sum(a == b for a, b in zip(values_a, values_b)) / 100,
            "cohen_kappa": cohen_kappa(values_a, values_b),
        }
    report_payload = {
        "schema_version": "2",
        "status": "complete",
        "annotators": [primary[0][0].annotator_id, primary[1][0].annotator_id],
        "completion": {primary[0][0].annotator_id: 1.0, primary[1][0].annotator_id: 1.0},
        "agreement": agreement_by_field,
        "disputed_pairs": len(disputed),
        "disputed_pair_ids": sorted(disputed),
        "third_annotator_labels": 0,
        "tie_rate": None,
        "uncertain_rate": None,
    }
    third_records = _load_annotations(third) if third else []
    third_by_pair = {record.pair_id: record for record in third_records}
    if third_records and (
        len({record.annotator_id for record in third_records}) != 1
        or third_records[0].annotator_id in primary_ids
    ):
        raise ValueError("third annotations must come from one distinct annotator")
    if set(third_by_pair) != disputed:
        missing = disputed - set(third_by_pair)
        extra = set(third_by_pair) - disputed
        report_payload["status"] = "needs_third_annotator" if not third_records else "invalid_third_coverage"
        report_payload["third_annotator_labels"] = len(third_records)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps(report_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise ValueError(f"third annotator must cover exactly disputed pairs; missing={len(missing)} extra={len(extra)}")

    results = []
    for pair_id in sorted(by_primary[0]):
        a = by_primary[0][pair_id]
        b = by_primary[1][pair_id]
        agree = _agreement(a, b)
        selected = a if agree else third_by_pair[pair_id]
        result = AdjudicatedLabelV2(
            pair_id=pair_id, annotator_ids=[a.annotator_id, b.annotator_id], agreement=agree,
            third_annotator_id=None if agree else selected.annotator_id,
            faithfulness_preference=selected.faithfulness_preference,
            preservation_preference=selected.preservation_preference,
            temporal_consistency_preference=selected.temporal_consistency_preference,
            visual_quality_preference=selected.visual_quality_preference,
            overall_preference=selected.overall_preference,
            human_tie=selected.overall_preference == "tie",
            human_uncertain=selected.overall_preference == "uncertain",
            adjudicated_at=_utc_now(),
        ).model_dump(mode="json")
        results.append(result)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")

    report_payload["third_annotator_labels"] = len(third_records)
    report_payload["tie_rate"] = sum(result["human_tie"] for result in results) / 100
    report_payload["uncertain_rate"] = sum(result["human_uncertain"] for result in results) / 100
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results
