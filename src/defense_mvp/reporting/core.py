"""Identity gates and deterministic public projection. No annotation exports are consumed."""
from __future__ import annotations

import csv
import io
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict
from w1_pipeline.hashing import sha256_file
from defense_mvp.annotation_bundle import read_json, validate_inputs, verify_sums
from defense_mvp.analysis_models import FAMILIES, FIELDS

REPO = Path(__file__).resolve().parents[3]
CONFIG = REPO / 'configs/defense_mvp/report-v1.yaml'
CONFIG_SHA = '000f4acee9b4b141382cbe1492863c7bc004b48edc5aad91a7a15c1321815005'
LABELS = {'proposed-n4-vs-n1': 'Proposed N=4 vs N=1',
          'proposed-vs-linear-n4': 'Proposed N=4 vs Linear N=4',
          'overall': '总体偏好', 'faithfulness': '指令忠实度', 'preservation': '非目标保持',
          'temporal_consistency': '时序一致性', 'visual_quality': '视觉质量'}
CASE_LABELS = ['成功案例1', '失败案例1', '不确定案例1', '定性边界案例1']


class Inputs(BaseModel):
    model_config = ConfigDict(extra='forbid', arbitrary_types_allowed=True)
    aggregate: Path
    analysis: Path
    d4_verification: Path
    selection: Path
    metrics: Path
    design: Path
    ingest: Path
    config: Path = CONFIG


def load_config(path=CONFIG):
    path = Path(path)
    if sha256_file(path) != CONFIG_SHA:
        raise ValueError('report protocol/config drift')
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf-8')


def csv_bytes(rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8')


def source_identity():
    files = sorted(p for p in Path(__file__).parent.rglob('*') if p.suffix in {'.py', '.mjs'} and '__pycache__' not in p.parts)
    files += sorted((REPO/'tests/defense_mvp').glob('*d5*.py'))
    files += [CONFIG]
    return {'git_head': subprocess.check_output(['git','rev-parse','HEAD'], cwd=REPO, text=True).strip(),
            'files': {p.relative_to(REPO).as_posix(): sha256_file(p) for p in files},
            'python': sys.version, 'platform': platform.platform()}


def mapped_pins(inputs, cfg):
    result = {}
    for relative, digest in cfg['input_pins'].items():
        p = Path(relative)
        if relative.startswith('configs/'):
            actual = REPO / p
        elif '/DEFENSE-MVP-D4-v01/' in relative:
            suffix = relative.split('/DEFENSE-MVP-D4-v01/')[1]
            if suffix == 'verification.json': actual = inputs.d4_verification
            else:
                kind, name = suffix.split('/', 1)
                actual = getattr(inputs, kind) / name
        else:
            kind, name = relative.split('/DEFENSE-MVP-v01/')[1].split('/', 1)
            actual = (inputs.ingest.parent if kind == 'ingest' else getattr(inputs, kind)) / name
        result[relative] = {'path': actual, 'sha256': digest}
    return result


def verify_pins(inputs, cfg):
    pins = mapped_pins(inputs, cfg)
    for key, item in pins.items():
        if sha256_file(item['path']) != item['sha256']:
            raise ValueError('frozen input SHA drift: '+key)
    return {key: item['sha256'] for key, item in pins.items()}


def verify_d4(inputs):
    """Use the frozen verifier as a black box; never return human payloads."""
    from defense_mvp.analysis_verification import verify_analysis_artifacts
    locations = read_json(inputs.aggregate/'aggregation-receipt.json')['source_locations']
    output = Path(tempfile.mkdtemp(prefix='defense-d5-d4-'))/'verification.json'
    result = verify_analysis_artifacts(
        Path(locations['bundle']), Path(locations['annotator-a']), Path(locations['annotator-b']),
        Path(locations['dual_verification']), inputs.aggregate, inputs.analysis, inputs.selection,
        inputs.metrics, inputs.design, inputs.ingest, REPO/'configs/defense_mvp/analysis-v1.yaml', output)
    if result != read_json(inputs.d4_verification) or sha256_file(output) != sha256_file(inputs.d4_verification):
        raise ValueError('independent D4 verification identity mismatch')
    return result


def frame_indices(count, cfg):
    if type(count) is not int or count < 2:
        raise ValueError('frame sequence must have at least two frames')
    return [math.floor((count-1)*p+0.5) for p in cfg['cases']['positions']]


def outcome(row):
    value = row['aggregate']['overall']
    return ('win' if value == row['proposed_side'] else 'loss') if value in ('X','Y') else value


def select_cases(rows, manifest, failure, cfg):
    selected=[]
    rule=cfg['cases']
    failure_ids={r['comparison_id']:r for r in failure['cases']}
    for index, wanted in enumerate(rule['outcomes']):
        candidates=[r for r in rows if r['family']==rule['family'] and r['source']==rule['source'] and outcome(r)==wanted]
        candidates.sort(key=lambda r: tuple(r[k] for k in rule['sort']))
        item={'label':CASE_LABELS[index], 'kind':wanted, 'status':'available' if candidates else 'unavailable'}
        if candidates:
            row=candidates[0]
            if wanted in ('loss','uncertain') and (row['comparison_id'] not in failure_ids or failure_ids[row['comparison_id']]['overall_outcome']!=wanted):
                raise ValueError('case missing from D4 failure index')
            item['record']=row
        else: item['reason']='no comparison satisfies the frozen rule'
        selected.append(item)
    sample_ids=sorted(manifest['qualitative_sample_ids'])
    item={'label':CASE_LABELS[3], 'kind':'qualitative_only', 'status':'available' if sample_ids else 'unavailable'}
    if sample_ids: item['sample_id']=sample_ids[0]
    else: item['reason']='no qualitative-only sample'
    selected.append(item)
    return selected


def validate_counts(summary, verification, rows, main, agreement, bt, failure):
    expected={'status':'passed','aggregate_records':42,'human_pairs':32,'automatic_ties':10,
              'families':dict(zip(FAMILIES,(28,14))), 'sample_clusters':7,'agreement_n':32,
              'bootstrap_iterations':2000,'bt_status':'ok'}
    if any(verification.get(k)!=v for k,v in expected.items()): raise ValueError('D4 verification status/count drift')
    if [summary.get(k) for k in ['records','human_pairs','automatic_ties','sample_clusters','failure_case_count']] != [42,32,10,7,9]:
        raise ValueError('D4 summary count drift')
    if len(rows)!=42 or len({r['comparison_id'] for r in rows})!=42 or len({r['sample_id'] for r in rows})!=7:
        raise ValueError('aggregate identity/count drift')
    if Counter(r['source'] for r in rows)!=Counter(human_pair=32,automatic_tie=10): raise ValueError('source count drift')
    if len(main)!=10 or {(r['family'],r['field']) for r in main}!={(f,k) for f in FAMILIES for k in FIELDS}: raise ValueError('main table coverage drift')
    for family,total,auto in zip(FAMILIES,(28,14),(6,4)):
        rr=[r for r in rows if r['family']==family]
        if len(rr)!=total or sum(r['source']=='automatic_tie' for r in rr)!=auto: raise ValueError('family count drift')
        for r in [r for r in main if r['family']==family]:
            if int(r['total'])!=total or sum(int(r[k]) for k in ('wins','losses','ties','uncertain'))!=total: raise ValueError('table count conservation')
            lo,hi=float(r['bootstrap_lower']),float(r['bootstrap_upper'])
            if not 0<=lo<=hi<=1: raise ValueError('CI order/range invalid')
            cell=summary['bootstrap']['metrics'][family][r['field']]
            if cell['valid_replicates']+cell['invalid_replicates']!=2000: raise ValueError('bootstrap count drift')
    if len(agreement)!=5 or {r['field'] for r in agreement}!=set(FIELDS) or any(int(r['n'])!=32 for r in agreement): raise ValueError('agreement count drift')
    if bt['status']!='ok' or bt['diagnostics']['edge_count']!=11: raise ValueError('BT state drift')
    if failure['count']!=9 or len(failure['cases'])!=9: raise ValueError('failure index count drift')


def load_inputs(inputs):
    cfg=load_config(inputs.config)
    pins=verify_pins(inputs,cfg)
    for root,name in [(inputs.aggregate,'SHA256SUMS'),(inputs.analysis,'SHA256SUMS'),
                      (inputs.selection,'SELECTION_SHA256SUMS'),(inputs.metrics,'METRICS_SHA256SUMS'),
                      (inputs.design,'DESIGN_SHA256SUMS'),(inputs.ingest.parent,'INGEST_SHA256SUMS')]: verify_sums(root,name)
    verification=verify_d4(inputs)
    linked=validate_inputs(inputs.selection.resolve(),inputs.ingest.resolve(),inputs.metrics.resolve(),inputs.design.resolve(),REPO/'configs/defense_mvp/pilot.yaml','formal')
    # Project each verified D4 row immediately. Do not carry its human observations into reporting.
    keys=('comparison_id','family','sample_id','trial_id','replicate','source','candidate_x','candidate_y','proposed_side','aggregate')
    rows=[{k:r[k] for k in keys} for r in (json.loads(line) for line in (inputs.aggregate/'aggregate.jsonl').read_text(encoding='utf-8').splitlines())]
    comparisons={r['comparison_id']:r for r in linked['comparisons']}
    for row in rows:
        match=comparisons.get(row['comparison_id'])
        if match is None or any(row[k]!=match[k] for k in ('family','sample_id','trial_id','replicate')): raise ValueError('D4/D2 identity link drift')
        for side in ('x','y'):
            a,b=row['candidate_'+side],match['candidate_'+side]
            if (a['role'],a['candidate_id'],a['video_sha256'])!=(b['role'],b['candidate_id'],b['video']['sha256']): raise ValueError('D4/D2 role/media link drift')
    main=[r for r in csv.DictReader((inputs.analysis/'main-table.csv').read_text(encoding='utf-8').splitlines()) if r['scope']=='all-42']
    agreement=list(csv.DictReader((inputs.analysis/'agreement.csv').read_text(encoding='utf-8').splitlines()))
    summary=read_json(inputs.analysis/'summary.json'); bt=read_json(inputs.analysis/'bt.json'); failure=read_json(inputs.analysis/'failure-cases.json')
    validate_counts(summary,verification,rows,main,agreement,bt,failure)
    manifest=read_json(inputs.ingest)
    # Hash every supplied frame/mask without viewing pixels, including qualitative candidates.
    from defense_mvp.metrics import _package_file
    media_root=Path(manifest['delivery_root'])
    for frames in ([s[key] for s in manifest['samples'] for key in ('source_frames','masks')]+[c['frames'] for c in manifest['candidates']]):
        for relative,digest in zip(frames['relative_paths'],frames['sha256']): _package_file(media_root,relative,digest)
    return {'cfg':cfg,'pins':pins,'summary':summary,'main':main,'agreement':agreement,'bt':bt,'failure':failure,
            'manifest':manifest,'rows':rows,'comparisons':comparisons,'costs':read_json(inputs.analysis/'costs.json'),
            'selection_summary':read_json(inputs.selection/'selection-summary.json'),
            'metrics_summary':read_json(inputs.metrics/'metrics-summary.json'),
            'cases':select_cases(rows,manifest,failure,cfg)}


class Registry:
    def __init__(self): self.entries={}
    def add(self,key,value,source,pointer,sha,unit='count',digits=None,derivation=None):
        if key in self.entries: raise ValueError('duplicate fact '+key)
        if isinstance(value,float) and not math.isfinite(value): raise ValueError('non-finite fact')
        display='unavailable' if value is None else (f'{value:.{digits}f}' if digits is not None and isinstance(value,(float,int)) else str(value))
        self.entries[key]={'raw':value,'display':display,'digits':digits,'unit':unit,'source':source,'pointer':pointer,'source_sha256':sha,'derivation':derivation}
        return display
    def __getitem__(self,key): return self.entries[key]['display']


def build_facts(data, inputs):
    r=Registry(); s=data['summary']; cfg=data['cfg']; prec=cfg['digits']
    summary_sha=sha256_file(inputs.analysis/'summary.json')
    def add(key,value,pointer,unit='count',digits=None): r.add(key,value,'D4/analysis/summary.json',pointer,summary_sha,unit,digits)
    for key in ('records','human_pairs','automatic_ties','sample_clusters','failure_case_count'): add(key,s[key],'/'+key)
    for family in FAMILIES:
        r.add('auto.'+family,sum(row['family']==family and row['source']=='automatic_tie' for row in data['rows']),
              'D4/aggregate/aggregate.jsonl',f'[family={family},source=automatic_tie]',sha256_file(inputs.aggregate/'aggregate.jsonl'),derivation='count')
    add('bootstrap_iterations',s['bootstrap']['iterations'],'/bootstrap/iterations')
    main=[]
    for row in data['main']:
        copy=dict(row); family,field=row['family'],row['field']; stem=family+'.'+field
        boot=s['bootstrap']['metrics'][family][field]
        copy.update(valid_bootstrap=boot['valid_replicates'],invalid_bootstrap=boot['invalid_replicates']); main.append(copy)
        for col,raw in copy.items():
            if col in ('scope','family','field'): continue
            value=raw
            if col in ('wins','losses','ties','uncertain','total','valid_bootstrap','invalid_bootstrap'): value=int(raw)
            elif col in ('tie_aware_win_rate','decisive_win_rate','tie_rate','uncertain_rate','bootstrap_lower','bootstrap_upper'): value=float(raw) if raw!='' else None
            source='D4/analysis/summary.json' if col in ('valid_bootstrap','invalid_bootstrap') else 'D4/analysis/main-table.csv'
            sha=summary_sha if source.endswith('.json') else sha256_file(inputs.analysis/'main-table.csv')
            pointer=f'/bootstrap/metrics/{family}/{field}/'+('valid_replicates' if col=='valid_bootstrap' else 'invalid_replicates') if source.endswith('.json') else f'[scope=all-42,family={family},field={field}].{col}'
            r.add(stem+'.'+col,value,source,pointer,sha,'ratio' if isinstance(value,float) else 'count' if isinstance(value,int) else 'status',prec if isinstance(value,float) else None)
    agreement=[]
    for row in data['agreement']:
        agreement.append(dict(row))
        for col in ('n','diagonal','observed_agreement','cohen_kappa'):
            raw=int(row[col]) if col in ('n','diagonal') else float(row[col]) if row[col] else None
            r.add('agreement.'+row['field']+'.'+col,raw,'D4/analysis/agreement.csv',f'[field={row["field"]}].{col}',sha256_file(inputs.analysis/'agreement.csv'),'count' if col in ('n','diagonal') else 'ratio',None if col in ('n','diagonal') else prec)
    exact=s['agreement']['exact_five_field_agreement']
    for key in ('numerator','denominator'): add('exact.'+key,exact[key],'/agreement/exact_five_field_agreement/'+key)
    add('exact.rate',exact['rate']['value'],'/agreement/exact_five_field_agreement/rate/value','ratio',prec)
    agreement.append({'field':'exact_five_field_vector','n':exact['denominator'],'diagonal':exact['numerator'],'observed_agreement':exact['rate']['value'],'kappa_status':'not_applicable','cohen_kappa':'','kappa_reason':'vector exact agreement only'})
    add('bt.edges',data['bt']['diagnostics']['edge_count'],'/bradley_terry/diagnostics/edge_count')
    for node,value in data['bt']['abilities'].items(): add('bt.'+node,value,'/bradley_terry/abilities/'+node,'centered log ability',cfg['ability_digits'])
    costs=[]
    for name,item in sorted(data['costs']['entries'].items()):
        public=name.replace('annotator-a','reviewer_A').replace('annotator-b','reviewer_B')
        r.add('cost.'+public,item['value'],'D4/analysis/costs.json','/entries/'+name+'/value',sha256_file(inputs.analysis/'costs.json'),item['unit'],prec if isinstance(item['value'],float) else None)
        costs.append({'metric':public,'value':item['value'],'unit':item['unit'],'status':item['status'],'semantics':item['semantics'],
                      'source':'D4/analysis/costs.json','pointer':'/entries/'+name,'source_sha256':sha256_file(inputs.analysis/'costs.json'),
                      'upstream_sha256':item.get('source_sha256') or '', 'reason':item.get('reason','')})
    manifest=data['manifest']; imsha=sha256_file(inputs.ingest)
    for key,value,pointer in [('samples',len(manifest['samples']),'/samples'),('candidates',len(manifest['candidates']),'/candidates'),('primary_samples',len(manifest['primary_sample_ids']),'/primary_sample_ids'),('qualitative_samples',len(manifest['qualitative_sample_ids']),'/qualitative_sample_ids')]:
        r.add(key,value,'D2/ingest/normalized-manifest.json',pointer,imsha,derivation='length')
    for key,scope in [('scored_candidates','primary_sample_ids'),('qualitative_candidates','qualitative_sample_ids')]:
        r.add(key,sum(c['sample_id'] in manifest[scope] for c in manifest['candidates']),'D2/ingest/normalized-manifest.json','/candidates',imsha,derivation='count sample_id in '+scope)
    sels=[json.loads(line) for line in (inputs.selection/'selections.jsonl').read_text(encoding='utf-8').splitlines()]
    fallback=sum(row['n']==2 and row['method']=='constrained-pareto' and row['audit'].get('fallback') is True for row in sels)
    if fallback!=data['selection_summary']['pareto_fallbacks']: raise ValueError('fallback scope mismatch')
    r.add('fallback_n2',fallback,'D2/selection/selections.jsonl','[n=2,method=constrained-pareto].audit.fallback',sha256_file(inputs.selection/'selections.jsonl'),derivation='count persisted fallback flags')
    for key,value in cfg['protocol_constants'].items():
        r.add('protocol.'+key,value,'report-v1.yaml','/protocol_constants/'+key,CONFIG_SHA,'protocol constant')
    return r, main, agreement, costs


def audit_registry(registry,inputs):
    """Resolve every source pointer independently of content formatting."""
    files={'D4/analysis/'+name:inputs.analysis/name for name in ('summary.json','main-table.csv','agreement.csv','costs.json')}
    files.update({'D4/aggregate/aggregate.jsonl':inputs.aggregate/'aggregate.jsonl',
                  'D2/ingest/normalized-manifest.json':inputs.ingest,
                  'D2/selection/selections.jsonl':inputs.selection/'selections.jsonl','report-v1.yaml':inputs.config})
    cache={}
    for key,fact in registry.entries.items():
        source=files[fact['source']]
        if sha256_file(source)!=fact['source_sha256']: raise ValueError('fact source SHA mismatch')
        if source not in cache:
            text=source.read_text(encoding='utf-8')
            if source.suffix=='.csv':value=list(csv.DictReader(text.splitlines()))
            elif source.suffix=='.jsonl':value=[json.loads(line) for line in text.splitlines()]
            elif source.suffix=='.yaml':value=yaml.safe_load(text)
            else:value=json.loads(text)
            cache[source]=value
        value=cache[source]; pointer=fact['pointer']; derivation=fact['derivation']
        if pointer.startswith('/'):
            for part in pointer.lstrip('/').split('/'): value=value[part]
        else:
            criteria,tail=pointer[1:].split(']',1)
            criteria=dict(part.split('=',1) for part in criteria.split(','))
            matched=[row for row in value if all(str(row.get(k))==v for k,v in criteria.items())]
            if derivation=='count':value=len(matched)
            elif derivation=='count persisted fallback flags':value=sum(row['audit'].get('fallback') is True for row in matched)
            else:
                if len(matched)!=1:raise ValueError('ambiguous fact source pointer')
                value=matched[0][tail.lstrip('.')]
                if isinstance(fact['raw'],int):value=int(value)
                elif isinstance(fact['raw'],float):value=float(value)
                elif fact['raw'] is None and value=='':value=None
        if derivation=='length':value=len(value)
        elif derivation and derivation.startswith('count sample_id in '):
            scope=derivation.removeprefix('count sample_id in ')
            value=sum(row['sample_id'] in cache[source][scope] for row in value)
        if value!=fact['raw']:raise ValueError('fact pointer/raw mismatch: '+key)
    return len(registry.entries)


FORBIDDEN=('显著提升','证明优于','达到 SOTA','普遍有效','双盲','42 条独立真人样本','84 条独立','CPU 指标理解语义')
REQUIRED=('描述性','跨 0.5','未观察到差异','一致性较低','两位评审','7 个','代理')


def narrative_guard(text, registry, required=True):
    if any(term in text for term in FORBIDDEN): raise ValueError('unsupported narrative claim')
    if required and any(term not in text for term in REQUIRED): raise ValueError('missing narrative boundary')
    clean=re.sub(r'`[^`]*`|\]\([^)]*\)|<!--[\s\S]*?-->', '', text)
    clean=re.sub(r'(?<![A-Za-z0-9])SHA-256(?![A-Za-z0-9])','',clean)  # Algorithm identifier, including adjacent CJK.
    clean=re.sub(r'#{1,6}[^\n]*','',clean)
    allowed={'0','1','2','3','4','5','6','7','8','9','10','60','90'}
    for fact in registry.entries.values(): allowed.update(re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?',fact['display']))
    values=set(re.findall(r'(?<![A-Za-z0-9])\d+(?:\.\d+)?',clean))
    if values-allowed: raise ValueError('unregistered narrative numbers: '+str(sorted(values-allowed)))


def script_seconds(text,cfg):
    body=re.sub(r'^#.*$|<!--.*?-->','',text,flags=re.M)
    count=len(re.findall(r'[\u3400-\u9fff]',body))+len(re.findall(r'[A-Za-z]+|\d+(?:\.\d+)?',body))
    seconds=count*60/cfg['script']['effective_characters_per_minute']
    if not cfg['script']['min_seconds']<=seconds<=cfg['script']['max_seconds']: raise ValueError(f'script duration outside gate: {count} units / {seconds:.1f}s')
    return {'effective_characters':count,'estimated_seconds':seconds,'effective_characters_per_minute':cfg['script']['effective_characters_per_minute'],'method':'CJK characters plus Latin words and number tokens; excludes headings'}
