"""Separate module CLI preserves the frozen D4 top-level source identity."""
import argparse
import json
from pathlib import Path
from .core import Inputs,CONFIG


def main():
    parser=argparse.ArgumentParser(description='D5 CPU-only audited report and Slides draft')
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ('report','verify-report'):
        p=sub.add_parser(command)
        for name in ('aggregate','analysis','d4-verification','selection','metrics','design','ingest'):
            p.add_argument('--'+name,type=Path,required=True)
        p.add_argument('--config',type=Path,default=CONFIG);p.add_argument('--output',type=Path,required=True)
        if command=='report':
            for name in ('runtime-python','runtime-node','runtime-modules','slides-skill'): p.add_argument('--'+name,type=Path,required=True)
        else:p.add_argument('--report',type=Path,required=True)
    args=vars(parser.parse_args());command=args.pop('command'); output=args.pop('output')
    if command=='report':
        from .build import run_report
        runtime={key:args.pop(arg) for key,arg in [('python','runtime_python'),('node','runtime_node'),('modules','runtime_modules'),('skill','slides_skill')]}
        result=run_report(Inputs(**args),output,runtime)
        print(json.dumps({'status':result['status'],'evidence_status':result['evidence_status'],'script_timing':result['script_timing']},ensure_ascii=False))
    else:
        from .verification import verify_report
        root=args.pop('report'); result=verify_report(root,Inputs(**args),output)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__=='__main__': main()
