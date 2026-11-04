#!/usr/bin/env python3
import argparse
import json
from inteldoc.world import expand, load_world, ROOT
from inteldoc.pipeline import plan, run, score

parser=argparse.ArgumentParser(description='Reproducible, zero-cost fictional corpus baseline')
parser.add_argument('command',choices=['world','plan','generate','evaluate','build'])
parser.add_argument('--count',type=int,default=5000)
parser.add_argument('--seed',type=int,default=42)
parser.add_argument('--limit',type=int)
parser.add_argument('--retry-failed',action='store_true')
args=parser.parse_args()
failed=0
if args.command=='world':
    w=expand(args.seed);print(json.dumps({'entities':len(w['entities']),'events':len(w['events'])}))
if args.command in ['plan','build']:
    load_world();print(json.dumps({'planned':plan(args.count,args.seed)}))
if args.command in ['generate','build']:
    result=run(args.limit,args.retry_failed)
    print(json.dumps(result))
    failed=result['failed']
if args.command in ['evaluate','build']:
    result=score(); (ROOT/'corpus/scorecard.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if failed:raise SystemExit(1)
