"""Tests for E1 judge runner, cache, lock, and swap logic (§18.3, §18.4)."""

import json

import pytest

from e1_judge.cache import JudgeCache
from e1_judge.runner import (
    acquire_lock,
    build_judge_plan,
    judge_key,
    merge_results,
    release_lock,
    run_judge,
    unlock,
)


def _request(**overrides):
    base = dict(
        source_checksum="a" * 64,
        candidate_a_checksum="b" * 64,
        candidate_b_checksum="c" * 64,
        method="pairwise-swap-v1",
        comparison_direction="a_vs_b",
        backend="mock",
        model_name="mock",
        model_revision="v0",
        prompt_version="v1",
        parser_version="v1",
        media_packet_checksum="p" * 64,
        generation_parameters={},
    )
    base.update(overrides)
    return base


def test_judge_key_order_independent():
    a = _request()
    b = _request(candidate_b_checksum="c" * 64)
    assert judge_key(a) == judge_key(b)


def test_judge_key_direction_sensitive():
    a = _request(comparison_direction="a_vs_b")
    b = _request(comparison_direction="b_vs_a")
    assert judge_key(a) != judge_key(b)


def test_cache_roundtrip_and_hit(tmp_path):
    key = judge_key(_request())
    payload = {"request_id": "r1", "overall_preference": "a"}
    with JudgeCache(tmp_path / "cache.sqlite3") as cache:
        cache.put(key, "r1", "succeeded", payload)
        assert cache.get(key) == payload
        assert cache.get("0" * 64) is None


def test_lock_prevents_second_writer(tmp_path):
    experiment = tmp_path / "exp"
    acquire_lock(experiment)
    try:
        with pytest.raises(RuntimeError, match="lock exists"):
            acquire_lock(experiment)
    finally:
        release_lock(experiment)


def test_unlock_removes_lock(tmp_path):
    experiment = tmp_path / "exp"
    acquire_lock(experiment)
    unlock(experiment, "test reason")
    acquire_lock(experiment)
    release_lock(experiment)


def test_unlock_without_lock_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        unlock(tmp_path / "exp", "nope")


def _pair_lines():
    pair = dict(
        pair_id="bear-white-p01",
        sample_id="bear-white",
        task_type="attribute",
        instruction="Make the bear white",
        target_caption="A white bear walking",
        source_video_path="/tmp/source.mp4",
        source_checksum="a" * 64,
        mask_paths=[],
        candidate_left_id="bear-white-s101",
        candidate_left_checksum="b" * 64,
        candidate_left_path="/tmp/a.mp4",
        candidate_right_id="bear-white-s202",
        candidate_right_checksum="c" * 64,
        candidate_right_path="/tmp/b.mp4",
        canonical_candidate_a_id="bear-white-s101",
        canonical_candidate_b_id="bear-white-s202",
        display_direction="a_vs_b",
        split="dev",
        randomization_seed=0,
        pair_schema_version="1",
    )
    return [json.dumps(pair)]


def test_build_judge_plan_counts(tmp_path):
    pairs_path = tmp_path / "pairs.jsonl"
    pairs_path.write_text("\n".join(_pair_lines()) + "\n", encoding="utf-8")
    config_path = tmp_path / "pilot.yaml"
    config_path.write_text(
        "methods:\n"
        "  absolute-v1: {requests: 2, prompt: p1.yaml, swap: false}\n"
        "  pairwise-single-v1: {requests: 1, prompt: p2.yaml, swap: false}\n"
        "  pairwise-swap-v1: {requests: 2, prompt: p3.yaml, swap: true}\n"
        "  rubric-swap-v1: {requests: 2, prompt: p4.yaml, swap: true}\n"
        "total_requests: 7\n",
        encoding="utf-8",
    )
    output = tmp_path / "judge-plan.json"
    requests = build_judge_plan(pairs_path, config_path, output)
    assert len(requests) == 7
    # absolute: 2, single: 1, swap: 2, rubric-swap: 2
    assert sum(1 for r in requests if r["method"] == "absolute-v1") == 2
    assert sum(1 for r in requests if r["method"] == "pairwise-single-v1") == 1
    assert sum(1 for r in requests if r["method"] == "pairwise-swap-v1") == 2
    assert sum(1 for r in requests if r["method"] == "rubric-swap-v1") == 2


def test_run_judge_mock_and_resume(tmp_path):
    pairs_path = tmp_path / "pairs.jsonl"
    pairs_path.write_text("\n".join(_pair_lines()) + "\n", encoding="utf-8")
    config_path = tmp_path / "pilot.yaml"
    config_path.write_text(
        "methods:\n"
        "  pairwise-single-v1: {requests: 1, prompt: p2.yaml, swap: false}\n"
        "total_requests: 1\n",
        encoding="utf-8",
    )
    plan = tmp_path / "judge-plan.json"
    build_judge_plan(pairs_path, config_path, plan)
    completed = run_judge("mock", plan, tmp_path / "exp", tmp_path / "cache.sqlite3", None, None, None)
    assert completed == 1
    # Second run: cache hit.
    completed2 = run_judge("mock", plan, tmp_path / "exp", tmp_path / "cache.sqlite3", None, None, None)
    assert completed2 == 1


def test_merge_results_rejects_duplicates(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text(json.dumps({"request_id": "r1"}) + "\n", encoding="utf-8")
    b.write_text(json.dumps({"request_id": "r1"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        merge_results([a, b], tmp_path / "out.jsonl")


def test_merge_results_combines(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text(json.dumps({"request_id": "r1"}) + "\n", encoding="utf-8")
    b.write_text(json.dumps({"request_id": "r2"}) + "\n", encoding="utf-8")
    records = merge_results([a, b], tmp_path / "out.jsonl")
    assert len(records) == 2
