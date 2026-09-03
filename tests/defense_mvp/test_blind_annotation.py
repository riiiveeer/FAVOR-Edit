"""D3 engineering tests: synthetic bytes and answers are always practice-only."""

import copy
import http.client
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from collections import Counter
from pathlib import Path

import pytest
from typer.testing import CliRunner

from defense_mvp.annotation_bundle import (
    automatic_ties, load_bundle, mapping_for, prepare_annotation, read_json, validate_inputs, write_sums,
)
from defense_mvp.annotation_export import export_annotations, verify_annotations
from defense_mvp.annotation_models import ANNOTATORS, FAMILIES, FIELDS, Answers, canonical_answers
from defense_mvp.annotation_server import AnnotationHTTPServer, byte_range
from defense_mvp.annotation_store import AnnotationStore, Conflict, WriterLock
from defense_mvp.cli import app
from defense_mvp.design import create_design
from defense_mvp.ingest import ingest_delivery
from defense_mvp.io import write_json
from defense_mvp.selection import select_design
from w1_pipeline.hashing import sha256_file

PILOT = Path("configs/defense_mvp/pilot.yaml")
_dataset = None


@pytest.fixture
def ann_data(handoff_factory, tmp_path):
    # A shared immutable input fixture; each session/test output uses its own tmp_path.
    global _dataset
    if _dataset is None:
        root = tmp_path / "fixture"
        root.mkdir()
        ingest_delivery(handoff_factory(), PILOT, root / "ingest")
        manifest = read_json(root / "ingest/normalized-manifest.json")
        (root / "metrics").mkdir()
        metrics = root / "metrics/metrics.jsonl"
        rows = []
        for c in manifest["candidates"]:
            primary = c["sample_id"] in manifest["primary_sample_ids"]
            value = [101, 202, 303, 404, 505].index(c["seed"]) / 4
            rows.append({"candidate_id": c["candidate_id"], "sample_id": c["sample_id"], "seed": c["seed"],
                         "candidate_video_sha256": c["video"]["sha256"],
                         "measurement_status": "scored" if primary else "qualitative_only",
                         "scores": {"F": value, "P": 1 - value, "T": value, "Q": 1 - value} if primary else None})
        metrics.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        write_json(root / "metrics/metrics-config-lock.json", {
            "config_sha256": sha256_file(PILOT),
            "ingest_manifest_sha256": sha256_file(root / "ingest/normalized-manifest.json"),
            "package_manifest_sha256": manifest["package_manifest_sha256"],
        })
        write_sums(root / "metrics")
        (root / "metrics/SHA256SUMS").rename(root / "metrics/METRICS_SHA256SUMS")
        create_design(metrics, root / "ingest/normalized-manifest.json", PILOT, root / "design")
        select_design(root / "design/design.json", metrics, PILOT, root / "selection")
        prepare_annotation(root / "selection", root / "ingest/normalized-manifest.json", root / "bundle", "practice", fixture_native_media=True)
        _dataset = root
    return _dataset


def answers(value="A", **overrides):
    return {**dict.fromkeys(FIELDS, value), "confidence": 0.75, "notes": "fixture only", **overrides}


def view_ready(store):
    view = store.open_view()
    view["media_served"] = {"source", "A", "B"}
    view["ready"] = True
    return view


def finish(store):
    while len(store.records) < len(store.mapping):
        store.submit(view_ready(store)["handle"], answers(), uuid.uuid4().hex)


def store_for(ann_data, tmp_path, annotator="annotator-a", **kwargs):
    return AnnotationStore(ann_data / "bundle", annotator, tmp_path / annotator, **kwargs)


def rewrite(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rechain(root):
    ingest, metrics, design, selection = (root / n for n in ("ingest", "metrics", "design", "selection"))
    metric_lock = read_json(metrics / "metrics-config-lock.json")
    metric_lock["ingest_manifest_sha256"] = sha256_file(ingest / "normalized-manifest.json")
    rewrite(metrics / "metrics-config-lock.json", metric_lock)
    d = read_json(design / "design.json")
    d.update(ingest_manifest_sha256=sha256_file(ingest / "normalized-manifest.json"), metrics_sha256=sha256_file(metrics / "metrics.jsonl"))
    rewrite(design / "design.json", d)
    dlock = read_json(design / "design-lock.json")
    dlock.update(ingest_manifest_sha256=d["ingest_manifest_sha256"], metrics_sha256=d["metrics_sha256"], design_sha256=sha256_file(design / "design.json"))
    rewrite(design / "design-lock.json", dlock)
    slock = read_json(selection / "selection-lock.json")
    slock.update(metrics_sha256=d["metrics_sha256"], design_sha256=dlock["design_sha256"],
                 selections_sha256=sha256_file(selection / "selections.jsonl"), comparisons_sha256=sha256_file(selection / "comparisons.json"))
    rewrite(selection / "selection-lock.json", slock)
    for directory, name in ((ingest,"INGEST"),(metrics,"METRICS"),(design,"DESIGN"),(selection,"SELECTION")):
        (directory / f"{name}_SHA256SUMS").unlink()
        write_sums(directory)
        (directory / "SHA256SUMS").rename(directory / f"{name}_SHA256SUMS")


def check_inputs(root):
    return validate_inputs(root / "selection", root / "ingest/normalized-manifest.json", root / "metrics", root / "design", PILOT, "practice")


def test_bundle_replay_mapping_and_no_replace(ann_data, tmp_path):
    bundle = load_bundle(ann_data / "bundle")
    for a in ANNOTATORS:
        mapping = mapping_for(bundle["comparisons"], a)
        assert mapping == mapping_for(bundle["comparisons"], a)
        assert len(mapping) == len({d["comparison_id"] for d in mapping})
        families = {c["comparison_id"]: c["family"] for c in bundle["comparisons"]}
        for family in FAMILIES:
            counts = Counter(d["x_as"] for d in mapping if families[d["comparison_id"]] == family)
            assert abs(counts["A"] - counts["B"]) <= 1
    receipt = prepare_annotation(ann_data / "selection", ann_data / "ingest/normalized-manifest.json", tmp_path / "replay", "practice", fixture_native_media=True)
    assert receipt["formal_answers"] == 0
    assert sha256_file(ann_data / "bundle/private-mapping.json") == sha256_file(tmp_path / "replay/private-mapping.json")
    with pytest.raises(FileExistsError):
        prepare_annotation(ann_data / "selection", ann_data / "ingest/normalized-manifest.json", tmp_path / "replay", "practice")
    with pytest.raises(ValueError, match="frozen formal"):
        prepare_annotation(ann_data / "selection", ann_data / "ingest/normalized-manifest.json", tmp_path / "bad-formal", "formal")
    assert list(tmp_path.glob(".bad-formal-*.staging/FAILED.json"))


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "role", "family", "sample", "source", "candidate", "false_tie", "qualitative"])
def test_comparison_relationship_tampering_rejected_after_rechecksum(ann_data, tmp_path, mutation):
    root = tmp_path / "drift"
    shutil.copytree(ann_data, root)
    path = root / "selection/comparisons.json"
    p = read_json(path)
    c = p["comparisons"][0]
    if mutation == "missing": p["comparisons"].pop()
    elif mutation == "duplicate": p["comparisons"][-1] = c
    elif mutation == "role": c["candidate_x"]["role"] = "equal-linear-n4"
    elif mutation == "family": c["family"] = FAMILIES[1] if c["family"] == FAMILIES[0] else FAMILIES[0]
    elif mutation == "sample": c["sample_id"] = "bus-red"
    elif mutation == "source": c["source_video"]["sha256"] = "0" * 64
    elif mutation == "candidate": c["candidate_x"]["video"]["relative_path"] = "metadata/original-plan.json"
    elif mutation == "false_tie": c["identical_selection"] = not c["identical_selection"]
    elif mutation == "qualitative": c["candidate_x"]["candidate_id"] = "dog-tiger-s101"
    rewrite(path, p)
    rechain(root)
    with pytest.raises(ValueError): check_inputs(root)


@pytest.mark.parametrize("file", ["ingest/normalized-manifest.json", "selection/selection-lock.json", "metrics/metrics.jsonl", "design/design.json"])
def test_checksum_drift_rejected(ann_data, tmp_path, file):
    root = tmp_path / "drift"
    shutil.copytree(ann_data, root)
    with (root / file).open("ab") as h: h.write(b" ")
    with pytest.raises(ValueError, match="checksum"): check_inputs(root)


def test_cross_lock_and_ingest_role_drift(ann_data, tmp_path):
    root = tmp_path / "drift"
    shutil.copytree(ann_data, root)
    p = read_json(root / "ingest/normalized-manifest.json")
    p["candidates"][0]["sample_id"] = "dog-tiger"
    rewrite(root / "ingest/normalized-manifest.json", p)
    rechain(root)
    with pytest.raises(ValueError, match="matrix"): check_inputs(root)


@pytest.mark.parametrize("direction", ["A", "B"])
@pytest.mark.parametrize("choice", ["A", "B", "tie", "uncertain"])
def test_all_direction_choices(direction, choice):
    expected = ("X" if choice == direction else "Y") if choice in ("A", "B") else choice
    assert set(canonical_answers(Answers.model_validate(answers(choice)), direction).values()) == {expected}


@pytest.mark.parametrize("patch", [{"overall":"X"},{"confidence":1.1},{"confidence":float("nan")},
                                     {"confidence":.6},{"confidence":True},{"confidence":"0.75"},
                                     {"notes":"x"*1001},{"annotator_id":"annotator-b"},{"x_as":"B"}])
def test_strict_answer_fields(patch):
    with pytest.raises(ValueError): Answers.model_validate(answers(**patch))


def test_missing_answer_and_safe_notes():
    data = answers(); data.pop("overall")
    with pytest.raises(ValueError): Answers.model_validate(data)
    assert Answers.model_validate(answers(notes="<script>alert(1)</script>")).notes.startswith("<script>")


def test_draft_confirm_retry_conflict_resume(ann_data, tmp_path):
    with store_for(ann_data, tmp_path) as s:
        view = view_ready(s)
        assert s.save_draft(view["handle"], {"overall":"B"}, 0) == 1
        with pytest.raises(Conflict): s.save_draft(view["handle"], {}, 0)
        req = uuid.uuid4().hex
        record = s.submit(view["handle"], answers(), req)
        assert s.submit(view["handle"], answers(), req) == record
        with pytest.raises(Conflict): s.submit(view["handle"], answers("B"), req)
        with pytest.raises(Conflict): s.submit(view["handle"], answers(), uuid.uuid4().hex)
        with pytest.raises(Conflict): s.save_draft(view["handle"], {}, 1)
    with pytest.raises(FileExistsError): store_for(ann_data, tmp_path)
    with store_for(ann_data, tmp_path, resume=True) as s:
        assert len(s.records) == 1 and s.open_view()["position"] == 2
        assert s.records[0].source == "practice"
        assert s.submit(view["handle"], answers(), req) == record
        with pytest.raises(Conflict): s.submit(view_ready(s)["handle"], answers(), req)


def test_uncertain_rename_receipt_is_reconciled(ann_data, tmp_path, monkeypatch):
    from defense_mvp.io import rename_noreplace
    with store_for(ann_data, tmp_path) as s:
        view = view_ready(s)
        def rename_then_fail(source, target):
            rename_noreplace(source, target)
            raise OSError("simulated lost acknowledgement after rename")
        with monkeypatch.context() as m:
            m.setattr("defense_mvp.annotation_store.rename_noreplace", rename_then_fail)
            record = s.submit(view["handle"], answers(), uuid.uuid4().hex)
        assert len(s.records) == 1 and len(list((s.directory / "records").iterdir())) == 1
        assert s.submit(view["handle"], answers(), record.request_id) == record


@pytest.mark.parametrize("failure", ["fsync", "rename"])
def test_power_loss_pending_never_becomes_answer(ann_data, tmp_path, monkeypatch, failure):
    with store_for(ann_data, tmp_path) as s:
        view = view_ready(s)
        with monkeypatch.context() as m:
            def fail(*a, **k): raise OSError("simulated power loss")
            if failure == "fsync": m.setattr("os.fsync", fail)
            else: m.setattr("defense_mvp.annotation_store.rename_noreplace", fail)
            with pytest.raises(OSError): s.submit(view["handle"], answers(), uuid.uuid4().hex)
        assert not s.records and not list((s.directory / "records").iterdir())
        assert list((s.directory / "pending").iterdir())
    with store_for(ann_data, tmp_path, resume=True) as s:
        assert s.open_view()["position"] == 1


def test_two_tabs_and_process_locks_and_crash_recovery(ann_data, tmp_path):
    with store_for(ann_data, tmp_path) as s:
        v1, v2 = view_ready(s), view_ready(s)
        with pytest.raises(Conflict): WriterLock(s.directory)
        command = [sys.executable,"-c","from pathlib import Path; from defense_mvp.annotation_store import WriterLock; WriterLock(Path(__import__('sys').argv[1]))",str(s.directory)]
        p = subprocess.run(command, capture_output=True)
        assert p.returncode != 0 and b"another process" in p.stderr
        s.submit(v1["handle"], answers(), uuid.uuid4().hex)
        with pytest.raises(Conflict): s.submit(v2["handle"], answers(), uuid.uuid4().hex)
    # Abrupt process exit releases the kernel lock, preserving the unchanged sentinel.
    command = [sys.executable,"-c","from pathlib import Path; from defense_mvp.annotation_store import WriterLock; import os,sys; lock=WriterLock(Path(sys.argv[1])); os._exit(0)",str(tmp_path/"annotator-a")]
    assert subprocess.run(command, capture_output=True).returncode == 0
    with store_for(ann_data, tmp_path, resume=True) as s: assert len(s.records) == 1


@pytest.mark.parametrize("damage", ["record", "draft", "lock", "identity", "direction", "gap"])
def test_resume_rejects_corruption(ann_data, tmp_path, damage):
    with store_for(ann_data, tmp_path) as s:
        view = view_ready(s)
        s.save_draft(view["handle"], {}, 0)
        s.submit(view["handle"], answers(), uuid.uuid4().hex)
    root = tmp_path / "annotator-a"
    if damage in ("record","draft"):
        (root / ("records" if damage == "record" else "drafts") / "0001.json").write_bytes(b"{")
    elif damage == "lock": (root / "writer.lock").write_bytes(b"unknown")
    elif damage == "gap": (root / "records/0001.json").rename(root / "records/0002.json")
    else:
        path = root / ("session.json" if damage == "identity" else "records/0001.json")
        p = read_json(path)
        if damage == "identity": p["annotator_id"] = "annotator-b"
        else: p["x_as"] = "A" if p["x_as"] == "B" else "B"
        rewrite(path, p)
    with pytest.raises(ValueError): store_for(ann_data, tmp_path, resume=True)


def test_wrong_resume_and_media_not_ready(ann_data, tmp_path):
    with pytest.raises(ValueError): store_for(ann_data, tmp_path, resume=True)
    with store_for(ann_data, tmp_path) as s:
        with pytest.raises(ValueError, match="media not ready"): s.submit(s.open_view()["handle"], answers(), uuid.uuid4().hex)
    with pytest.raises(ValueError): AnnotationStore(ann_data/"bundle", "annotator-b", tmp_path/"annotator-a", True)


@pytest.mark.parametrize("header,expected", [(None,(0,9,200)),("bytes=0-2",(0,2,206)),("bytes=4-",(4,9,206)),("bytes=-4",(6,9,206)),("bytes=0-999",(0,9,206)),("bytes=-99",(0,9,206))])
def test_ranges(header, expected): assert byte_range(header, 10) == expected


@pytest.mark.parametrize("header", ["bytes=10-", "bytes=5-3", "bytes=-0", "bytes=-", "bytes=0-1,3-4", "bad", "bytes=a-2"])
def test_invalid_ranges(header):
    with pytest.raises(ValueError): byte_range(header, 10)


@pytest.fixture
def http_session(ann_data, tmp_path):
    with store_for(ann_data, tmp_path) as s:
        with AnnotationHTTPServer(s, 0) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            yield server
            server.shutdown(); thread.join()


def request(server, path, method="GET", payload=None, headers=None, auth=True, raw_path=False):
    h = {"Cookie": server.cookie_name + "=" + server.cookie_token} if auth else {}
    if method == "POST": h.update({"Origin":server.origin,"X-Review-CSRF":server.csrf,"Content-Type":"application/json"})
    h.update(headers or {})
    if not raw_path and not path.startswith((server.prefix, "/entry/")):
        path = server.prefix + path.lstrip("/")
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    conn.request(method, path, json.dumps(payload) if payload is not None else None, h)
    response = conn.getresponse(); data = response.read(); status = response.status; hs=dict(response.getheaders()); conn.close()
    return status, hs, data


def test_http_anonymity_ranges_errors_and_identity(http_session):
    s = http_session
    status, headers, body = request(s,"/")
    assert status == 200
    status, _, raw = request(s,"/api/current")
    current = json.loads(raw)
    assert set(current) == {"complete","view","csrf","progress","instruction","practice","media","draft","revision"}
    all_output = body + raw + json.dumps(headers).encode()
    for secret in (b"constrained-pareto",b"equal-linear",b"candidate_id",b"comparison_id",b"20260901",b"delivery_root",b"D:\\",b"x_as"):
        assert secret not in all_output
    for label,url in current["media"].items():
        assert request(s,url)[0] == 200
        status,hs,data = request(s,url,headers={"Range":"bytes=0-1"})
        assert status == 206 and len(data)==2 and hs["Content-Range"].startswith("bytes 0-1/")
        assert request(s,url,headers={"Range":"bytes=999999-"})[0] == 416
    assert request(s,"/api/media-state","POST",{"view":current["view"],"ready":True})[0] == 200
    payload={"view":current["view"],"request_id":uuid.uuid4().hex,"answers":answers()}
    assert request(s,"/api/submit","POST",{**payload,"annotator_id":"annotator-b"})[0] == 422
    assert request(s,"/api/submit","POST",payload)[0] == 200
    assert request(s,"/api/submit","POST",payload)[0] == 200
    assert request(s,current["media"]["A"])[0] == 409


@pytest.mark.parametrize("headers", [{"Cookie":"review_session=bad"},{"Origin":"https://other.invalid"},{"Host":"attacker.invalid"},{"Sec-Fetch-Site":"cross-site"}])
def test_http_wrong_session_origin_host_rejected(http_session, headers):
    assert request(http_session,"/api/current",headers=headers)[0] == 403


def test_http_entry_csrf_and_route_allowlist(http_session):
    s=http_session
    assert request(s,"/api/current",auth=False)[0] == 403
    assert request(s,"/entry/invalid",auth=False)[0] == 403
    status,hs,_=request(s,"/entry/"+s.entry_token,auth=False)
    assert status==303 and "HttpOnly" in hs["Set-Cookie"] and hs["Location"]==s.prefix
    assert "Path="+s.prefix in hs["Set-Cookie"]
    assert request(s,"/entry/"+s.entry_token,auth=False)[0]==403
    for path in ("/private-mapping.json","/bundle.json","/../session.json","/%2e%2e/session.json","/media/../../pilot.yaml","/?file=secret","/api/other"):
        status,_,body=request(s,path)
        assert status==404 and b"secret" not in body
    assert request(s,"/api/draft","POST",{},headers={"X-Review-CSRF":"bad"})[0]==403


def test_old_page_path_rejected_even_with_new_browser_cookie(http_session):
    s = http_session
    old = s.prefix
    s.prefix = "/s/" + uuid.uuid4().hex + "/"
    assert request(s,old+"api/current",raw_path=True)[0] == 404
    assert request(s,old+"api/submit","POST",{},raw_path=True)[0] == 404
    assert request(s,"/api/current")[0] == 200
    mixed = s.cookie_name + "=" + s.cookie_token + "; review_session=legacy_root_cookie"
    assert request(s,"/api/current",headers={"Cookie":mixed})[0] == 200


def test_fixture_native_cannot_be_formal(ann_data, tmp_path):
    with pytest.raises(ValueError, match="practice-only"):
        prepare_annotation(ann_data/"selection",ann_data/"ingest/normalized-manifest.json",tmp_path/"bad","formal",fixture_native_media=True)


def test_original_media_drift_and_missing_block_submit(ann_data, tmp_path, monkeypatch):
    from defense_mvp.annotation_store import media_for
    with store_for(ann_data, tmp_path) as s:
        view = view_ready(s)
        ref = media_for(s.bundle, view["comparison_id"])["X"]
        original = Path(s.bundle["delivery_root"]) / ref["relative_path"]
        # Patch the reader, never mutate a shared input fixture.
        old_hash = sha256_file
        with monkeypatch.context() as m:
            m.setattr("defense_mvp.annotation_store.sha256_file", lambda p: "0"*64 if p == original else old_hash(p))
            with pytest.raises(ValueError,match="media changed"):
                s.submit(view["handle"],answers(),uuid.uuid4().hex)
        with monkeypatch.context() as m:
            def missing(*args): raise ValueError("media missing")
            m.setattr("defense_mvp.annotation_store._package_file",missing)
            with pytest.raises(ValueError,match="media missing"):
                s.submit(view["handle"],answers(),uuid.uuid4().hex)
        assert len(s.records)==0


def test_lossless_presentation_equivalence_on_playable_fixture(tmp_path):
    import imageio_ffmpeg
    from defense_mvp.annotation_media import create_presentation, decoded_signature
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    source = tmp_path / "source.mp4"
    subprocess.run([exe,"-v","error","-n","-f","lavfi","-i","testsrc2=size=512x512:rate=8",
                    "-frames:v","16","-c:v","mpeg4","-pix_fmt","yuv420p",str(source)],check=True)
    ref = {"relative_path":"source.mp4","sha256":sha256_file(source)}
    data = {"delivery_root":str(tmp_path),"comparisons":[{"source_video":ref,"candidate_x":{"video":ref},"candidate_y":{"video":ref}}]}
    output = tmp_path / "presentation-bundle"; output.mkdir()
    result = create_presentation(data,output,False)
    target = output / result["presentation_media"]["source.mp4"]["relative_path"]
    assert decoded_signature(exe,source)==decoded_signature(exe,target)
    assert read_json(output/"presentation-proof.json")["media"][0]["original_sha256"]==ref["sha256"]


def test_export_dual_coverage_no_replace_and_practice_boundary(ann_data, tmp_path):
    bundle=ann_data/"bundle"
    with store_for(ann_data,tmp_path) as s: pass
    export_annotations(bundle,tmp_path/"annotator-a",tmp_path/"empty")
    assert verify_annotations(bundle,[tmp_path/"empty"],True)["status"]=="incomplete"
    outputs=[]
    for a in ANNOTATORS:
        with store_for(ann_data,tmp_path,a,resume=(a=="annotator-a")) as s: finish(s)
        target=tmp_path/(a+"-export")
        export_annotations(bundle,tmp_path/a,target); outputs.append(target)
    result=verify_annotations(bundle,outputs,True)
    assert result["status"]=="complete" and result["scope"]=="dual" and result["mode"]=="practice"
    assert result["exported_answers"]==2*result["manual_per_annotator"]
    assert all(c["covered"]==42 for c in result["coverages"])
    with pytest.raises(ValueError,match="practice"): verify_annotations(bundle,outputs)
    with pytest.raises(ValueError,match="independent"): verify_annotations(bundle,[outputs[0],outputs[0]],True)
    with pytest.raises(FileExistsError): export_annotations(bundle,tmp_path/"annotator-a",outputs[0])
    export_annotations(bundle,tmp_path/"annotator-a",tmp_path/"another")
    assert sha256_file(outputs[0]/"answers.jsonl")==sha256_file(tmp_path/"another/answers.jsonl")
    rows=read_json(outputs[0]/"automatic-ties.json")
    assert all(set(r)=={"comparison_id","source","reason","media_sha256","outcome"} for r in rows)


@pytest.mark.parametrize("damage",["duplicate","auto","mode","bundle","canonical","coverage"])
def test_export_tampering_rejected_even_with_rechecksum(ann_data,tmp_path,damage):
    with store_for(ann_data,tmp_path) as s: s.submit(view_ready(s)["handle"],answers(),uuid.uuid4().hex)
    output=tmp_path/"export"
    export_annotations(ann_data/"bundle",tmp_path/"annotator-a",output)
    if damage=="duplicate":
        p=output/"answers.jsonl"; p.write_text(p.read_text()*2)
    elif damage=="canonical":
        p=output/"answers.jsonl"; r=json.loads(p.read_text()); r["canonical"]["overall"]="uncertain"; p.write_text(json.dumps(r)+"\n")
    else:
        p=output/({"auto":"automatic-ties.json","mode":"session.json","bundle":"session.json","coverage":"coverage.json"}[damage])
        r=read_json(p)
        if damage=="auto": r[0]["media_sha256"]="0"*64
        elif damage=="mode": r["mode"]="formal"
        elif damage=="bundle": r["bundle_sha256"]="0"*64
        else: r["status"]="complete"
        rewrite(p,r)
    (output/"SHA256SUMS").unlink(); write_sums(output)
    with pytest.raises(ValueError): verify_annotations(ann_data/"bundle",[output],True)


def test_new_cli_smoke():
    for command in ("prepare-annotation","annotate","export-annotations","verify-annotations"):
        result=CliRunner().invoke(app,[command,"--help"])
        assert result.exit_code==0, result.output
