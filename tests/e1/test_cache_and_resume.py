import json
import sys
from pathlib import Path

import pytest

from e1_judge.runner import acquire_lock, build_judge_plan, merge_results, release_lock, run_judge


def _write_command_runtime(path: Path, script: Path):
    path.write_text(
        "runtime_schema_version: '2'\n"
        "backend: command\n"
        "model:\n"
        "  name: fake-command-model\n"
        "  revision: fake-v1\n"
        f"  manifest_sha256: '{'1' * 64}'\n"
        "  local_path: fake-model\n"
        "adapter:\n"
        f"  python: '{sys.executable.replace(chr(92), '/')}'\n"
        f"  script: '{str(script).replace(chr(92), '/')}'\n"
        "  timeout_seconds: 30\n",
        encoding="utf-8",
    )


def _fake_adapter(path: Path):
    path.write_text(
        "import argparse,json\n"
        "from pathlib import Path\n"
        "p=argparse.ArgumentParser(); p.add_argument('--requests'); p.add_argument('--output-dir'); p.add_argument('--model-path'); a=p.parse_args()\n"
        "root=Path(__file__).parent; count=root/'invocations.txt'; count.write_text(str(int(count.read_text())+1) if count.exists() else '1')\n"
        "marker=root/'first-attempt.done'; out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)\n"
        "records=[json.loads(x) for x in Path(a.requests).read_text().splitlines() if x.strip()]\n"
        "for i,r in enumerate(records):\n"
        "  if not marker.exists() and i==0: continue\n"
        "  m=r['method']\n"
        "  if m=='absolute-v1': payload={'scores':{'faithfulness':2,'preservation':2,'temporal_consistency':2,'visual_quality':2},'overall_score':2,'confidence':.8,'evidence':'fake'}\n"
        "  elif m=='rubric-swap-v1':\n"
        "    d={'preference':'a','confidence':.8,'evidence':'fake'}; payload={'faithfulness':d,'preservation':d,'temporal_consistency':d,'visual_quality':d,'overall_preference':'a','overall_confidence':.8,'failure_tags_a':[],'failure_tags_b':[]}\n"
        "  else: payload={'overall_preference':'a','confidence':.8,'evidence':'fake'}\n"
        "  env={'schema_version':'2','request_id':r['request_id'],'judge_key':r['judge_key'],'status':'succeeded','raw_text':json.dumps(payload),'raw_response':{'research_result':False},'runtime_seconds':.01,'peak_vram_mb':10}\n"
        "  target=out/(r['judge_key']+'.json'); tmp=target.with_suffix('.tmp'); tmp.write_text(json.dumps(env)); tmp.replace(target)\n"
        "marker.write_text('done')\n",
        encoding="utf-8",
    )


def test_command_backend_one_batch_partial_resume_and_cache(e1_v2_fixture, tmp_path):
    script = tmp_path / "fake_adapter.py"
    runtime = tmp_path / "runtime-command.yaml"
    _fake_adapter(script)
    _write_command_runtime(runtime, script)
    plan = tmp_path / "plan.jsonl"
    requests = build_judge_plan(
        e1_v2_fixture["pairs_path"], e1_v2_fixture["packets_dir"], e1_v2_fixture["config"],
        runtime, plan, snapshot="test-snapshot",
    )
    assert len(requests) == 550
    experiment = tmp_path / "experiment"
    cache = tmp_path / "cache.sqlite3"
    first = run_judge(plan, runtime, experiment, cache)
    assert first == {"selected": 550, "cache_hits": 0, "attempted": 550, "succeeded": 549, "failed": 1}
    second = run_judge(plan, runtime, experiment, cache)
    assert second["attempted"] == 1 and second["succeeded"] == 550
    third = run_judge(plan, runtime, experiment, cache)
    assert third["cache_hits"] == 550 and third["attempted"] == 0
    assert (tmp_path / "invocations.txt").read_text() == "2"
    assert len((experiment / "results.jsonl").read_text().splitlines()) == 550


def test_active_lock_rejected_and_released(tmp_path):
    experiment = tmp_path / "locked"
    acquire_lock(experiment)
    with pytest.raises(RuntimeError, match="run lock exists"):
        acquire_lock(experiment)
    release_lock(experiment)
    assert not (experiment / ".e1-run.lock").exists()


def test_merge_rejects_mixed_runtime_generation_and_frozen_protocol(e1_v2_fixture, tmp_path):
    runtime = Path(__file__).parents[2] / "configs" / "e1" / "runtime-mock.yaml"
    plan = tmp_path / "mock-plan.jsonl"
    build_judge_plan(e1_v2_fixture["pairs_path"], e1_v2_fixture["packets_dir"], e1_v2_fixture["config"], runtime, plan, snapshot="test")
    experiment = tmp_path / "mock"
    run_judge(plan, runtime, experiment, tmp_path / "cache.sqlite3", split="dev")
    records = [json.loads(line) for line in (experiment / "results.jsonl").read_text().splitlines()]
    variants = {
        "runtime": lambda record: record.update(runtime_fingerprint="f" * 64),
        "generation": lambda record: record["generation_parameters"].update(max_new_tokens=999),
        "frozen-protocol": lambda record: record.update(frozen_protocol_fingerprint="e" * 64),
        "model-manifest": lambda record: record.update(model_manifest_sha256="d" * 64),
    }
    for name, mutate in variants.items():
        first = tmp_path / f"first-{name}.jsonl"
        second = tmp_path / f"second-{name}.jsonl"
        first.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
        changed = json.loads(json.dumps(records[1]))
        mutate(changed)
        second.write_text(json.dumps(changed) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="mixed"):
            merge_results([first, second], tmp_path / f"merged-{name}.jsonl")
