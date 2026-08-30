"""Deterministic Markdown, SVG, and CSV reporting for E2 analysis artifacts."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from e1_judge.phase3 import _rename_noreplace
from w1_pipeline.hashing import sha256_file


def _write_win_svg(path: Path, metrics: dict) -> None:
    point = float(metrics["overall"]["tie_aware_win_rate"])
    lower = float(metrics["overall"]["bootstrap_95_ci"]["lower"])
    upper = float(metrics["overall"]["bootstrap_95_ci"]["upper"])
    x = lambda value: 80 + 700 * value
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="240" viewBox="0 0 860 240">
<rect width="860" height="240" fill="white"/><text x="40" y="35" font-family="sans-serif" font-size="20">E2 N=4 vs N=1 tie-aware win rate</text>
<line x1="80" y1="150" x2="780" y2="150" stroke="#333"/><line x1="{x(0.6):.2f}" y1="70" x2="{x(0.6):.2f}" y2="175" stroke="#d65f5f" stroke-dasharray="5 4"/>
<line x1="{x(lower):.2f}" y1="115" x2="{x(upper):.2f}" y2="115" stroke="#356ca8" stroke-width="8"/>
<circle cx="{x(point):.2f}" cy="115" r="10" fill="#173f6b"/>
<text x="{x(0.6) + 5:.2f}" y="68" font-family="sans-serif" font-size="13">M1 target 0.60</text>
<text x="80" y="195" font-family="sans-serif" font-size="14">0.0</text><text x="765" y="195" font-family="sans-serif" font-size="14">1.0</text>
<text x="80" y="220" font-family="sans-serif" font-size="13">point={point:.3f}; sample-cluster 95% CI [{lower:.3f}, {upper:.3f}]</text></svg>"""
    path.write_text(svg, encoding="utf-8")


def _write_cost_svg(path: Path, rows: list) -> None:
    points_generation = " ".join(f"{80 + index * 200},{190 - row['generated_candidates'] / 4}" for index, row in enumerate(rows))
    points_judge = " ".join(f"{80 + index * 200},{190 - row['primary_judge_requests'] / 40}" for index, row in enumerate(rows))
    labels = "".join(
        f"<text x='{70 + index * 200}' y='220' font-family='sans-serif' font-size='13'>N={row['n']}</text>"
        for index, row in enumerate(rows)
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="820" height="250" viewBox="0 0 820 250">
<rect width="820" height="250" fill="white"/><text x="35" y="30" font-family="sans-serif" font-size="20">Theoretical independent-trial cost counts</text>
<polyline points="{points_generation}" fill="none" stroke="#356ca8" stroke-width="4"/>
<polyline points="{points_judge}" fill="none" stroke="#d07a32" stroke-width="4"/>{labels}
<text x="550" y="50" font-family="sans-serif" font-size="13" fill="#356ca8">generated candidates / 4</text>
<text x="550" y="70" font-family="sans-serif" font-size="13" fill="#d07a32">Judge requests / 40</text></svg>"""
    path.write_text(svg, encoding="utf-8")


def report_e2(analysis_dir: Path, output_dir: Path) -> dict:
    metrics = json.loads((Path(analysis_dir) / "metrics.json").read_text(encoding="utf-8"))
    costs = json.loads((Path(analysis_dir) / "costs.json").read_text(encoding="utf-8"))
    output_dir = Path(output_dir).resolve()
    staging = output_dir.parent / f".{output_dir.name}.report.staging"
    failure = output_dir.parent / f"{output_dir.name}.report.failed"
    for path in (output_dir, staging, failure):
        if os.path.lexists(path):
            raise FileExistsError(f"E2 report path must be absent: {path}")
    staging.mkdir(parents=True)
    try:
        rows = costs["theoretical_independent_trials"]
        with (staging / "cost-curve.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        _write_win_svg(staging / "win-rate.svg", metrics)
        _write_cost_svg(staging / "cost-curve.svg", rows)
        overall = metrics["overall"]
        ci = overall["bootstrap_95_ci"]
        disclaimer = (
            "This bundle contains synthetic/mock engineering outputs and no research measurements."
            if metrics["research_measurements"] == 0
            else "This bundle is marked formal-command; verify server receipts and model identities before interpretation."
        )
        dimension_rows = "\n".join(
            f"| {dimension} | {value['tie_aware_win_rate']:.3f} | {value['decisive_win_rate']} | {value['tie_rate']:.3f} | {value['uncertain_rate']:.3f} |"
            for dimension, value in metrics["dimensions"].items()
        )
        markdown = f"""# E2 Best-of-N Pilot Report

{disclaimer}

## Primary human result

- comparisons: 80 (10 samples × 8 balanced rounds)
- N=4 tie-aware win rate: {overall['tie_aware_win_rate']:.3f}
- sample-cluster bootstrap 95% CI: [{ci['lower']:.3f}, {ci['upper']:.3f}]
- decisive win rate: {overall['decisive_win_rate']}
- tie rate: {overall['tie_rate']:.3f}; uncertain rate: {overall['uncertain_rate']:.3f}
- identical-selection automatic ties: {metrics['identical_selection_ties']}
- meets_m1_target: {str(metrics['meets_m1_target']).lower()} (target flag only, not an automatic significance claim)
- warnings: {', '.join(metrics['warnings']) if metrics['warnings'] else 'none'}

## Dimension preferences

| dimension | tie-aware N=4 rate | decisive N=4 rate | tie rate | uncertain rate |
|---|---:|---:|---:|---:|
{dimension_rows}

## Cost accounting

- shared pool candidates: {costs['actual_shared_eight_candidate_pool']['generated_candidates']}
- primary Judge requests: {costs['actual_shared_eight_candidate_pool']['primary_judge_requests']}
- auxiliary rubric requests: {costs['actual_shared_eight_candidate_pool']['auxiliary_rubric_requests']}
- actual amortized seconds per balanced trial: {costs['actual_shared_eight_candidate_pool']['amortized_seconds_per_balanced_trial']:.3f}

See `win-rate.svg`, `cost-curve.svg`, and `cost-curve.csv` for portable artifacts.
"""
        (staging / "E2_REPORT.md").write_text(markdown, encoding="utf-8", newline="\n")
        manifest = {
            "schema_version": "1", "analysis_metrics_sha256": sha256_file(Path(analysis_dir) / "metrics.json"),
            "analysis_costs_sha256": sha256_file(Path(analysis_dir) / "costs.json"),
            "research_measurements": metrics["research_measurements"],
            "artifacts": {
                path.name: sha256_file(path)
                for path in sorted(staging.iterdir()) if path.is_file()
            },
        }
        (staging / "report-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        _rename_noreplace(staging, output_dir)
    except Exception as exc:
        (staging / "REPORT_FAILED.json").write_text(
            json.dumps({"schema_version": "1", "status": "failed", "error": f"{type(exc).__name__}: {exc}"}, indent=2) + "\n",
            encoding="utf-8",
        )
        _rename_noreplace(staging, failure)
        raise
    return {"status": "passed", "output_dir": str(output_dir), "manifest": manifest}
