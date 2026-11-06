#!/usr/bin/env python3
import argparse
import json
from inteldoc.world import expand, load_world, use_world_dir
from inteldoc.pipeline import plan, run, score
from inteldoc.settings import load_config
from inteldoc.store import use_dataset, data_root


def main():
    parser=argparse.ArgumentParser(description='Reproducible fictional corpus, offline or model-assisted')
    parser.add_argument('command',choices=['world','plan','generate','evaluate','build','cdr'])
    parser.add_argument('--cdr-count',type=int,default=14000,help='Synthetic partner-agency call records to generate')
    parser.add_argument('--count',type=int,default=5000)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--limit',type=int)
    parser.add_argument('--retry-failed',action='store_true')
    parser.add_argument('--config',help='YAML provider and corpus settings; defaults to offline config')
    parser.add_argument('--world-dir',help='Separate expanded-world directory; also set INTELDOC_WORLD_DIR when serving it')
    parser.add_argument('--output-dir',help='Separate corpus directory; recommended for model pilots')
    parser.add_argument('--workers',type=int,default=1,help='Concurrent cables for model providers')
    args=parser.parse_args()
    if args.output_dir:use_dataset(args.output_dir)
    if args.world_dir:use_world_dir(args.world_dir)
    try:
        cfg=load_config(args.config)
        failed=0
        if args.command=='world':
            w=expand(args.seed);print(json.dumps({'entities':len(w['entities']),'events':len(w['events'])}))
        if args.command in ['plan','build']:
            load_world();print(json.dumps({'planned':plan(args.count,args.seed,cfg)}))
        if args.command in ['generate','build']:
            result=run(args.limit,args.retry_failed,cfg,args.workers)
            print(json.dumps(result));failed=result['failed']
        if args.command=='cdr':
            from inteldoc import cdr
            print(json.dumps({**cdr.generate(args.seed,args.cdr_count),**cdr.ingest()}))
        if args.command in ['evaluate','build']:
            result=score();data_root().mkdir(parents=True,exist_ok=True)
            (data_root()/'scorecard.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
        if failed:raise SystemExit(1)
    except (ValueError,OSError) as exc:
        parser.exit(1,f'Configuration error: {exc}\n')


if __name__=='__main__':main()
