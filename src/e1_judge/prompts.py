"""Prompt loading, rendering, fingerprinting, and strict response parsing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from string import Template
from typing import Any, Dict, Tuple

import yaml

from .models import (
    AbsolutePayloadV2,
    PairwisePayloadV2,
    PromptSpecV2,
    RubricPayloadV2,
)


def prompt_checksum(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_prompt(path: Path) -> Tuple[PromptSpecV2, str]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"prompt file missing: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    spec = PromptSpecV2.model_validate(payload)
    required = {"instruction", "target_caption"}
    identifiers = set(Template(spec.user_template).get_identifiers())
    missing = required - identifiers
    if missing:
        raise ValueError(f"prompt {path} missing template variables: {sorted(missing)}")
    return spec, prompt_checksum(path)


def render_prompt(spec: PromptSpecV2, instruction: str, target_caption: str) -> str:
    user = Template(spec.user_template).substitute(
        instruction=instruction,
        target_caption=target_caption,
    )
    return f"{spec.system_prompt.strip()}\n\n{user.strip()}"


def parse_response(method: str, raw_text: str) -> Dict[str, Any]:
    """Parse a complete JSON response without fence stripping or semantic repair."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("judge response is empty")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"judge response is not strict JSON: {exc}") from exc
    if method == "absolute-v1":
        return AbsolutePayloadV2.model_validate(payload).model_dump(mode="json")
    if method in {"pairwise-single-v1", "pairwise-swap-v1"}:
        return PairwisePayloadV2.model_validate(payload).model_dump(mode="json")
    if method == "rubric-swap-v1":
        return RubricPayloadV2.model_validate(payload).model_dump(mode="json")
    raise ValueError(f"unknown judge method: {method}")
