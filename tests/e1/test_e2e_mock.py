import json
from pathlib import Path

from e1_judge.runner import build_judge_plan, run_judge


def test_mock_e2e_550_requests_and_resume(e1_v2_fixture, tmp_path):
    runtime = Path(__file__).parents[2] / "configs" / "e1" / "runtime-mock.yaml"
    plan = tmp_path / "judge-plan.jsonl"
    requests = build_judge_plan(
        e1_v2_fixture["pairs_path"], e1_v2_fixture["packets_dir"], e1_v2_fixture["config"],
        runtime, plan, snapshot="test-snapshot",
    )
    assert len(requests) == 550
    assert sum(request["split"] == "dev" for request in requests) == 165
    assert sum(request["split"] == "frozen-eval" for request in requests) == 385
    assert len({request["judge_key"] for request in requests}) == 550
    absolute = [request for request in requests if request["method"] == "absolute-v1"]
    assert all(request["source"]["asset_id"] == request["sample_id"] for request in absolute)
    assert all(request["sample_id"] in request["instruction"] for request in absolute)

    experiment = tmp_path / "mock"
    cache = tmp_path / "cache.sqlite3"
    first = run_judge(plan, runtime, experiment, cache)
    assert first == {"selected": 550, "cache_hits": 0, "attempted": 550, "succeeded": 550, "failed": 0}
    second = run_judge(plan, runtime, experiment, cache)
    assert second == {"selected": 550, "cache_hits": 550, "attempted": 0, "succeeded": 550, "failed": 0}
    result_lines = (experiment / "results.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(result_lines) == 550
    assert all(json.loads(line)["raw_response"]["research_result"] is False for line in result_lines)
    raw_names = [path.name for path in (experiment / "raw-responses").glob("*.json")]
    assert len(raw_names) == 550 and all(len(name) == 69 for name in raw_names)
