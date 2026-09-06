"""Fixed case media projection with checksum and pixel preserving copies."""
import html
import shutil
from pathlib import Path
from PIL import Image
from defense_mvp.metrics import _package_file
from .core import frame_indices, json_bytes


STYLE='body{font-family:"Microsoft YaHei",sans-serif;max-width:1500px;margin:32px auto;color:#172B3A;padding:20px}table{width:100%;table-layout:fixed;border-collapse:collapse}th,td{padding:6px;text-align:center}img{width:100%;height:auto}a{color:#0068A0}p{line-height:1.8}'


def render_cases(data, output):
    output=Path(output); media=output/'media'; media.mkdir(parents=True)
    manifest=data['manifest']; root=Path(manifest['delivery_root']); cfg=data['cfg']
    samples={r['sample_id']:r for r in manifest['samples']}; candidates={r['candidate_id']:r for r in manifest['candidates']}
    traces=[]; public=[]
    for i,item in enumerate(data['cases'],1):
        trace={'label':item['label'],'kind':item['kind'],'status':item['status']}; roles=[]
        if item['status']=='available':
            row=item.get('record'); sample=samples[row['sample_id'] if row else item['sample_id']]
            roles.append(('输入',sample['source_frames'],sample['source_video'],None,'source'))
            if row:
                for side in (row['proposed_side'].lower(),'y' if row['proposed_side']=='X' else 'x'):
                    c=candidates[row['candidate_'+side]['candidate_id']]
                    name='Proposed N=4' if side==row['proposed_side'].lower() else 'N=1 baseline'
                    if c['sample_id']!=sample['sample_id'] or c['video']['sha256']!=row['candidate_'+side]['video_sha256']: raise ValueError('case role/candidate/media drift')
                    roles.append((name,c['frames'],c['video'],c['candidate_id'],row['candidate_'+side]['role']))
                trace.update({k:row[k] for k in ('comparison_id','family','sample_id','trial_id','replicate','proposed_side')})
            else:
                for number,c in enumerate(sorted([c for c in candidates.values() if c['sample_id']==sample['sample_id']],key=lambda c:c['candidate_id']),1):
                    roles.append((f'定性候选{number}',c['frames'],c['video'],c['candidate_id'],'qualitative_only'))
                trace['sample_id']=sample['sample_id']
            indices=frame_indices(cfg['cases']['expected_frames'],cfg)
            trace.update(frame_indices=indices,roles=[],source_summary='D4 verified aggregate and D2 verified frame manifest')
            page=f'<h1>{html.escape(item["label"])}</h1><p>指令：{html.escape(sample["instruction"])}</p>'
            page+=f'<p>状态：{html.escape(item["kind"])}。按冻结规则选例；静态帧仅辅助核查，不能替代整段视频评估。</p>'
            page+='<table><tr><th>方法</th>'+''.join(f'<th>帧 {idx}</th>' for idx in indices)+'</tr>'
            sheet=Image.new('RGB',(4*512,len(roles)*512),'white')
            for j,(label,frames,video,cid,role) in enumerate(roles):
                if len(frames['relative_paths'])!=cfg['cases']['expected_frames'] or len(frames['sha256'])!=cfg['cases']['expected_frames']: raise ValueError('case frame count drift')
                _package_file(root,video['relative_path'],video['sha256'])
                role_trace={'label':label,'role':role,'candidate_id':cid,'video_sha256':video['sha256'],'frames':[]}
                page+=f'<tr><th>{html.escape(label)}</th>'
                for k,idx in enumerate(indices):
                    p=_package_file(root,frames['relative_paths'][idx],frames['sha256'][idx])
                    filename=f'case-{i}-role-{j}-frame-{idx}.png'
                    with Image.open(p) as image:
                        image.load()
                        if image.size!=tuple(cfg['cases']['pixel_size']) or image.mode!='RGB': raise ValueError('case frame size/mode mismatch')
                        sheet.paste(image,(k*512,j*512))
                    shutil.copyfile(p,media/filename)
                    role_trace['frames'].append({'index':idx,'sha256':frames['sha256'][idx],'source_relative_path':frames['relative_paths'][idx],'output':'media/'+filename})
                    page+=f'<td><img src="media/{filename}" alt="{html.escape(label)} 帧 {idx}"></td>'
                trace['roles'].append(role_trace); page+='</tr>'
            sheet.save(media/f'case-{i}-sheet.png')
            page+='</table><p>图片原帧复制，显示保持比例。来源：已验证D4/D2摘要；内部trace仅用于本地审计。</p>'
        else:
            trace['reason']=item['reason']; page=f'<h1>{html.escape(item["label"])}</h1><p>unavailable：{html.escape(item["reason"])}</p>'
        (output/f'case-{i}.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+item['label']+'</title><style>'+STYLE+'</style><body>'+page+'<p><a href="index.html">返回案例总览</a></p></body></html>',encoding='utf-8')
        traces.append(trace); public.append({k:trace[k] for k in ('label','kind','status')}|{'page':f'case-{i}.html'})
    (output/'trace-manifest.json').write_bytes(json_bytes({'cases':traces,'failure_index':data['failure']}))
    (output/'case-index.json').write_bytes(json_bytes({'cases':public,'failure_index_count':data['failure']['count']}))
    (output/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>确定性案例</title><style>'+STYLE+'</style><body><h1>固定案例与能力边界</h1><p>成功、失败、不确定来自正式聚合。定性边界不进入胜率。</p>'+''.join(f'<p><a href="{c["page"]}">{c["label"]}</a> · {c["status"]}</p>' for c in public)+'</body></html>',encoding='utf-8')
    return traces
