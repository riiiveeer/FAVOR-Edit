"""Deterministic public document copies with a verifiable link rewrite only."""
import re
from pathlib import Path
from .core import json_bytes,sha256_file


def public_files(root, repository):
    root=Path(root).resolve(); repository=Path(repository).resolve()
    relative=root.relative_to(repository).as_posix()
    report=(root/'report/DEFENSE_REPORT.md').read_text(encoding='utf-8')
    def rewrite(match):
        link=match.group(1)
        if link.startswith(('tables/','figures/')): dest='d5_generated/'+link
        else: dest='../../'+relative+'/report/'+link
        return ']('+dest+')'
    report=re.sub(r'\]\(([^)]+)\)',rewrite,report)
    files={'DEFENSE_REPORT.md':report.encode('utf-8'),
           'DEFENSE_SCRIPT.md':(root/'script/DEFENSE_SCRIPT.md').read_bytes(),
           'RECORDING_PLAN.md':(root/'script/RECORDING_PLAN.md').read_bytes()}
    for folder in ('tables','figures'):
        for p in sorted((root/'report'/folder).iterdir()):
            if p.suffix in ('.csv','.svg','.png'): files['d5_generated/'+folder+'/'+p.name]=p.read_bytes()
    import hashlib
    receipt={'schema_version':'1','source_root':relative,'source_report_sha256':sha256_file(root/'report/DEFENSE_REPORT.md'),
             'relationship':'report changes relative links only; script, plan, tables and figures are byte copies',
             'files':{name:hashlib.sha256(value).hexdigest() for name,value in files.items()}}
    files['d5_generated/public-export.json']=json_bytes(receipt)
    return files


def export_public(root,repository,destination):
    files=public_files(root,repository); destination=Path(destination)
    for name,value in files.items():
        p=destination/name
        if p.exists(): raise FileExistsError('public destination exists: '+name)
    for name,value in files.items():
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value)
    verify_public(root,repository,destination)
    return sorted(files)


def verify_public(root,repository,destination):
    files=public_files(root,repository)
    for name,value in files.items():
        if (Path(destination)/name).read_bytes()!=value: raise ValueError('public copy drift: '+name)
    return {'status':'passed','public_files':len(files)}
