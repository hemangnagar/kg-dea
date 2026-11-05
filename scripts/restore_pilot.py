#!/usr/bin/env python3
"""Restore the exact synthetic snapshot using only Python's standard library.

No models, network requests, world expansion, regeneration, or credential access.
Existing differing files are rejected before any destination files are written.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tarfile
import tempfile


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def allowed(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts:return False
    exact={'world/expanded.json','world/graph_truth.json','world/pilot/expanded.json',
           'world/pilot/graph_truth.json','corpus/manifest.sqlite',
           'corpus/api-pilot/manifest.sqlite','corpus/api-pilot/selection.json','corpus/scorecard.json'}
    return (name in exact or (len(p.parts)==3 and p.parts[:2] in [('corpus','xml'),('corpus','truth')]
                              and p.suffix in ['.xml','.json']))


def restore(archive,destination):
    archive=archive.resolve();destination=destination.resolve()
    checksum=archive.with_suffix(archive.suffix+'.sha256')
    expected=checksum.read_text().split()[0]
    if digest(archive)!=expected:raise ValueError('Archive checksum mismatch')
    with tempfile.TemporaryDirectory(prefix='kg-pilot-restore-') as folder:
        stage=Path(folder)
        with tarfile.open(archive,'r:gz') as tar:
            members=tar.getmembers()
            if len(members)>20000 or sum(m.size for m in members)>512*1024*1024:
                raise ValueError('Archive exceeds recovery limits')
            if any(not m.isfile() for m in members):raise ValueError('Only regular files are permitted')
            names=[m.name for m in members]
            if len(names)!=len(set(names)):raise ValueError('Duplicate archive paths')
            index=tar.getmember('recovery.json')
            if index.size>8*1024*1024:raise ValueError('Oversized recovery index')
            manifest=json.load(tar.extractfile(index))
            if manifest.get('format')!=1 or manifest.get('contains_credentials') is not False:
                raise ValueError('Unsupported recovery format')
            files=manifest['files']
            if set(names)!=set(files)|{'recovery.json'}:raise ValueError('Archive/index membership mismatch')
            for name,metadata in files.items():
                if not allowed(name):raise ValueError('Unexpected recovery path: '+name)
                member=tar.getmember(name)
                if member.size!=metadata['size']:raise ValueError('File size mismatch: '+name)
                target=stage/name;target.parent.mkdir(parents=True,exist_ok=True)
                with tar.extractfile(member) as source,target.open('wb') as output:
                    shutil.copyfileobj(source,output)
                if digest(target)!=metadata['sha256']:raise ValueError('File checksum mismatch: '+name)
        for rel,expected_states in [('corpus/manifest.sqlite',{'validated':5000}),
                                    ('corpus/api-pilot/manifest.sqlite',{'planned':5000})]:
            db=sqlite3.connect('file:'+str(stage/rel)+'?mode=ro',uri=True)
            try:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Corrupt database')
                states=dict(db.execute('SELECT state,count(*) FROM cables GROUP BY state'))
                if states!=expected_states:raise ValueError('Unexpected archived manifest state')
                rows,spend=db.execute('SELECT count(*),COALESCE(sum(COALESCE(actual,reserved)),0) FROM spend').fetchone()
                if rows!=manifest['live_spend_rows'] or spend!=manifest['live_spend_usd']:
                    raise ValueError('Archived ledger does not match recovery index')
            finally:db.close()
        conflicts=[]
        for name,metadata in files.items():
            target=destination/name
            if not target.resolve().is_relative_to(destination):raise ValueError('Destination symlink escapes checkout')
            if target.is_symlink() or (target.exists() and (not target.is_file() or digest(target)!=metadata['sha256'])):
                conflicts.append(name)
            if name.endswith('.sqlite') and target.with_name(target.name+'-wal').exists():
                conflicts.append(name+'-wal (stop running services and inspect existing state)')
        if conflicts:raise ValueError('Existing state differs; nothing overwritten: '+', '.join(conflicts[:10]))
        restored=0
        for name in files:
            target=destination/name
            if target.exists():continue
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(stage/name,target);restored+=1
    return {'restored_files':restored,'baseline_validated':manifest['baseline_validated'],
            'pilot_planned':manifest['pilot_planned'],'pilot_validated':manifest['pilot_validated'],
            'historical_api_spend_usd':manifest['live_spend_usd'],'api_requests_made_by_restore':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/pilot-recovery-2026-11-05.tar.gz')
    parser.add_argument('--destination',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    try:print(json.dumps(restore(args.archive,args.destination),indent=2))
    except (ValueError,OSError,tarfile.TarError,KeyError,sqlite3.DatabaseError) as exc:
        parser.exit(1,'Recovery stopped: '+str(exc)+'\n')


if __name__=='__main__':main()
