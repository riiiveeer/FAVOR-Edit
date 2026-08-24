"""E1 report generation."""

import json
from pathlib import Path


def generate_report(analysis: Path, output_dir: Path) -> Path:
    """Write a minimal E1 report from analysis/metrics.json."""
    metrics_path = Path(analysis) / "metrics.json"
    if not metrics_path.is_file():
        raise FileNotFoundError(f"metrics.json missing in {analysis}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    pairwise = metrics.get("pairwise", {})
    swap = metrics.get("swap_consistency", 0.0)
    bias = metrics.get("position_bias", {})
    categories = metrics.get("categories", {})

    lines = [
        "# E1 Judge Reliability Report",
        "",
        "## Summary",
        "",
        f"- decisive accuracy: {pairwise.get('decisive_accuracy', 0.0):.3f}",
        f"- effective accuracy: {pairwise.get('effective_accuracy', 0.0):.3f}",
        f"- coverage: {pairwise.get('coverage', 0.0):.3f}",
        f"- swap consistency: {swap:.3f}",
        f"- left choice rate: {bias.get('left_rate', 0.0):.3f}",
        f"- right choice rate: {bias.get('right_rate', 0.0):.3f}",
        "",
        "## Category metrics",
        "",
    ]
    for task_type, values in categories.items():
        lines.append(f"- {task_type}: pairs={values.get('pairs', 0)}, accuracy={values.get('decisive_accuracy', 0.0):.3f}")

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_path = Path(output_dir) / "E1_REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path
