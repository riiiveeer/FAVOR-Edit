"""Synthetic-only D5 content/media fixture, constructed without real experiment reads."""
import csv
import json
from pathlib import Path
from PIL import Image
from defense_mvp.analysis import (agreement_statistics,rate_statistics,cluster_bootstrap,bradley_terry_statistics,
                                 annotation_descriptives,build_failure_cases,build_summary,build_main_rows,build_agreement_rows)
from defense_mvp.analysis_models import FAMILIES,FIELDS,load_analysis_config
from defense_mvp.reporting.core import Inputs,load_config,select_cases,json_bytes,csv_bytes
from w1_pipeline.hashing import sha256_file


def synthetic_data(root):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    for name in ('aggregate','analysis','selection','metrics','design','ingest','media'): (root/name).mkdir()
    acfg=load_analysis_config(Path('configs/defense_mvp/analysis-v1.yaml')); cfg=load_config()
    samples=[]; candidates=[]
    for n in range(10):
        sid=f'synthetic-{n:02}'
        paths=[]; hashes=[]
        for frame in range(16):
            p=root/'media'/f'{sid}-{frame}.png'
            Image.new('RGB',(512,512),(35+n*17,70+frame*6,160)).save(p)
            paths.append(p.relative_to(root).as_posix()); hashes.append(sha256_file(p))
        frames={'relative_paths':paths,'sha256':hashes}
        p=root/'media'/f'{sid}-source.mp4';p.write_bytes(f'synthetic source {n}'.encode())
        samples.append({'sample_id':sid,'instruction':'Synthetic fixture：目标颜色变化；不是研究测量','source_frames':frames,'source_video':{'relative_path':p.relative_to(root).as_posix(),'sha256':sha256_file(p)}})
        for c in range(5):
            p=root/'media'/f'{sid}-candidate-{c}.mp4';p.write_bytes(f'synthetic candidate {n}-{c}'.encode())
            candidates.append({'sample_id':sid,'candidate_id':f'{sid}-c{c}','seed':c,'frames':frames,'video':{'relative_path':p.relative_to(root).as_posix(),'sha256':sha256_file(p)}})
    manifest={'samples':samples,'candidates':candidates,'primary_sample_ids':[s['sample_id'] for s in samples[:7]],'qualitative_sample_ids':[s['sample_id'] for s in samples[7:]],'delivery_root':str(root.resolve())}
    rows=[]
    specs=[['win']*5+['loss']*2+['uncertain']*4+['tie']*11+['automatic']*6,['win']*2+['loss']*2+['uncertain']+['tie']*5+['automatic']*4]
    for family,count,outcomes in zip(FAMILIES,(4,2),specs):
        for index,wanted in enumerate(outcomes):
            sn=index//count; rep=index%count+1; sid=samples[sn]['sample_id']
            x=candidates[sn*5]; y=candidates[sn*5+(0 if wanted=='automatic' else 1)]
            val={'win':'X','loss':'Y','uncertain':'uncertain','tie':'tie','automatic':'tie'}[wanted]
            choice=dict.fromkeys(FIELDS,val)
            human=None if wanted=='automatic' else {who:{'canonical':choice.copy(),'confidence':.75,'current_view_elapsed_seconds':2.0} for who in ('annotator-a','annotator-b')}
            rows.append({'schema_version':'1','protocol':acfg.protocol,'family':family,'sample_id':sid,'trial_id':f'fixture-{sid}-{rep}',
                         'replicate':rep,'comparison_id':f'fixture-{family}-{sid}-{rep}','source':'automatic_tie' if wanted=='automatic' else 'human_pair',
                         'reason':'media_identity' if wanted=='automatic' else None,'aggregate':choice,'human':human,'proposed_side':'X',
                         'candidate_x':{'role':'constrained-pareto-n4','candidate_id':x['candidate_id'],'video_sha256':x['video']['sha256']},
                         'candidate_y':{'role':'constrained-pareto-n1' if family==FAMILIES[0] else 'equal-linear-n4','candidate_id':y['candidate_id'],'video_sha256':y['video']['sha256']}})
    agree=agreement_statistics(rows); rates=rate_statistics(rows,acfg); bt=bradley_terry_statistics(rows,acfg)
    draws,boot=cluster_bootstrap(rows,FIELDS,FAMILIES,20260901,2000,7,[.025,.975],'linear')
    fail=build_failure_cases(rows,acfg); summary=build_summary(rows,agree,rates,boot,bt,annotation_descriptives(rows),fail['count'],acfg)
    main=[{k:str(v) if v is not None else '' for k,v in row.items()} for row in build_main_rows(rates,boot,acfg) if row['scope']=='all-42']
    agreement=[{k:str(v) if v is not None else '' for k,v in row.items()} for row in build_agreement_rows(agree)]
    entries={}
    for name,value,unit in [('e0_generation_runtime_sum',100.0,'seconds'),('e0_generation_peak_vram_max',500.0,'MB'),('d2_scoring_total_elapsed',5.0,'seconds'),('d2_scoring_per_candidate_elapsed',.1,'seconds/candidate'),('d2_selection_elapsed',None,'seconds'),('d4_analysis_compute_elapsed',.1,'seconds'),('d3_annotator-a_current_view_elapsed_sum',64.0,'seconds'),('d3_annotator-b_current_view_elapsed_sum',64.0,'seconds')]:
        entries[name]={'value':value,'unit':unit,'status':'unavailable' if value is None else 'available','semantics':'synthetic engineering value; not research','source_sha256':None}
    costs={'entries':entries}
    for name,value in [('summary.json',summary),('bt.json',bt),('failure-cases.json',fail),('costs.json',costs)]: (root/'analysis'/name).write_bytes(json_bytes(value))
    (root/'analysis/main-table.csv').write_bytes(csv_bytes(main)); (root/'analysis/agreement.csv').write_bytes(csv_bytes(agreement))
    (root/'ingest/normalized-manifest.json').write_bytes(json_bytes(manifest))
    (root/'selection/selections.jsonl').write_text('\n'.join(json.dumps({'n':2,'method':'constrained-pareto','audit':{'fallback':True}}) for _ in range(26))+'\n',encoding='utf-8')
    inputs=Inputs(aggregate=root/'aggregate',analysis=root/'analysis',d4_verification=root/'verification.json',selection=root/'selection',metrics=root/'metrics',design=root/'design',ingest=root/'ingest/normalized-manifest.json')
    projected=[{k:v for k,v in row.items() if k not in ('human','reason','schema_version','protocol')} for row in rows]
    (root/'aggregate/aggregate.jsonl').write_text('\n'.join(json.dumps(r) for r in projected)+'\n',encoding='utf-8')
    data={'evidence_status':'synthetic-engineering-only','cfg':cfg,'pins':{},'summary':summary,'main':main,'agreement':agreement,'bt':bt,'failure':fail,'manifest':manifest,'rows':projected,'costs':costs,'selection_summary':{'pareto_fallbacks':26},'metrics_summary':{}}
    data['cases']=select_cases(projected,manifest,fail,cfg)
    return data,inputs
