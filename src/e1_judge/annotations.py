"""E1 human annotation service and adjudication."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional

from .hashing import canonical_sha256
from .models import AdjudicatedLabel, HumanAnnotation

ANNOTATION_SCHEMA_VERSION = "1"
ADJUDICATION_PROTOCOL_VERSION = "1"

DIMENSIONS = ["faithfulness", "preservation", "temporal_consistency", "visual_quality"]
PREFERENCES = {"a", "b", "tie", "uncertain"}


def _read_pairs(pairs_path: Path) -> List[dict]:
    return [json.loads(line) for line in Path(pairs_path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_existing_annotations(output: Path) -> Dict[str, dict]:
    path = Path(output)
    if not path.exists():
        return {}
    by_pair = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            by_pair[record["pair_id"]] = record
    return by_pair


def _render_page(pair: dict, index: int, total: int) -> str:
    rows = []
    for dim in DIMENSIONS:
        rows.append(
            f"<label>{dim}: <select name='{dim}'>"
            "<option value='a'>A</option><option value='b'>B</option>"
            "<option value='tie'>tie</option><option value='uncertain'>uncertain</option></select></label><br>"
        )
    return (
        "<html><head><meta charset='utf-8'><title>E1 annotation</title></head><body>"
        f"<h2>{index + 1}/{total} — {pair['pair_id']}</h2>"
        f"<p><b>Instruction:</b> {pair['instruction']}</p>"
        f"<p><b>Target caption:</b> {pair['target_caption']}</p>"
        "<p>Video A (left) and B (right):</p><form method='POST'>"
        + "".join(rows)
        + "<label>Overall: <select name='overall'><option value='a'>A</option><option value='b'>B</option>"
          "<option value='tie'>tie</option><option value='uncertain'>uncertain</option></select></label><br>"
          "<label>Confidence (0-1): <input name='confidence' value='0.8'></label><br>"
          "<input type='submit' value='Submit'></form></body></html>"
    )


def run_annotation_server(
    pairs: Path, packets: Path, annotator_id: str, output: Path, host: str, port: int
) -> None:
    """Serve a minimal single-user loopback annotation UI on HTTP."""
    pair_records = _read_pairs(pairs)
    existing = _load_existing_annotations(output)
    remaining = [pair for pair in pair_records if pair["pair_id"] not in existing]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if not remaining:
                body = b"<html><body><h2>All pairs annotated. Done.</h2></body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(body)
                return
            pair = remaining[0]
            body = _render_page(pair, len(pair_records) - len(remaining), len(pair_records)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # noqa: N802
            from urllib.parse import parse_qs

            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            fields = parse_qs(raw)
            if not remaining:
                self.send_response(400)
                self.end_headers()
                return
            pair = remaining.pop(0)
            annotation = HumanAnnotation(
                annotation_id=canonical_sha256(f"{pair['pair_id']}|{annotator_id}")[:16],
                pair_id=pair["pair_id"],
                annotator_id=annotator_id,
                display_direction=pair["display_direction"],
                faithfulness_preference=fields["faithfulness"][0],
                preservation_preference=fields["preservation"][0],
                temporal_consistency_preference=fields["temporal_consistency"][0],
                visual_quality_preference=fields["visual_quality"][0],
                overall_preference=fields["overall"][0],
                confidence=float(fields["confidence"][0]),
                started_at="",
                submitted_at="",
                annotation_schema_version=ANNOTATION_SCHEMA_VERSION,
            )
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with Path(output).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(annotation.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

        def log_message(self, *_args) -> None:
            pass

    server = HTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _load_annotations(path: Path) -> List[HumanAnnotation]:
    if not Path(path).exists():
        return []
    return [HumanAnnotation.model_validate(json.loads(line)) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _agreement(a: HumanAnnotation, b: HumanAnnotation) -> bool:
    return (
        a.overall_preference == b.overall_preference
        and a.faithfulness_preference == b.faithfulness_preference
        and a.preservation_preference == b.preservation_preference
        and a.temporal_consistency_preference == b.temporal_consistency_preference
        and a.visual_quality_preference == b.visual_quality_preference
    )


def adjudicate(annotations: List[Path], third: Optional[Path], output: Path) -> List[dict]:
    """Adjudicate two annotators per pair and apply a third for disagreements."""
    if len(annotations) < 2:
        raise ValueError("adjudicate requires at least two annotator files")
    first = _load_annotations(annotations[0])
    second = _load_annotations(annotations[1])
    first_by_pair = {a.pair_id: a for a in first}
    second_by_pair = {a.pair_id: a for a in second}
    third_by_pair = {}
    if third is not None:
        third_by_pair = {a.pair_id: a for a in _load_annotations(third)}

    pair_ids = set(first_by_pair) | set(second_by_pair)
    results: List[dict] = []
    for pair_id in sorted(pair_ids):
        a = first_by_pair.get(pair_id)
        b = second_by_pair.get(pair_id)
        if a is None or b is None:
            raise ValueError(f"pair {pair_id} missing annotation from one annotator")
        agree = _agreement(a, b)
        chosen = a
        third_id = None
        if not agree:
            if pair_id not in third_by_pair:
                raise ValueError(f"pair {pair_id} is disputed but no third annotation provided")
            chosen = third_by_pair[pair_id]
            third_id = chosen.annotator_id

        results.append(
            AdjudicatedLabel(
                pair_id=pair_id,
                annotator_ids=[a.annotator_id, b.annotator_id],
                agreement=agree,
                third_annotator_id=third_id,
                faithfulness_preference=chosen.faithfulness_preference,
                preservation_preference=chosen.preservation_preference,
                temporal_consistency_preference=chosen.temporal_consistency_preference,
                visual_quality_preference=chosen.visual_quality_preference,
                overall_preference=chosen.overall_preference,
                human_tie=chosen.overall_preference == "tie",
                human_uncertain=chosen.overall_preference == "uncertain",
                adjudicated_at="",
                protocol_version=ADJUDICATION_PROTOCOL_VERSION,
            ).model_dump(mode="json")
        )

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with Path(output).open("w", encoding="utf-8") as handle:
        for record in results:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return results
