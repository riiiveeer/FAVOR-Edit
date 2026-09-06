"""D5 tests use synthetic facts and tiny images, never formal annotation records."""
from copy import deepcopy
from pathlib import Path
import json
import random

import pytest
from defense_mvp.reporting.core import (
    CONFIG, CASE_LABELS, Inputs, Registry, frame_indices, load_config,
    narrative_guard, select_cases, verify_pins, validate_counts, script_seconds,
)


def case_rows():
    rows=[]
    for sample in ['z','a']:
        for i,choice in enumerate(['X','Y','uncertain']):
            rows.append({'family':'proposed-n4-vs-n1','source':'human_pair','sample_id':sample,
                         'trial_id':f'{sample}-trial-{i}','replicate':i+1,'comparison_id':f'fixture-{sample}-{i}',
                         'proposed_side':'X','aggregate':{'overall':choice}})
    return rows


def failure_for(rows):
    return {'cases':[{'comparison_id':r['comparison_id'],'overall_outcome': 'loss' if r['aggregate']['overall']=='Y' else 'uncertain'} for r in rows if r['aggregate']['overall']!='X']}


def test_report_config_frozen_and_16_frame_rounding(tmp_path):
    cfg=load_config()
    assert frame_indices(16,cfg)==[0,5,10,15]
    assert frame_indices(6,cfg)==[0,2,3,5]
    p=tmp_path/'config.yaml'; p.write_bytes(CONFIG.read_bytes()+b'\nunknown: true\n')
    with pytest.raises(ValueError,match='drift'): load_config(p)


@pytest.mark.parametrize('seed',range(8))
def test_case_stable_order_and_category_selection(seed):
    rows=case_rows(); random.Random(seed).shuffle(rows)
    selected=select_cases(rows,{'qualitative_sample_ids':['z','a','m']},failure_for(rows),load_config())
    assert [r['label'] for r in selected]==CASE_LABELS
    assert [r['record']['sample_id'] for r in selected[:3]]==['a']*3
    assert [r['kind'] for r in selected[:3]]==['win','loss','uncertain']
    assert selected[3]['sample_id']=='a'


def test_case_missing_is_unavailable_no_replacement():
    rows=[r for r in case_rows() if r['aggregate']['overall']=='X']
    chosen=select_cases(rows,{'qualitative_sample_ids':[]},failure_for(rows),load_config())
    assert [r['status'] for r in chosen]==['available','unavailable','unavailable','unavailable']
    assert all('reason' in r for r in chosen[1:])


def test_case_direction_and_failure_index():
    rows=case_rows()
    for r in rows:
        r['proposed_side']='Y'
        if r['aggregate']['overall'] in ('X','Y'): r['aggregate']['overall']='Y' if r['aggregate']['overall']=='X' else 'X'
    failure={'cases':[{'comparison_id':r['comparison_id'],'overall_outcome':'loss' if r['aggregate']['overall']=='X' else 'uncertain'} for r in rows if r['aggregate']['overall']!='Y']}
    chosen=select_cases(rows,{'qualitative_sample_ids':[]},failure,load_config())
    assert chosen[0]['record']['aggregate']['overall']=='Y'
    with pytest.raises(ValueError,match='failure index'): select_cases(rows,{'qualitative_sample_ids':[]},{'cases':[]},load_config())


def test_fact_registry_precision_none_finite_duplicate():
    r=Registry(); r.add('ratio',5/7,'synthetic.json','/ratio','a'*64,'ratio',3)
    r.add('missing',None,'synthetic.json','/missing','a'*64,'seconds')
    assert r.entries['ratio']['raw']==5/7 and r['ratio']=='0.714'
    assert r['missing']=='unavailable'
    with pytest.raises(ValueError): r.add('ratio',1,'x','/x','a'*64)
    with pytest.raises(ValueError): r.add('nan',float('nan'),'x','/x','a'*64)


@pytest.mark.parametrize('claim',['显著提升','证明优于','达到 SOTA','普遍有效','双盲','84 条独立答案','CPU 指标理解语义'])
def test_narrative_rejects_unsupported_claims(claim):
    with pytest.raises(ValueError,match='unsupported'): narrative_guard(claim,Registry(),required=False)


def test_narrative_requires_limits_and_registered_numbers():
    with pytest.raises(ValueError,match='boundary'): narrative_guard('描述性',Registry())
    with pytest.raises(ValueError,match='unregistered'): narrative_guard('胜率0.999',Registry(),required=False)
    narrative_guard('来源SHA-256：`abcdef`',Registry(),required=False)
    with pytest.raises(ValueError,match='unregistered'): narrative_guard('256个样本',Registry(),required=False)


def test_script_duration_uses_effective_content():
    cfg=load_config()
    result=script_seconds('# 标题123\n'+'甲'*1560,cfg)
    assert result['estimated_seconds']==360
    with pytest.raises(ValueError,match='duration'): script_seconds('短讲稿',cfg)


def test_input_pins_reject_missing_formal_sources(tmp_path):
    args={k:tmp_path/k for k in ('aggregate','analysis','d4_verification','selection','metrics','design','ingest')}
    with pytest.raises(FileNotFoundError): verify_pins(Inputs(**args),load_config())


@pytest.fixture(scope='module')
def full_synthetic(tmp_path_factory):
    from d5_fixture import synthetic_data
    return synthetic_data(tmp_path_factory.mktemp('d5-synthetic'))


def test_complete_fact_content_expansion(full_synthetic):
    from defense_mvp.reporting.core import build_facts,audit_registry
    from defense_mvp.reporting.content import compose
    data,inputs=full_synthetic
    registry,main,agreement,costs=build_facts(data,inputs)
    assert audit_registry(registry,inputs)>200
    assert len(main)==10 and len(agreement)==6
    assert registry['fallback_n2']=='26'
    assert registry.entries['exact.rate']['raw']==1.0
    assert next(c for c in costs if c['metric']=='d2_selection_elapsed')['value'] is None
    content=compose(registry,data)
    assert len(content['slides'])==10 and 300<=content['timing']['estimated_seconds']<=420
    assert 'synthetic' not in content['report'] # no raw media path or sample ID copied into report
    assert 'SYNTHETIC' in content['report']


def test_case_media_preserves_pixels_and_trace(full_synthetic,tmp_path):
    from defense_mvp.reporting.cases import render_cases
    from PIL import Image
    from w1_pipeline.hashing import sha256_file
    data,_=full_synthetic; traces=render_cases(data,tmp_path/'cases')
    assert len(traces)==4 and len(traces[3]['roles'])==6
    for case in traces:
        assert case['frame_indices']==[0,5,10,15]
        for role in case['roles']:
            for frame in role['frames']:
                assert sha256_file(tmp_path/'cases'/frame['output'])==frame['sha256']
    public=''.join(p.read_text(encoding='utf-8') for p in (tmp_path/'cases').glob('*.html'))
    assert 'comparison_id' not in public and 'annotator-' not in public and 'notes' not in public


@pytest.mark.parametrize('key,value',[('status','failed'),('aggregate_records',41),('human_pairs',31),('automatic_ties',11),('sample_clusters',8),('agreement_n',42),('bootstrap_iterations',1999),('bt_status','separation')])
def test_cardinality_drift_is_hard_failure(full_synthetic,key,value):
    data,_=full_synthetic
    v={'status':'passed','aggregate_records':42,'human_pairs':32,'automatic_ties':10,'families':dict(zip(('proposed-n4-vs-n1','proposed-vs-linear-n4'),(28,14))),'sample_clusters':7,'agreement_n':32,'bootstrap_iterations':2000,'bt_status':'ok'}
    v[key]=value
    with pytest.raises(ValueError): validate_counts(data['summary'],v,data['rows'],data['main'],data['agreement'],data['bt'],data['failure'])


@pytest.fixture(scope='module')
def bundled_runtime():
    b=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'
    packages=Path.home()/'.codex/plugins/cache/openai-primary-runtime/presentations'
    if not b.is_dir() or not packages.is_dir(): pytest.skip('bundled presentation runtime unavailable')
    skills=sorted(packages.glob('*/skills/presentations'))
    return {'python':b/'python/python.exe','node':b/'node/bin/node.exe','modules':b/'node/node_modules','skill':skills[-1]}


@pytest.fixture(scope='module')
def rendered_synthetic(full_synthetic,bundled_runtime,tmp_path_factory):
    from defense_mvp.reporting.build import build_draft
    # Finalizer requires outputs below this workspace. Each pytest session uses a new ignored root.
    import uuid
    output=Path('artifacts/defense_mvp/d5-engineering')/('pytest-'+uuid.uuid4().hex)
    data,inputs=full_synthetic
    build_draft(data,inputs,output,bundled_runtime)
    return output.resolve(),data,inputs,bundled_runtime


def test_complete_synthetic_rebuild_pptx_and_render_verifier(rendered_synthetic):
    from defense_mvp.reporting.verification import verify_stable
    root,data,inputs,runtime=rendered_synthetic
    result=verify_stable(root,inputs,data,runtime,require_visual=False)
    assert result['page_count']==10 and result['stable_files_rebuilt']>80 and result['links_checked']>60
    assert result['evidence_status']=='synthetic-engineering-only'


def test_no_replace_keeps_existing_output(rendered_synthetic):
    from defense_mvp.reporting.build import build_draft
    from w1_pipeline.hashing import sha256_file
    root,data,inputs,runtime=rendered_synthetic;before=sha256_file(root/'SHA256SUMS')
    with pytest.raises(FileExistsError):build_draft(data,inputs,root,runtime)
    assert sha256_file(root/'SHA256SUMS')==before


def test_staging_failure_preserves_diagnostic(full_synthetic,tmp_path,monkeypatch):
    from defense_mvp.reporting.build import build_draft
    def fail(*args):raise OSError('synthetic renderer failure')
    monkeypatch.setattr('defense_mvp.reporting.build.write_stable',fail)
    data,inputs=full_synthetic;output=tmp_path/'draft'
    with pytest.raises(OSError):build_draft(data,inputs,output,{})
    failed=list(tmp_path.glob('.draft-*.failed'))
    assert len(failed)==1 and not output.exists()
    assert json.loads((failed[0]/'FAILED.json').read_text())['error']=='synthetic renderer failure'


@pytest.mark.parametrize('mutation',['unknown','report','png','source','config','slide','case','script'])
def test_rehashed_tamper_hard_fails(rendered_synthetic,tmp_path,mutation):
    import shutil
    from defense_mvp.annotation_bundle import write_sums
    from defense_mvp.reporting.verification import verify_stable
    root,data,inputs,runtime=rendered_synthetic;copy=tmp_path/'copy';shutil.copytree(root,copy)
    if mutation=='unknown':(copy/'extra.txt').write_text('unexpected')
    elif mutation=='report':
        p=copy/'report/DEFENSE_REPORT.md';p.write_text(p.read_text(encoding='utf-8').replace('0.554','0.999'),encoding='utf-8')
    elif mutation=='png':
        from PIL import Image
        Image.new('RGB',(1600,900),'red').save(copy/'report/figures/overall-ci.png')
    elif mutation=='source':
        p=copy/'report/input-manifest.json';v=json.loads(p.read_text());v['source']['files']['fake.py']='0'*64;p.write_text(json.dumps(v))
    elif mutation=='config':
        p=copy/'report/input-manifest.json';v=json.loads(p.read_text());v['config_sha256']='0'*64;p.write_text(json.dumps(v))
    elif mutation=='slide':
        p=copy/'report/slide-data.json';v=json.loads(p.read_text(encoding='utf-8'));v['slides'][6]['title']='显著提升';p.write_text(json.dumps(v))
    elif mutation=='case':
        p=copy/'report/cases/trace-manifest.json';v=json.loads(p.read_text(encoding='utf-8'));v['cases'][0]['frame_indices']=[1,5,10,15];p.write_text(json.dumps(v))
    else:
        p=copy/'script/DEFENSE_SCRIPT.md';p.write_text(p.read_text(encoding='utf-8')+'\n证明优于所有方法\n',encoding='utf-8')
    # Refresh both inventories: recomputation must reject tamper beyond mere byte hashes.
    (copy/'report/SHA256SUMS').unlink();write_sums(copy/'report')
    (copy/'SHA256SUMS').unlink();write_sums(copy)
    with pytest.raises(ValueError):verify_stable(copy,inputs,data,runtime,require_visual=False)


def test_visual_receipt_required(rendered_synthetic):
    from defense_mvp.reporting.verification import verify_stable
    root,data,inputs,runtime=rendered_synthetic
    with pytest.raises(FileNotFoundError):verify_stable(root,inputs,data,runtime,require_visual=True)


def test_public_documents_have_deterministic_relationship(rendered_synthetic,tmp_path):
    from defense_mvp.reporting.publication import export_public,verify_public
    root,_,_,_=rendered_synthetic;dest=tmp_path/'docs'
    files=export_public(root,Path.cwd(),dest)
    assert len(files)==15
    assert verify_public(root,Path.cwd(),dest)['status']=='passed'
    with pytest.raises(FileExistsError):export_public(root,Path.cwd(),dest)
    for name in files:
        if Path(name).suffix in ('.json','.md','.csv','.svg'):
            content=(dest/name).read_text(encoding='utf-8')
            assert 'private-mapping' not in content and 'entry_token' not in content and 'fixture-proposed' not in content


@pytest.mark.parametrize('command',['report','verify-report'])
def test_d5_module_cli_help(command):
    import subprocess,sys
    result=subprocess.run([sys.executable,'-m','defense_mvp.reporting',command,'--help'],capture_output=True,text=True)
    assert result.returncode==0 and '--d4-verification' in result.stdout and '--ingest' in result.stdout


def test_pptx_text_tamper_even_with_updated_hash(rendered_synthetic,tmp_path):
    import shutil,zipfile,hashlib
    from defense_mvp.reporting.verification import verify_pptx
    root,_,_,_=rendered_synthetic;copy=tmp_path/'copy';shutil.copytree(root,copy)
    pptx=copy/'slides/DEFENSE_MVP_D5_DRAFT.pptx'
    with zipfile.ZipFile(pptx) as z:parts={n:z.read(n) for n in z.namelist()}
    xml=parts['ppt/slides/slide7.xml'].decode('utf-8');xml=xml.replace('0.554','0.999');parts['ppt/slides/slide7.xml']=xml.encode()
    with zipfile.ZipFile(pptx,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in parts.items():z.writestr(n,b)
    p=copy/'slides/slides-receipt.json';receipt=json.loads(p.read_text(encoding='utf-8'));receipt['pptx_sha256']=hashlib.sha256(pptx.read_bytes()).hexdigest();p.write_text(json.dumps(receipt),encoding='utf-8')
    with pytest.raises(ValueError,match='semantics'):verify_pptx(copy,json.loads((copy/'report/slide-data.json').read_text(encoding='utf-8')))


def test_registry_pointer_and_raw_tamper_rejected(full_synthetic):
    from defense_mvp.reporting.core import build_facts,audit_registry
    data,inputs=full_synthetic;r,*_=build_facts(data,inputs)
    r.entries['records']['raw']=84
    with pytest.raises(ValueError,match='pointer/raw'):audit_registry(r,inputs)
