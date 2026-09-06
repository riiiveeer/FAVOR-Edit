"""Independent D5 content, linkage, package, render and provenance checks."""
import hashlib
import json
import os
import re
import tempfile
import uuid
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import unquote

from PIL import Image
from defense_mvp.annotation_bundle import read_json,verify_sums
from defense_mvp.io import rename_noreplace
from defense_mvp.models import validate_relative_path
from .core import load_inputs,source_identity,sha256_file,json_bytes,verify_pins
from .build import stable_payload,write_stable

NS={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}


def inventory(root):
    root=Path(root); result={}
    for line in (root/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        sha,rel=line.split('  ',1); validate_relative_path(rel)
        if rel in result or not re.fullmatch('[0-9a-f]{64}',sha): raise ValueError('invalid report inventory')
        if sha256_file(root/rel)!=sha: raise ValueError('report checksum mismatch: '+rel)
        result[rel]=sha
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    additions={'SHA256SUMS','verification.json','visual-qa.json'}
    if actual-set(result)-additions or set(result)-actual or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('unknown report files or symlinks')
    return result


def check_links(root):
    checked=0
    for p in [root/'report/DEFENSE_REPORT.md',*sorted((root/'report/cases').glob('*.html'))]:
        text=p.read_text(encoding='utf-8')
        refs=re.findall(r'\]\(([^)]+)\)',text) if p.suffix=='.md' else re.findall(r'(?:src|href)="([^"]+)"',text)
        for ref in refs:
            if re.match(r'^[a-zA-Z]+:',ref) or ref.startswith(('/', '\\')): raise ValueError('external/absolute public link')
            dest=(p.parent/unquote(ref.split('#')[0])).resolve()
            if not dest.is_relative_to(root.resolve()) or not dest.is_file(): raise ValueError('broken/escaping report link')
            checked+=1
    return checked


def expected_texts(d,sd):
    text=[]
    if d['index']==1:
        text=['Defense MVP / D5 初稿',d['lead'],*d['body']]
    else:
        text=[d['title']]
        kind=d['kind']
        if kind=='scope': text += [d['lead'],*d['body'],'主表严格保留定量范围']
        elif kind=='system':
            for i,v in enumerate(d['flow']):
                text.append(v)
                if i<3:text.append('→')
            text += ['↓','←','←',*d['body']]
        elif kind=='metrics': text += [s for row in d['metrics'] for s in row]
        elif kind=='selection': text += [d['lead'],*d['body'],'N=1 baseline\nEqual-linear N=4\nConstrained Pareto/max-min N=4']
        elif kind=='blind': text += [d['lead'],*d['body']]
        elif kind=='results':
            for i,row in enumerate(r for r in sd['main'] if r['field']=='overall'):
                text += ['对 N=1 baseline' if i==0 else '对 Linear N=4',f"W/L/T/U  {row['wins']}/{row['losses']}/{row['ties']}/{row['uncertain']}",f"n={row['total']}    tie-aware {float(row['tie_aware_win_rate']):.3f}"]
        elif kind=='cases':
            for label in d['case_labels']: text += [label,'由上至下：输入 / Proposed / 对照']
            text.append(d['body'][0])
        elif kind=='limitations': text+=d['body']
        elif kind=='next': text += [d['lead'],*d['body']]
    return text+[d['footer']]


def _normalize(text): return re.sub(r'\s+','',text)


def verify_pptx(root,sd):
    pptx=root/'slides/DEFENSE_MVP_D5_DRAFT.pptx'; receipt=read_json(root/'slides/slides-receipt.json')
    if receipt['pptx_sha256']!=sha256_file(pptx) or receipt['slide_data_sha256']!=sha256_file(root/'report/slide-data.json') or receipt['page_count']!=10:
        raise ValueError('slides receipt mismatch')
    with zipfile.ZipFile(pptx) as z:
        if z.testzip() is not None: raise ValueError('PPTX zip CRC mismatch')
        names=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        if len(names)!=10: raise ValueError('PPTX page count drift')
        relns={'r':'http://schemas.openxmlformats.org/package/2006/relationships'}
        expected_images={7:['report/figures/overall-ci.png'],8:[f'report/cases/media/case-{i}-sheet.png' for i in (1,2,3)],9:['report/figures/agreement.png']}
        for i,d in enumerate(sd['slides'],1):
            tree=ET.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
            actual=[]
            for shape in tree.findall('.//p:sp',NS):
                vals=shape.findall('.//a:t',NS)
                if vals: actual.append(''.join(v.text or '' for v in vals))
            if [_normalize(s) for s in actual]!=[_normalize(s) for s in expected_texts(d,sd)]:
                raise ValueError(f'PPTX text/number semantics mismatch on page {i}')
            note=ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml'))
            note_text=''.join(t.text or '' for t in note.findall('.//a:t',NS))
            if _normalize(d['notes']) not in _normalize(note_text): raise ValueError('PPTX speaker notes mismatch')
            rels=ET.fromstring(z.read(f'ppt/slides/_rels/slide{i}.xml.rels'))
            images=[]
            for rel in rels:
                if rel.attrib['Type'].endswith('/image'):
                    if rel.attrib.get('TargetMode')=='External': raise ValueError('external PPTX image')
                    import posixpath
                    target=posixpath.normpath(posixpath.join('ppt/slides',rel.attrib['Target'])).lstrip('/')
                    images.append(hashlib.sha256(z.read(target)).hexdigest())
            if sorted(images)!=sorted(sha256_file(root/p) for p in expected_images.get(i,[])): raise ValueError('PPTX image binding mismatch')
    for i in range(1,11):
        p=root/'slides/rendered'/f'slide-{i:02}.png'
        with Image.open(p) as image:
            image.load()
            if image.size!=(1280,720): raise ValueError('render dimensions mismatch')
        if receipt['render_sha256'][p.name]!=sha256_file(p): raise ValueError('render receipt mismatch')
    with Image.open(root/'slides/contact-sheet.png') as sheet:
        if sheet.size!=(2560,3600): raise ValueError('contact sheet dimensions mismatch')
        for i in range(10):
            with Image.open(root/'slides/rendered'/f'slide-{i+1:02}.png') as frame:
                if sheet.crop(((i%2)*1280,(i//2)*720,(i%2+1)*1280,(i//2+1)*720)).tobytes()!=frame.convert('RGB').tobytes(): raise ValueError('contact sheet content mismatch')
    validation=read_json(root/'build/presentation-validation.json')
    if (validation['finalSha256']!=sha256_file(pptx) or validation['packageIntegrity']['status']!='pass'
        or validation['presentationLayout']['findingCount']!=0 or validation['presentationLayout']['warning_count']!=0
        or not validation['firstPartyImport']['passed'] or not validation['fontSelection']['passed']):
        raise ValueError('skill finalization status invalid')
    return receipt


def verify_stable(root,inputs,data,runtime,check_source=True,require_visual=True):
    root=Path(root).resolve(); sums=inventory(root); verify_sums(root/'report')
    manifest=read_json(root/'report/input-manifest.json'); receipt=read_json(root/'report/report-receipt.json')
    if manifest['inputs']!=data['pins'] or receipt['inputs']!=data['pins']: raise ValueError('input provenance mismatch')
    if manifest['config_sha256']!=sha256_file(inputs.config): raise ValueError('config provenance mismatch')
    if check_source:
        source=source_identity()
        if any(manifest['source'][k]!=source[k] for k in ('files','python','platform')) or receipt['source']!=manifest['source']: raise ValueError('report source drift')
    scratch=Path(tempfile.mkdtemp(prefix='defense-d5-rebuild-'))
    content,_=write_stable(data,inputs,scratch,runtime)
    expected_files={p.relative_to(scratch).as_posix() for p in scratch.rglob('*') if p.is_file()}
    for name in expected_files:
        if (root/name).read_bytes()!=(scratch/name).read_bytes(): raise ValueError('stable report recomputation mismatch: '+name)
    allowed=expected_files|{'report/input-manifest.json','report/report-receipt.json','report/SHA256SUMS',
        'slides/DEFENSE_MVP_D5_DRAFT.pptx','slides/slides-receipt.json','slides/contact-sheet.png',
        'build/candidate.pptx','build/candidate.pptx.inspect.ndjson','build/presentation-inspect.ndjson','build/presentation-validation.json'}
    allowed|={f'slides/rendered/slide-{i:02}.png' for i in range(1,11)}|{f'build/slide-{i:02}.layout.json' for i in range(1,11)}
    if set(sums)!=allowed: raise ValueError('unknown/missing D5 output inventory')
    if receipt['script_timing']!=content['timing']: raise ValueError('script timing receipt mismatch')
    for p in (root/'report/figures').glob('*.svg'): ET.parse(p)
    for p in (root/'report/figures').glob('*.png'):
        with Image.open(p) as im:
            im.load()
            if im.size!=(data['cfg']['figures']['width'],data['cfg']['figures']['height']): raise ValueError('figure dimensions invalid')
    link_count=check_links(root)
    sd=read_json(root/'report/slide-data.json'); sr=verify_pptx(root,sd)
    qa_path=root/'visual-qa.json'
    if require_visual:
        qa=read_json(qa_path)
        if qa['status']!='passed' or qa['pptx_sha256']!=sr['pptx_sha256'] or qa['render_sha256']!=sr['render_sha256'] or len(qa['pages'])!=10 or any(p['status']!='passed' for p in qa['pages']): raise ValueError('visual QA identity/status invalid')
    result={'schema_version':'1','protocol':'defense-report-v1','status':'passed' if require_visual else 'engineering-verified-awaiting-visual-review',
            'evidence_status':data.get('evidence_status','verified-formal-d4'),'input_sha256':data['pins'],
            'source_files':manifest['source']['files'],'source_commit':manifest['source']['git_head'],
            'report_inventory_sha256':sha256_file(root/'SHA256SUMS'),'report_sha256':sha256_file(root/'report/DEFENSE_REPORT.md'),
            'pptx_sha256':sr['pptx_sha256'],'page_count':10,'render_sha256':sr['render_sha256'],
            'script_timing':content['timing'],'links_checked':link_count,'stable_files_rebuilt':len(expected_files),
            'case_count':4,'failure_index_count':data['failure']['count'],
            'visual_qa_sha256':sha256_file(qa_path) if require_visual else None,
            'rebuild_equality':'stable report, CSV, SVG, PNG, cases and script byte-identical; PPTX text/image/notes semantics verified'}
    if (root/'verification.json').is_file() and read_json(root/'verification.json')!=result: raise ValueError('stored D5 verification mismatch')
    return result


def verify_report(root,inputs,output,runtime=None):
    output=Path(output).resolve()
    if os.path.lexists(output): raise FileExistsError('verification output already exists')
    data=load_inputs(inputs)
    if runtime is None: runtime=read_json(Path(root)/'report/report-receipt.json')['runtime']
    result=verify_stable(root,inputs,data,runtime)
    verify_pins(inputs,data['cfg'])
    tmp=output.with_name('.'+output.name+'-'+uuid.uuid4().hex+'.staging'); tmp.parent.mkdir(parents=True,exist_ok=True)
    tmp.write_bytes(json_bytes(result)); rename_noreplace(tmp,output)
    return result
