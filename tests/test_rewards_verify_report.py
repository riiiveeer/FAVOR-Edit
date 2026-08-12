import json
from pathlib import Path

from w1_pipeline.cache import Cache
from w1_pipeline.hashing import canonical_sha256
from w1_pipeline.models import RewardRequest
from w1_pipeline.rewards import reward_key


def test_reward_hash_includes_direction() -> None:
    base = dict(
        request_id="r1", candidate_a_checksum="a" * 64, candidate_b_checksum="b" * 64,
        instruction="edit", target_caption="edited", backend="mock", model="mock", prompt_version="v0",
    )
    forward = RewardRequest(**base, comparison_direction="a_vs_b")
    reverse = RewardRequest(**base, comparison_direction="b_vs_a")
    assert reward_key(forward) != reward_key(reverse)


def test_reward_cache_roundtrip(tmp_path: Path) -> None:
    key = canonical_sha256({"reward": 1})
    payload = {"reward_key": key}
    with Cache(tmp_path / "cache.sqlite3") as cache:
        cache.put_reward(key, "request", "succeeded", payload)
        assert cache.get_reward(key) == payload
