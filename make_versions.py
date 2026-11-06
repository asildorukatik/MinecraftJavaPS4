#!/usr/bin/env python3
"""Generate versions.json from real game HTML files in each version folder.

Run at the repository root: python3 make_versions.py
Does not modify game files or choose arbitrary HTMLs when ambiguous.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

SKIP = {'.git', '.github', 'assets', 'src', '__pycache__', 'node_modules', 'eaglercraft-adapter'}

def natural_key(label: str):
    return [int(x) if x.isdecimal() else x.lower() for x in __import__('re').split(r'(\d+)', label)]

def collect(root: Path):
    games = []
    warnings = []
    for folder in sorted((d for d in root.iterdir() if d.is_dir() and d.name not in SKIP and not d.name.startswith('.')), key=lambda d: natural_key(d.name)):
        html = sorted((f for f in folder.rglob('*') if f.is_file() and f.suffix.lower()=='.html'), key=lambda p: p.as_posix())
        if not html:
            continue
        preferred = [f for f in html if f.parent == folder and f.name.lower() == 'index.html']
        if len(preferred) == 1:
            entry = preferred[0]
        elif len(html) == 1:
            entry = html[0]
        else:
            warnings.append(f'{folder.name}: several HTML files found; rename the playable entry to index.html or remove extras: '+', '.join(p.relative_to(folder).as_posix() for p in html))
            continue
        files=[]
        total=0
        for f in sorted(folder.rglob('*')):
            if not f.is_file() or f.is_symlink():
                continue
            rel=f.relative_to(root).as_posix()
            if any(component.startswith('.') for component in f.relative_to(folder).parts):
                continue
            size=f.stat().st_size
            digest=hashlib.sha256()
            with f.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024), b''):
                    digest.update(chunk)
            files.append({'path':rel, 'bytes':size, 'sha256':digest.hexdigest()})
            total+=size
        if not any(item['path']==entry.relative_to(root).as_posix() for item in files):
            warnings.append(f'{folder.name}: entry HTML was excluded from the asset list')
            continue
        games.append({'id':folder.name,'title':'Eaglercraft '+folder.name,'entry':entry.relative_to(root).as_posix(), 'totalBytes':total,'files':files})
    if warnings:
        raise SystemExit('Please resolve these version folders before creating the manifest:\n- '+'\n- '.join(warnings))
    if not games:
        raise SystemExit('No version folders containing HTML files found. Run this script from MinecraftJavaPS4/.')
    return games

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent,help='Repository root')
    args=parser.parse_args()
    root=args.root.resolve()
    versions=collect(root)
    payload={'schema':1,'versions':versions}
    canonical=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    payload['catalogRevision']=hashlib.sha256(canonical).hexdigest()
    (root/'versions.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Wrote versions.json with '+str(len(versions))+' versions:')
    for v in versions:
        print(' - '+v['id']+' -> '+v['entry']+' ('+str(len(v['files']))+' files)')

if __name__=='__main__':
    main()
