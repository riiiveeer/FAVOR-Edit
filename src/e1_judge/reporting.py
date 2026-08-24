"""Frozen protocol creation and E1 report generation."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import yaml

from w1_pipeline.hashing import sha256_file

from .models import FrozenProtocolV2, load_runtime_config
from .prompts import load_prompt
from .runner import (
    build_judge_plan, code_snapshot, frozen_protocol_fingerprint, runtime_fingerprint,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def freeze_protocol(
    dev_selection: Path,
    pairs: Path,
    packets: Path,
    config: Path,
    runtime: Path,
    output_dir: Path,
    snapshot: Optional[str] = None,
) -> dict:
    """Copy, freeze, fingerprint, and lock a clean protocol plus its 550-request plan."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"frozen protocol output already exists: {output_dir}")
    selection = json.loads(Path(dev_selection).read_text(encoding="utf-8"))
    if selection.get("blocked") or not selection.get("selected_method"):
        raise ValueError("dev selection is blocked; prompt/judge must be revised before freeze")
    snapshot = snapshot or code_snapshot(Path(config).resolve().parents[2])
    if snapshot == "unknown-code-snapshot" or "+dirty" in snapshot:
        raise ValueError("frozen protocol requires a clean, known Git commit")

    output_dir.mkdir(parents=True)
    protocol_dir = output_dir / "protocol"
    protocol_dir.mkdir()
    config_data = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    config_data["frozen_selection"] = {
        "selected_method": selection["selected_method"],
        "confidence_threshold": float(selection["confidence_threshold"]),
        "absolute_delta_threshold": float(selection["absolute_delta_threshold"]),
    }
    frozen_config = protocol_dir / "pilot-frozen.yaml"
    frozen_config.write_text(yaml.safe_dump(config_data, sort_keys=False, allow_unicode=True), encoding="utf-8")

    prompt_checksums: Dict[str, str] = {}
    for method, method_cfg in config_data["methods"].items():
        source = Path(config).parent / method_cfg["prompt"]
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        payload["status"] = "frozen"
        target = protocol_dir / method_cfg["prompt"]
        target.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
        spec, checksum = load_prompt(target)
        if spec.method != method:
            raise ValueError(f"frozen prompt method mismatch for {method}")
        prompt_checksums[method] = checksum

    frozen_runtime = protocol_dir / "runtime-frozen.yaml"
    shutil.copy2(runtime, frozen_runtime)
    plan_path = output_dir / "judge-plan-frozen.jsonl"
    build_judge_plan(pairs, packets, frozen_config, frozen_runtime, plan_path, snapshot=snapshot)
    runtime_model = load_runtime_config(frozen_runtime)
    runtime_sha = runtime_fingerprint(runtime_model)
    protocol_sha = frozen_protocol_fingerprint(
        frozen_config, config_data, prompt_checksums, runtime_sha, snapshot
    )
    if protocol_sha is None:
        raise ValueError("frozen protocol fingerprint was not generated")
    protocol = FrozenProtocolV2(
        created_at=_utc_now(), code_snapshot=snapshot,
        selected_method=selection["selected_method"],
        confidence_threshold=float(selection["confidence_threshold"]),
        absolute_delta_threshold=float(selection["absolute_delta_threshold"]),
        config_checksum=sha256_file(frozen_config),
        runtime_fingerprint=runtime_sha,
        prompt_checksums=prompt_checksums,
        plan_checksum=sha256_file(plan_path),
        protocol_fingerprint=protocol_sha,
    ).model_dump(mode="json")
    (output_dir / "protocol.lock.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return protocol


def _svg(metrics: dict) -> str:
    methods = list(metrics.get("methods", {}))
    bars = []
    for index, method in enumerate(methods):
        values = metrics["methods"][method]
        accuracy = float(values.get("effective_accuracy", 0))
        coverage = float(values.get("coverage", 0))
        x = 30 + index * 180
        bars.append(
            f"<rect x='{x}' y='{260 - accuracy * 200:.1f}' width='55' height='{accuracy * 200:.1f}' fill='#3366cc'/>"
            f"<rect x='{x + 65}' y='{260 - coverage * 200:.1f}' width='55' height='{coverage * 200:.1f}' fill='#dc3912'/>"
            f"<text x='{x}' y='285' font-size='10'>{method}</text>"
        )
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' width='760' height='310' viewBox='0 0 760 310'>"
        "<rect width='100%' height='100%' fill='white'/><text x='20' y='20'>E1 effective accuracy (blue) / coverage (red)</text>"
        "<line x1='20' y1='260' x2='740' y2='260' stroke='black'/>" + "".join(bars) + "</svg>"
    )


def generate_report(analysis: Path, output_dir: Path) -> Path:
    analysis = Path(analysis)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"report output already exists: {output_dir}")
    metrics_path = analysis / "metrics.json"
    if not metrics_path.is_file():
        raise FileNotFoundError(f"metrics.json missing in {analysis}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    decision_path = analysis / "decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8")) if decision_path.is_file() else None
    output_dir.mkdir(parents=True)
    figures = output_dir / "figures"
    figures.mkdir()
    (figures / "reliability.svg").write_text(_svg(metrics), encoding="utf-8")

    lines = [
        "# E1 Judge Reliability Report", "",
        "## Protocol and data", "",
        f"- mode / split: `{metrics['mode']}` / `{metrics['split']}`",
        f"- evaluated pairs: {metrics['pairs']}",
        f"- adjudicated human labels: {metrics['human']['labels']}",
        f"- primary full-agreement rate: {metrics['human']['agreement_rate']:.3f}",
        f"- third-party adjudications: {metrics['human']['third_party_labels']}", "",
        "## Four-method reliability", "",
        "| method | decisive accuracy | effective accuracy | coverage | swap consistency | Kendall | Spearman |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for method, values in metrics["methods"].items():
        swap = values.get("swap_consistency")
        lines.append(
            f"| {method} | {values['decisive_accuracy']:.3f} | {values['effective_accuracy']:.3f} | "
            f"{values['coverage']:.3f} | {'—' if swap is None else f'{swap:.3f}'} | "
            f"{values['ranking']['kendall_tau']:.3f} | {values['ranking']['spearman']:.3f} |"
        )
    lines.extend(["", "![Reliability](figures/reliability.svg)", "", "## Category and dimensional checks", ""])
    for method, values in metrics["methods"].items():
        category_text = ", ".join(
            f"{name}={category['decisive_accuracy']:.3f}" for name, category in values["categories"].items()
        )
        dimension_text = ", ".join(
            f"{name}={dimension['decisive_accuracy']:.3f}" for name, dimension in values["dimensions"].items()
        )
        lines.extend([f"- **{method} categories:** {category_text}", f"- **{method} dimensions:** {dimension_text}"])

    lines.extend(["", "## Position bias and uncertainty", ""])
    for method, values in metrics["methods"].items():
        bias = values["position_bias"]
        lines.append(
            f"- {method}: left={bias['left_rate']:.3f}, right={bias['right_rate']:.3f}, "
            f"coverage={values['coverage']:.3f}"
        )
    cases = metrics.get("case_candidates", {})
    lines.extend(["", "## Case candidates", ""])
    for tag in ("under_edit", "over_edit"):
        values = cases.get(tag, [])
        lines.append(f"- {tag}: " + (", ".join(item["pair_id"] for item in values[:2]) if values else "none tagged"))
    lines.extend(["", "## Decision", ""])
    if decision:
        lines.append(f"- decision: **{decision['decision']}**")
        lines.append(f"- selected method: `{decision['selected_method']}`")
        lines.append("- gates: " + ", ".join(f"{key}={'PASS' if value else 'FAIL'}" for key, value in decision["gates"].items()))
    else:
        selection_path = analysis / "dev-selection.json"
        selection = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.is_file() else {}
        lines.append(f"- dev selected method: `{selection.get('selected_method')}`")
        lines.append(f"- blocked: `{selection.get('blocked')}`")
    lines.extend(["", "## Limitations", "", "- This 10-video DAVIS pilot is provisional and does not establish broad judge validity."])
    report_path = output_dir / "E1_REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path
