"""End-to-end mock E2E test (§18.7): 100 pairs -> 550 requests -> 550 results."""

import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pytest

from e1_judge.pairs import build_pairs
from e1_judge.runner import build_judge_plan, run_judge

SAMPLES = [
    ("bear-white", "attribute"),
    ("bus-red", "attribute"),
    ("elephant-pink", "attribute"),
    ("classic-car-blue", "attribute"),
    ("dog-tiger", "object"),
    ("horse-zebra", "object"),
    ("mallard-swan", "object"),
    ("hiker-backpack", "local"),
    ("rider-helmet", "local"),
    ("car-headlights", "local"),
]
SEEDS = [101, 202, 303, 404, 505]
SIZE = (32, 32)


def _checksum(path: Path) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _video(path: Path, base: int, n: int = 16) -> None:
    with imageio.get_writer(path, fps=8, codec="libx264", quality=8, macro_block_size=None) as writer:
        for i in range(n):
            writer.append_data(np.full((SIZE[1], SIZE[0], 3), (base + i) % 255, dtype=np.uint8))


@pytest.fixture(scope="module")
def e0_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("e0-e2e")
    media = root / "media"
    media.mkdir()

    inversions = []
    plan_candidates = []
    candidates = []

    for sample_id, task_type in SAMPLES:
        sample_dir = media / sample_id
        sample_dir.mkdir(parents=True)
        source = sample_dir / "source.mp4"
        _video(source, 0)
        inversions.append({"sample_id": sample_id, "source_video_path": str(source), "source_checksum": "a" * 64})
        for seed in SEEDS:
            cid = f"{sample_id}-s{seed}"
            video = sample_dir / f"seed-{seed}.mp4"
            _video(video, seed * 1000 + SAMPLES.index((sample_id, task_type)))
            plan_candidates.append(
                {
                    "candidate_id": cid,
                    "sample_id": sample_id,
                    "input": {
                        "sample_id": sample_id,
                        "task_type": task_type,
                        "instruction": f"instruction for {sample_id}",
                        "target_caption": f"target caption for {sample_id}",
                        "source_video_path": str(source),
                        "source_checksum": "a" * 64,
                        "mask_frame_paths": [],
                    },
                }
            )
            candidates.append(
                {"candidate_id": cid, "sample_id": sample_id, "video_path": str(video), "video_checksum": _checksum(video)}
            )

    plan_path = root / "plan.json"
    candidates_path = root / "candidates.json"
    plan_path.write_text(json.dumps({"inversions": inversions, "candidates": plan_candidates}), encoding="utf-8")
    candidates_path.write_text(json.dumps(candidates), encoding="utf-8")

    audit_path = root / "audit.csv"
    with audit_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("candidate_id,faithfulness,preservation,temporal_consistency,visual_quality,failure_tags,systematic_failure,usable_for_e1,reviewer,reviewed_at,notes\n")
        for record in candidates:
            handle.write(f"{record['candidate_id']},2,2,2,2,,,,yes,anon-01,2026-08-23,\n")

    config_path = root / "pilot.yaml"
    config_path.write_text(
        "dataset: DAVIS-2017\n"
        "split: train\n"
        "dev_samples: [bear-white, dog-tiger, hiker-backpack]\n"
        "frozen_eval_samples: [bus-red, elephant-pink, classic-car-blue, horse-zebra, mallard-swan, rider-helmet, car-headlights]\n",
        encoding="utf-8",
    )
    return root, plan_path, candidates_path, audit_path, config_path


def _full_pilot_config(path: Path) -> None:
    path.write_text(
        "dataset: DAVIS-2017\n"
        "split: train\n"
        "dev_samples: [bear-white, dog-tiger, hiker-backpack]\n"
        "frozen_eval_samples: [bus-red, elephant-pink, classic-car-blue, horse-zebra, mallard-swan, rider-helmet, car-headlights]\n"
        "methods:\n"
        "  absolute-v1: {requests: 50, prompt: prompt-absolute-v1.yaml, swap: false}\n"
        "  pairwise-single-v1: {requests: 100, prompt: prompt-pairwise-single-v1.yaml, swap: false}\n"
        "  pairwise-swap-v1: {requests: 200, prompt: prompt-pairwise-swap-v1.yaml, swap: true}\n"
        "  rubric-swap-v1: {requests: 200, prompt: prompt-rubric-swap-v1.yaml, swap: true}\n"
        "total_requests: 550\n"
        "bootstrap_seed: 20260820\n"
        "bootstrap_iterations: 2000\n",
        encoding="utf-8",
    )


def test_mock_e2e_550_requests(e0_fixture, tmp_path):
    _, plan, candidates, audit, config = e0_fixture
    full_config = tmp_path / "pilot-full.yaml"
    _full_pilot_config(full_config)

    pairs_path = tmp_path / "pairs.jsonl"
    pairs = build_pairs(plan, candidates, audit, full_config, pairs_path)
    assert len(pairs) == 100

    judge_plan = tmp_path / "judge-plan.json"
    requests = build_judge_plan(pairs_path, full_config, judge_plan)
    assert len(requests) == 550

    completed = run_judge("mock", judge_plan, tmp_path / "mock", tmp_path / "cache.sqlite3", None, None, None)
    assert completed == 550

    # Cache hit on second run.
    completed2 = run_judge("mock", judge_plan, tmp_path / "mock", tmp_path / "cache.sqlite3", None, None, None)
    assert completed2 == 550

    # Every result carries research_result=false (mock, not research measurement).
    results_dir = tmp_path / "mock" / "results"
    result_files = list(results_dir.glob("*.result.json"))
    assert len(result_files) == 550
    for path in result_files:
        result = json.loads(path.read_text())
        assert result.get("raw_response", {}).get("research_result") is False
        assert result.get("confidence") == 0.0
