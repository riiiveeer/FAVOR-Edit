import json
from pathlib import Path

from w1_pipeline.delivery import make_smoke_plan


def test_make_smoke_plan_selects_matching_inversion(tmp_path: Path) -> None:
    source = tmp_path / "plan.json"
    output = tmp_path / "smoke.json"
    source.write_text(
        json.dumps(
            {
                "inversions": [
                    {"sample_id": "a", "inversion_id": "inv-a"},
                    {"sample_id": "b", "inversion_id": "inv-b"},
                ],
                "candidates": [
                    {"sample_id": "b", "candidate_id": "b-s101"},
                    {"sample_id": "a", "candidate_id": "a-s101"},
                ],
            }
        ),
        encoding="utf-8",
    )
    make_smoke_plan(source, output)
    value = json.loads(output.read_text(encoding="utf-8"))
    assert value["candidates"] == [{"sample_id": "b", "candidate_id": "b-s101"}]
    assert value["inversions"] == [{"sample_id": "b", "inversion_id": "inv-b"}]


def test_offline_preflight_checks_required_resources() -> None:
    source = Path("scripts/offline_preflight.sh").read_text(encoding="utf-8")
    for required in (
        "robust-v2v-w1.bundle",
        "AnyV2V.bundle",
        "models/i2vgen-xl/model_index.json",
        "models/instruct-pix2pix/model_index.json",
        "metadata/SHA256SUMS",
        "A6000",
        "120 * 1024 * 1024",
    ):
        assert required in source


def test_delivery_manual_forbids_reusing_windows_manifest() -> None:
    source = Path("docs/SCHOOL_SERVER_DELIVERY.md").read_text(encoding="utf-8")
    assert "Windows 绝对路径" in source
    assert "服务器上重新运行 `w1 prepare`" in source
    assert "HF_HUB_OFFLINE=1" in source
