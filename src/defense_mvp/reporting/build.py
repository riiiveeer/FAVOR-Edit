"""D5 staging, rendering and no-replace publication."""
import os
import json
import threading
import subprocess
import uuid
from pathlib import Path
from PIL import Image
from defense_mvp.annotation_bundle import stage, write_sums, now
from defense_mvp.io import rename_noreplace
from .core import audit_registry,build_facts,json_bytes,csv_bytes,load_inputs,source_identity,sha256_file,verify_pins
from .content import compose
from .cases import render_cases


def stable_payload(data,inputs):
    registry,main,agreement,costs=build_facts(data,inputs)
    audit_registry(registry,inputs)
    content=compose(registry,data)
    slide_data={'schema_version':'1','evidence_status':data.get('evidence_status','verified-formal-d4'),
                'config':data['cfg'],'facts':registry.entries,'main':main,'agreement':agreement,
                'slides':content['slides'],'flow':content['flow'],'input_sha256':data['pins']}
    files={'report/DEFENSE_REPORT.md':content['report'].encode('utf-8'),
           'report/tables/main-results.csv':csv_bytes(main),'report/tables/agreement.csv':csv_bytes(agreement),
           'report/tables/costs.csv':csv_bytes(costs),'report/report-data.json':json_bytes({'protocol':data['cfg']['protocol'],
               'evidence_status':data.get('evidence_status','verified-formal-d4'),'facts':registry.entries}),
           'report/slide-data.json':json_bytes(slide_data),'script/DEFENSE_SCRIPT.md':content['script'].encode('utf-8'),
           'script/RECORDING_PLAN.md':content['recording'].encode('utf-8')}
    return files,content


def create_contact_sheet(root):
    sheet=Image.new('RGB',(1280*2,720*5),'#E6EBEF')
    for i in range(10):
        with Image.open(root/'slides/rendered'/f'slide-{i+1:02}.png') as im:
            if im.size!=(1280,720): raise ValueError('slide render dimensions drift')
            sheet.paste(im.convert('RGB'),((i%2)*1280,(i//2)*720))
    sheet.save(root/'slides/contact-sheet.png')


def run_slides(root,runtime):
    command=[str(runtime['node']),str(Path(__file__).with_name('slides.mjs')),str(root/'report/slide-data.json'),str(root),str(runtime['modules']),str(runtime['skill']),str(runtime['python'])]
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8')
    watchdog=threading.Timer(180,lambda:process.kill() if process.poll() is None else None)
    watchdog.daemon=True;watchdog.start()
    log=[]
    try:
        for line in process.stdout:
            log.append(line)
            if not line.startswith('{'): continue
            try: message=json.loads(line)
            except json.JSONDecodeError: continue
            if message.get('status')!='rendered': continue
            # The renderer deliberately remains idle after every asynchronous write is complete.
            receipt=json.loads((root/'slides/slides-receipt.json').read_text(encoding='utf-8'))
            if message['pptx_sha256']!=sha256_file(root/'slides/DEFENSE_MVP_D5_DRAFT.pptx') or receipt['pptx_sha256']!=message['pptx_sha256']:
                raise ValueError('renderer completion SHA mismatch')
            if len(receipt['render_sha256'])!=10: raise ValueError('incomplete renderer completion')
            for name,digest in receipt['render_sha256'].items():
                if sha256_file(root/'slides/rendered'/name)!=digest: raise ValueError('renderer image SHA mismatch')
            process.terminate(); process.wait(timeout=15)
            receipt['worker_shutdown']={'strategy':'controller-termination-after-verified-completion','exit_code':process.returncode,
                                        'reason':'bundled Windows canvas native destructor crash; all completed exports verified first'}
            (root/'slides/slides-receipt.json').write_bytes(json_bytes(receipt))
            return
        raise subprocess.CalledProcessError(process.wait(),command,output=''.join(log),stderr='renderer exited without completed exports handshake')
    finally:
        watchdog.cancel()
        if process.poll() is None: process.kill();process.wait(timeout=15)


def write_stable(data,inputs,root,runtime):
    root=Path(root); files,content=stable_payload(data,inputs)
    for name,value in files.items():
        p=root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(value)
    traces=render_cases(data,root/'report/cases')
    subprocess.run([str(runtime['python']),str(Path(__file__).with_name('figures.py')),str(root/'report/slide-data.json'),str(root/'report/figures')],check=True,capture_output=True,text=True,encoding='utf-8')
    return content,traces


def build_draft(data,inputs,output,runtime):
    output=Path(output).resolve(); staging=stage(output)
    try:
        source=source_identity()
        content,traces=write_stable(data,inputs,staging,runtime)
        manifest={'protocol':data['cfg']['protocol'],'inputs':data['pins'],'source':source,
                  'config_sha256':sha256_file(inputs.config)}
        (staging/'report/input-manifest.json').write_bytes(json_bytes(manifest))
        run_slides(staging,runtime)
        create_contact_sheet(staging)
        receipt={'status':'draft-generated','created_at':now(),'evidence_status':data.get('evidence_status','verified-formal-d4'),
                 'protocol':data['cfg']['protocol'],'source':source,'inputs':data['pins'],'script_timing':content['timing'],
                 'case_labels':[c['label'] for c in traces],'runtime':{k:str(v) for k,v in runtime.items()},
                 'command':'python -m defense_mvp.reporting report --aggregate <D4/aggregate> --analysis <D4/analysis> --d4-verification <D4/verification.json> --selection <D2/selection> --metrics <D2/metrics> --design <D2/design> --ingest <D2/ingest/normalized-manifest.json> --config configs/defense_mvp/report-v1.yaml --output <new-root> --runtime-python <bundled-python> --runtime-node <bundled-node> --runtime-modules <bundled-modules> --slides-skill <installed-skill>'}
        (staging/'report/report-receipt.json').write_bytes(json_bytes(receipt))
        write_sums(staging/'report')
        if data.get('evidence_status')!='synthetic-engineering-only': verify_pins(inputs,data['cfg'])
        write_sums(staging)
        rename_noreplace(staging,output)
        return receipt
    except Exception as exc:
        diagnostic={'status':'failed','at':now(),'error_type':type(exc).__name__,'error':str(exc)}
        if isinstance(exc,subprocess.CalledProcessError): diagnostic.update(stdout=exc.stdout,stderr=exc.stderr)
        (staging/'FAILED.json').write_bytes(json_bytes(diagnostic))
        rename_noreplace(staging,output.with_name('.'+output.name+'-'+uuid.uuid4().hex+'.failed'))
        raise


def run_report(inputs,output,runtime):
    if os.path.lexists(output): raise FileExistsError('report output already exists')
    data=load_inputs(inputs)
    return build_draft(data,inputs,output,runtime)
