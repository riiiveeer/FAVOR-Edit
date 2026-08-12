"""W1 Markdown and pipeline diagram generation."""

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

from .models import CandidateRecord


MERMAID = """flowchart LR
    A[DAVIS 2017 train] --> B[Validate and prepare 10 inputs]
    B --> C[One DDIM inversion per input]
    C --> D[Five fixed seeds]
    D --> E[InstructPix2Pix first-frame edit]
    E --> F[AnyV2V PnP video edit]
    F --> G[50 candidate artifacts]
    G --> H[SQLite generation cache]
    G --> I[Reward mock/replay interface]
    I --> J[SQLite reward cache]
    G --> K[Verify and W1 report]
"""


def _svg() -> str:
    labels = ["DAVIS train", "Prepare 10 inputs", "10 inversions", "5 fixed seeds", "50 candidates", "Reward replay", "Verify/report"]
    width = 1320
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="130" viewBox="0 0 {width} 130">',
              '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#4b5563"/></marker></defs>',
              '<rect width="100%" height="100%" fill="white"/>']
    for index, label in enumerate(labels):
        x = 20 + index * 185
        pieces.append(f'<rect x="{x}" y="38" width="150" height="52" rx="8" fill="#eff6ff" stroke="#2563eb"/>')
        pieces.append(f'<text x="{x + 75}" y="69" text-anchor="middle" font-family="Arial" font-size="13">{label}</text>')
        if index < len(labels) - 1:
            pieces.append(f'<line x1="{x + 150}" y1="64" x2="{x + 180}" y2="64" stroke="#4b5563" marker-end="url(#arrow)"/>')
    pieces.append("</svg>")
    return "".join(pieces)


def generate_report(plan_path: Path, candidates_path: Path, rewards_path: Path, output_dir: Path) -> Path:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    candidates = [CandidateRecord.model_validate(value) for value in json.loads(candidates_path.read_text(encoding="utf-8"))]
    rewards = json.loads(rewards_path.read_text(encoding="utf-8")) if rewards_path.is_file() else []
    inputs: Dict[str, dict] = {task["sample_id"]: task["input"] for task in plan["candidates"]}
    statuses = Counter(candidate.status.value for candidate in candidates)
    backends = Counter(candidate.config.backend for candidate in candidates)
    runtimes = [candidate.runtime_seconds or 0 for candidate in candidates]
    cases: List[CandidateRecord] = []
    for task_type in ("attribute", "object", "local"):
        match = next((candidate for candidate in candidates if candidate.status.value == "succeeded" and inputs[candidate.sample_id]["task_type"] == task_type), None)
        if match:
            cases.append(match)
    failures = [candidate for candidate in candidates if candidate.status.value == "failed"][:2]

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pipeline.mmd").write_text(MERMAID, encoding="utf-8")
    (output_dir / "pipeline.svg").write_text(_svg(), encoding="utf-8")
    lines = [
        "# W1 Pipeline Report", "", "> Mock/replay outputs are interface tests, not research measurements.", "",
        "## Summary", "", f"- Inversions planned: {len(plan['inversions'])}",
        f"- Candidates: {len(candidates)} ({dict(statuses)})", f"- Backends: {dict(backends)}",
        f"- Reward records: {len(rewards)}", f"- Total candidate runtime: {sum(runtimes):.3f}s", "",
        "## Representative cases", "", "| Type | Candidate | Seed | Video |", "|---|---|---:|---|",
    ]
    for candidate in cases:
        case_type = inputs[candidate.sample_id]["task_type"]
        video = Path(candidate.video_path or "")
        relative = Path("..") / video.relative_to(output_dir.parent) if video.is_absolute() and output_dir.parent in video.parents else video
        lines.append(f"| {case_type} | {candidate.candidate_id} | {candidate.config.seed} | [{video.name}]({relative.as_posix()}) |")
    lines.extend(["", "## Failure cases", ""])
    if failures:
        lines.extend([f"- `{item.candidate_id}`: {item.error}" for item in failures])
    else:
        lines.append("- No failed candidates in this run; failure slots remain reserved for the real A6000 batch.")
    lines.extend(["", "## Traceability", "", f"- Plan: `{plan_path.resolve()}`", f"- Candidates: `{candidates_path.resolve()}`", f"- Rewards: `{rewards_path.resolve()}`", "- Diagram: `pipeline.mmd` and `pipeline.svg`", ""])
    report_path = output_dir / "W1_REPORT.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path

