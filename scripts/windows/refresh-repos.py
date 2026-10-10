"""Bounded read-only repository inventory. No network or Git index writes."""
import argparse
import json
import os
import subprocess
from pathlib import Path

def inventory(roots):
    records = []
    excluded = {'.git', 'node_modules', '.venv', 'venv', 'vendor', 'dist', 'build', 'AppData', 'transcripts', 'recordings', '_repo-admin'}
    for root in roots:
        if not root.is_dir():
            continue
        for directory, dirs, files in os.walk(root):
            dirs[:] = [name for name in dirs if name not in excluded]
            path = Path(directory)
            if not (path / '.git').exists():
                continue
            dirs.clear()
            def git(*args):
                try:
                    result = subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3, env=os.environ | {'GIT_OPTIONAL_LOCKS':'0', 'GIT_TERMINAL_PROMPT':'0'})
                    return result.stdout.strip() if result.returncode == 0 else None
                except (OSError, subprocess.TimeoutExpired):
                    return None
            status=git('status','--porcelain=v1','--untracked-files=no')
            records.append({'name':path.name,'path':str(path),'head':git('rev-parse','HEAD') or '', 'branch':git('symbolic-ref','--short','-q','HEAD') or 'DETACHED','status':'unknown_timeout' if status is None else 'dirty' if status else 'clean'})
    return list({row['path']:row for row in records}.values())

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config-root',type=Path,required=True)
    args=parser.parse_args()
    roots=[Path.home()/'code',Path.home()/'Projects',Path.home()/'Documents'/'GitHub']
    if os.name=='nt': roots += [Path('E:/GitHub')]
    records=inventory(roots)
    args.config_root.mkdir(parents=True,exist_ok=True)
    target=args.config_root/'repos.json'
    temporary=target.with_suffix('.tmp')
    temporary.write_text(json.dumps({'repositories':records},ensure_ascii=False),encoding='utf8')
    temporary.replace(target)
    print(f'Read-only repository inventory: {len(records)} repositories')
