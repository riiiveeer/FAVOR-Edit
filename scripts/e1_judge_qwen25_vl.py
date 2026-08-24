"""Offline Qwen2.5-VL-7B batch adapter for the E1 command-backend contract.

Heavy dependencies are imported only after CLI parsing so ``--help`` remains usable
from the lightweight control environment.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def _atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _video_content(label: str, media: dict, generation: dict) -> list:
    frame_uris = [Path(path).resolve().as_uri() for path in media["frame_paths"]]
    return [
        {"type": "text", "text": label},
        {
            "type": "video", "video": frame_uris,
            "fps": float(generation.get("fps", 8.0)),
            "max_pixels": int(generation.get("max_pixels", 65536)),
        },
    ]


def _messages(request: dict) -> list:
    content = []
    content.extend(_video_content("SOURCE VIDEO", request["source"], request["generation_parameters"]))
    content.extend(_video_content("CANDIDATE A", request["candidate_a"], request["generation_parameters"]))
    if request.get("candidate_b"):
        content.extend(_video_content("CANDIDATE B", request["candidate_b"], request["generation_parameters"]))
    if request.get("mask_overlay"):
        content.extend([
            {"type": "text", "text": "TARGET MASK OVERLAY"},
            {"type": "image", "image": Path(request["mask_overlay"]["path"]).resolve().as_uri()},
        ])
    content.append({"type": "text", "text": request["rendered_prompt"]})
    return [{"role": "user", "content": content}]


def run(requests_path: Path, output_dir: Path, model_path: Path) -> int:
    import torch
    from qwen_vl_utils import process_vision_info
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        str(model_path), torch_dtype=torch.bfloat16, device_map="cuda:0",
        attn_implementation="sdpa", local_files_only=True,
    ).eval()
    processor = AutoProcessor.from_pretrained(str(model_path), local_files_only=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for line in requests_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        request = json.loads(line)
        target = output_dir / f"{request['judge_key']}.json"
        started = time.perf_counter()
        torch.cuda.reset_peak_memory_stats()
        try:
            messages = _messages(request)
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = processor(
                text=[text], images=image_inputs, videos=video_inputs,
                padding=True, return_tensors="pt",
            ).to("cuda")
            generation = request["generation_parameters"]
            generated = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=int(generation.get("max_new_tokens", 512)),
            )
            trimmed = generated[:, inputs.input_ids.shape[1]:]
            raw_text = processor.batch_decode(
                trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False,
            )[0]
            envelope = {
                "schema_version": "2", "request_id": request["request_id"],
                "judge_key": request["judge_key"], "status": "succeeded",
                "raw_text": raw_text,
                "raw_response": {"adapter": "qwen2.5-vl-7b", "research_result": True},
                "runtime_seconds": time.perf_counter() - started,
                "peak_vram_mb": torch.cuda.max_memory_allocated() / (1024 * 1024),
            }
        except Exception as exc:  # persist one failure and continue the batch
            failures += 1
            envelope = {
                "schema_version": "2", "request_id": request["request_id"],
                "judge_key": request["judge_key"], "status": "failed",
                "error": f"{type(exc).__name__}: {exc}", "raw_response": {},
                "runtime_seconds": time.perf_counter() - started,
                "peak_vram_mb": torch.cuda.max_memory_allocated() / (1024 * 1024),
            }
        _atomic_json(target, envelope)
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Qwen2.5-VL E1 batch adapter")
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    args = parser.parse_args()
    return run(args.requests, args.output_dir, args.model_path)


if __name__ == "__main__":
    raise SystemExit(main())
