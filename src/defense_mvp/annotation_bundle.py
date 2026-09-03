"""Read-only D2 identity validation and no-replace private annotation bundles."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import yaml

from w1_pipeline.hashing import canonical_sha256, sha256_file

from .annotation_models import (
    ANNOTATORS, CONFIG, FAMILIES, PROTOCOL, AutomaticTie, Comparison, Display,
)
from .config import load_config
from .design import cyclic_trials, load_metric_rows
from .ingest import _package_file
from .io import rename_noreplace, write_json
from .models import PackageCandidateV1, PackageSampleV1, validate_relative_path
from .selection import METHODS

PINS = {
    "pilot": "19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae",
    "ingest": "b0eee7ab41aff575220957fae4dd67afd0fbaac85e4f756d023a9e42929f0b46",
    "comparisons": "486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb",
    "selection_lock": "99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path):
    # Duplicate keys are corruption, even if a decoder would normally keep the last one.
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def verify_sums(root: Path, name: str = "SHA256SUMS") -> dict:
    root = Path(root)
    inventory = {}
    for line in (root / name).read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        validate_relative_path(relative)
        if relative in inventory or len(digest) != 64:
            raise ValueError("invalid checksum inventory")
        if sha256_file(_package_file(root, relative)) != digest:
            raise ValueError("artifact checksum mismatch")
        inventory[relative] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if set(inventory) != actual - {name} or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("artifact inventory mismatch")
    return inventory


def write_sums(root: Path) -> None:
    paths = sorted(p for p in root.rglob("*") if p.is_file())
    with (root / "SHA256SUMS").open("x", encoding="utf-8", newline="\n") as handle:
        for path in paths:
            handle.write(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n")
        handle.flush()
        os.fsync(handle.fileno())


def stage(output: Path) -> Path:
    output = Path(output)
    if os.path.lexists(output):
        raise FileExistsError("output already exists; choose a new directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(f".{output.name}-{uuid.uuid4().hex}.staging")
    staging.mkdir()
    return staging


def source_evidence() -> dict:
    repo = Path(__file__).resolve().parents[2]
    paths = list((repo / "src/defense_mvp").glob("*.py"))
    paths += list((repo / "src/defense_mvp").glob("*.html"))
    paths += list((repo / "src/defense_mvp").glob("*.js"))
    paths += [repo / "pyproject.toml", repo / "uv.lock"]
    return {
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "code_files": {p.relative_to(repo).as_posix(): sha256_file(p) for p in sorted(paths) if p.is_file()},
        "python": sys.version, "platform": platform.platform(),
        "dependencies": {p: version(p) for p in ("pydantic", "pyyaml", "typer", "numpy", "pillow")},
    }


def _check_link(lock: dict, key: str, path: Path) -> None:
    if lock.get(key) != sha256_file(path):
        raise ValueError(f"input lock mismatch: {key}")


def validate_inputs(selection: Path, ingest: Path, metrics: Path, design: Path, pilot: Path, mode: str) -> dict:
    if mode not in ("formal", "practice"):
        raise ValueError("invalid annotation mode")
    paths = {"pilot": pilot, "ingest": ingest, "comparisons": selection / "comparisons.json",
             "selection_lock": selection / "selection-lock.json"}
    if mode == "formal":
        for name, digest in PINS.items():
            if sha256_file(paths[name]) != digest:
                raise ValueError(f"frozen formal input drift: {name}")
    for directory, sums in ((selection, "SELECTION_SHA256SUMS"), (ingest.parent, "INGEST_SHA256SUMS"),
                            (metrics, "METRICS_SHA256SUMS"), (design, "DESIGN_SHA256SUMS")):
        for relative in verify_sums(directory, sums):
            paths[str((directory / relative).resolve())] = directory / relative
        paths[str((directory / sums).resolve())] = directory / sums
    cfg = load_config(pilot)
    manifest, plan = read_json(ingest), read_json(paths["comparisons"])
    if manifest["experiment_id"] != "DEFENSE-MVP-v01" or plan["experiment_id"] != "DEFENSE-MVP-v01":
        raise ValueError("experiment identity mismatch")
    root = Path(manifest["delivery_root"])
    if plan["delivery_root"] != str(root) or not root.is_absolute():
        raise ValueError("delivery root mismatch")
    if manifest["primary_sample_ids"] != cfg.primary_sample_ids or manifest["qualitative_sample_ids"] != cfg.qualitative_sample_ids:
        raise ValueError("sample scope mismatch")
    samples = [PackageSampleV1.model_validate(v) for v in manifest["samples"]]
    candidates = [PackageCandidateV1.model_validate(v) for v in manifest["candidates"]]
    if [s.sample_id for s in samples] != cfg.sample_ids:
        raise ValueError("sample matrix mismatch")
    if [(c.sample_id, c.seed) for c in candidates] != [(s, seed) for s in cfg.sample_ids for seed in cfg.seeds]:
        raise ValueError("candidate matrix mismatch")
    by_candidate = {c.candidate_id: c for c in candidates}
    by_sample = {s.sample_id: s for s in samples}
    if len(by_candidate) != 50:
        raise ValueError("candidate IDs not unique")
    media_inventory = {}
    for ref in [s.source_video for s in samples] + [c.video for c in candidates]:
        path = _package_file(root, ref.relative_path)
        if sha256_file(path) != ref.sha256:
            raise ValueError("media identity mismatch")
        if ref.relative_path in media_inventory:
            raise ValueError("media path reused")
        media_inventory[ref.relative_path] = ref.sha256
    # Validate the entire linked D2 artifact chain, without rerunning D2 algorithms.
    selection_lock = read_json(paths["selection_lock"])
    design_path, metrics_path = design / "design.json", metrics / "metrics.jsonl"
    design_lock, metric_lock = read_json(design / "design-lock.json"), read_json(metrics / "metrics-config-lock.json")
    for lock in (selection_lock, design_lock, metric_lock):
        _check_link(lock, "config_sha256", pilot)
    for lock in (selection_lock, design_lock):
        _check_link(lock, "metrics_sha256", metrics_path)
        _check_link(lock, "design_sha256", design_path)
    for lock in (design_lock, metric_lock):
        _check_link(lock, "ingest_manifest_sha256", ingest)
    _check_link(selection_lock, "comparisons_sha256", paths["comparisons"])
    _check_link(selection_lock, "selections_sha256", selection / "selections.jsonl")
    if metric_lock.get("package_manifest_sha256") != manifest["package_manifest_sha256"]:
        raise ValueError("package identity mismatch")
    data = read_json(design_path)
    _check_link(data, "metrics_sha256", metrics_path)
    _check_link(data, "ingest_manifest_sha256", ingest)
    if data["delivery_root"] != str(root):
        raise ValueError("design delivery mismatch")
    expected_trials, expected_samples = [], []
    for sample_id in cfg.primary_sample_ids:
        sample = by_sample[sample_id]
        cs = [c for c in candidates if c.sample_id == sample_id]
        expected_trials += cyclic_trials(sample_id, [c.candidate_id for c in cs])
        expected_samples.append({"sample_id": sample_id, "instruction": sample.instruction,
                                "target_caption": sample.target_caption,
                                "source_video": sample.source_video.model_dump(mode="json"),
                                "candidates": [{"candidate_id": c.candidate_id, "seed": c.seed,
                                                "video": c.video.model_dump(mode="json")} for c in cs]})
    if data["trials"] != expected_trials or data["samples"] != expected_samples:
        raise ValueError("design/ingest relationship mismatch")
    rows = load_metric_rows(metrics_path, pilot)
    metric_by_id = {r["candidate_id"]: r for r in rows}
    for c in candidates:
        r = metric_by_id.get(c.candidate_id, {})
        if (r.get("sample_id"), r.get("seed"), r.get("candidate_video_sha256")) != (c.sample_id, c.seed, c.video.sha256):
            raise ValueError("metric candidate mismatch")
    selections = [json.loads(line) for line in (selection / "selections.jsonl").read_text(encoding="utf-8").splitlines()]
    lookup = {(r["trial_id"], r["n"], r["method"]): r for r in selections}
    keys = {(t["trial_id"], n, m) for t in expected_trials for n in (1, 2, 4) for m in METHODS}
    if len(selections) != 315 or set(lookup) != keys:
        raise ValueError("selection matrix mismatch")
    for t in expected_trials:
        for n in (1, 2, 4):
            for m in METHODS:
                r = lookup[t["trial_id"], n, m]
                c = by_candidate.get(r["candidate_id"])
                if (c is None or c.sample_id != t["sample_id"] or r["sample_id"] != c.sample_id
                        or r["replicate"] != t["replicate"] or r["subset_candidate_ids"] != t["subsets"][str(n)]
                        or c.candidate_id not in r["subset_candidate_ids"]
                        or r["candidate_video_sha256"] != c.video.sha256
                        or r["raw_scores"] != metric_by_id[c.candidate_id]["scores"]):
                    raise ValueError("selection candidate relationship mismatch")
    comparisons = [Comparison.model_validate(c) for c in plan["comparisons"]]
    expected_ids = {f"defense:{family}:{s}:r{r}" for s in cfg.primary_sample_ids
                    for family, count in zip(FAMILIES, (4, 2)) for r in range(1, count + 1)}
    if len(comparisons) != 42 or {c.comparison_id for c in comparisons} != expected_ids:
        raise ValueError("42 comparison identity matrix mismatch")
    ties = dict.fromkeys(FAMILIES, 0)
    for c in comparisons:
        sample = by_sample[c.sample_id]
        if c.sample_id not in cfg.primary_sample_ids or c.comparison_id != f"defense:{c.family}:{c.sample_id}:r{c.replicate}":
            raise ValueError("comparison scope mismatch")
        if c.trial_id != f"defense:{c.sample_id}:r{c.replicate}" or (c.family == FAMILIES[1] and c.replicate > 2):
            raise ValueError("comparison trial mismatch")
        if c.instruction != sample.instruction or c.target_caption != sample.target_caption or c.source_video != sample.source_video:
            raise ValueError("comparison source mismatch")
        spec = [(c.candidate_x, 4, "constrained-pareto"),
                (c.candidate_y, 1, "constrained-pareto") if c.family == FAMILIES[0]
                else (c.candidate_y, 4, "equal-linear")]
        for side, n, method in spec:
            candidate = by_candidate.get(side.candidate_id)
            if (candidate is None or candidate.sample_id != c.sample_id or side.video != candidate.video
                    or side.role != f"{method}-n{n}"
                    or lookup[c.trial_id, n, method]["candidate_id"] != side.candidate_id):
                raise ValueError("comparison candidate/role mismatch")
        identical = c.candidate_x.video.sha256 == c.candidate_y.video.sha256
        if identical != c.identical_selection:
            raise ValueError("automatic tie identity mismatch")
        ties[c.family] += identical
    if mode == "formal" and list(ties.values()) != [6, 4]:
        raise ValueError("formal automatic tie counts drifted")
    return {"comparisons": [c.model_dump(mode="json") for c in comparisons],
            "delivery_root": str(root), "media_inventory": media_inventory,
            "inputs": {str(p.resolve()): sha256_file(p) for p in paths.values()}}


def derived_hash(annotator: str, comparison_id: str, purpose: str) -> str:
    return canonical_sha256({"protocol": PROTOCOL, "seed": 20260901, "annotator_id": annotator,
                             "comparison_id": comparison_id, "purpose": purpose})


def mapping_for(comparisons: list, annotator: str) -> list:
    if annotator not in ANNOTATORS:
        raise ValueError("unknown annotator")
    directions = {}
    for family in FAMILIES:
        ids = [c["comparison_id"] for c in comparisons if c["family"] == family and not c["identical_selection"]]
        ids.sort(key=lambda cid: (derived_hash(annotator, cid, "direction"), cid))
        directions.update({cid: "A" if i < len(ids) // 2 else "B" for i, cid in enumerate(ids)})
    ids = sorted(directions, key=lambda cid: (derived_hash(annotator, cid, "order"), cid))
    return [Display(comparison_id=cid, position=i + 1, x_as=directions[cid]).model_dump()
            for i, cid in enumerate(ids)]


def automatic_ties(comparisons: list) -> list:
    return [AutomaticTie(comparison_id=c["comparison_id"], source="automatic_tie", reason="media_identity",
                         media_sha256=c["candidate_x"]["video"]["sha256"], outcome="tie").model_dump()
            for c in sorted(comparisons, key=lambda c: c["comparison_id"])
            if c["candidate_x"]["video"]["sha256"] == c["candidate_y"]["video"]["sha256"]]


def prepare_annotation(selection: Path, ingest: Path, output: Path, mode: str,
                       config: Path = Path("configs/defense_mvp/annotation-v1.yaml"),
                       pilot: Path = Path("configs/defense_mvp/pilot.yaml"),
                       metrics: Path = None, design: Path = None, fixture_native_media: bool = False) -> dict:
    selection, ingest, output = Path(selection).resolve(), Path(ingest).resolve(), Path(output).resolve()
    staging = stage(output)
    try:
        from .annotation_media import create_presentation
        if fixture_native_media and mode != "practice":
            raise ValueError("fixture native media is practice-only")
        if yaml.safe_load(config.read_text(encoding="utf-8")) != CONFIG:
            raise ValueError("annotation protocol configuration drifted")
        data = validate_inputs(selection, ingest, Path(metrics or selection.parent / "metrics"),
                               Path(design or selection.parent / "design"), pilot, mode)
        data["input_locations"] = {"selection": str(selection), "ingest": str(ingest),
                                   "metrics": str(Path(metrics or selection.parent / "metrics").resolve()),
                                   "design": str(Path(design or selection.parent / "design").resolve()),
                                   "pilot": str(pilot.resolve())}
        data.update(create_presentation(data, staging, fixture_native_media))
        mapping = {a: mapping_for(data["comparisons"], a) for a in ANNOTATORS}
        write_json(staging / "private-mapping.json", mapping)
        write_json(staging / "automatic-ties.json", automatic_ties(data["comparisons"]))
        data.update({"protocol": PROTOCOL, "config": CONFIG, "protocol_sha256": canonical_sha256(CONFIG),
                     "mode": mode, "mapping_sha256": sha256_file(staging / "private-mapping.json"),
                     "automatic_sha256": sha256_file(staging / "automatic-ties.json")})
        data["inputs"][str(config.resolve())] = sha256_file(config)
        write_json(staging / "bundle.json", data)
        receipt = {"status": "prepared", "mode": mode, "created_at": now(),
                   "bundle_sha256": sha256_file(staging / "bundle.json"), "comparisons": 42,
                   "automatic_ties": len(automatic_ties(data["comparisons"])),
                   "manual_per_annotator": len(mapping["annotator-a"]), "formal_answers": 0,
                   "environment": source_evidence()}
        write_json(staging / "prepare-receipt.json", receipt)
        write_sums(staging)
        rename_noreplace(staging, output)
        return receipt
    except Exception as exc:
        write_json(staging / "FAILED.json", {"status": "failed", "error": str(exc), "at": now()})
        raise


def load_bundle(path: Path) -> dict:
    from .annotation_media import PRESENTATION, comparison_refs
    path = Path(path)
    verify_sums(path)
    data = read_json(path / "bundle.json")
    if data["protocol"] != PROTOCOL or data["config"] != CONFIG or data["protocol_sha256"] != canonical_sha256(CONFIG):
        raise ValueError("bundle protocol drifted")
    if data["mode"] not in ("formal", "practice"):
        raise ValueError("bundle mode invalid")
    checked = validate_inputs(**{k: Path(v) for k, v in data["input_locations"].items()}, mode=data["mode"])
    for key in ("comparisons", "delivery_root", "media_inventory"):
        if checked[key] != data[key]:
            raise ValueError("bundle/input relationship drifted")
    if any(data["inputs"].get(k) != v for k, v in checked["inputs"].items()):
        raise ValueError("bundle input inventory drifted")
    for name, digest in data["inputs"].items():
        if sha256_file(Path(name)) != digest:
            raise ValueError("bundle external input drifted")
    for relative, digest in data["media_inventory"].items():
        if sha256_file(_package_file(Path(data["delivery_root"]), relative)) != digest:
            raise ValueError("bundle media drifted")
    mapping = read_json(path / "private-mapping.json")
    if mapping != {a: mapping_for(data["comparisons"], a) for a in ANNOTATORS}:
        raise ValueError("bundle display mapping drifted")
    if read_json(path / "automatic-ties.json") != automatic_ties(data["comparisons"]):
        raise ValueError("bundle automatic rules drifted")
    _check_link(data, "mapping_sha256", path / "private-mapping.json")
    _check_link(data, "automatic_sha256", path / "automatic-ties.json")
    receipt = read_json(path / "prepare-receipt.json")
    _check_link(receipt, "bundle_sha256", path / "bundle.json")
    refs = comparison_refs(data)
    if set(data["presentation_media"]) != set(refs):
        raise ValueError("presentation inventory mismatch")
    if data["presentation_mode"] == "fixture-native-v1":
        if data["mode"] != "practice" or data["presentation_proof_sha256"] is not None:
            raise ValueError("fixture presentation cannot be formal")
        if data["presentation_media"] != {p: {"relative_path": p, "sha256": h} for p, h in refs.items()}:
            raise ValueError("fixture presentation identity mismatch")
        data["presentation_root"] = data["delivery_root"]
    elif data["presentation_mode"] == PRESENTATION:
        _check_link(data, "presentation_proof_sha256", path / "presentation-proof.json")
        proof = read_json(path / "presentation-proof.json")
        if proof["protocol"] != PRESENTATION or len(proof["media"]) != len(refs):
            raise ValueError("presentation proof mismatch")
        if {p["original_relative_path"] for p in proof["media"]} != set(refs):
            raise ValueError("presentation proof inventory mismatch")
        for item in proof["media"]:
            relative = item["original_relative_path"]
            ref = data["presentation_media"][relative]
            if (item["original_sha256"] != refs[relative] or item["presentation"] != ref
                    or sha256_file(_package_file(path, ref["relative_path"])) != ref["sha256"]):
                raise ValueError("presentation proof/media identity mismatch")
        data["presentation_root"] = str(path.resolve())
    else:
        raise ValueError("unknown presentation protocol")
    data["sha256"] = sha256_file(path / "bundle.json")
    data["mapping"] = mapping
    return data
