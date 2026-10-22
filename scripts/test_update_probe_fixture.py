#!/usr/bin/env python3
"""Build and run authored probe fixtures in an explicitly supplied Wine prefix.

Does not launch a game or install into a game directory. Output must be a fresh
external directory. Prefix must already exist; no wineboot/setup is requested.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wine', required=True, type=Path)
    p.add_argument('--prefix', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    cc = shutil.which('x86_64-w64-mingw32-gcc')
    out, prefix, wine = args.out.resolve(), args.prefix.resolve(), args.wine.resolve()
    if not cc or not wine.is_file() or not prefix.is_dir():
        p.error('MinGW, Wine executable and existing fixture prefix required')
    if out.is_relative_to(ROOT) or out.exists():
        p.error('Output must be a fresh directory outside the repository')
    out.mkdir(parents=True)
    native = ROOT/'native/snow_host'
    flags = [cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(native)]
    sources = ['snow_update_probe.c','snow_update_trace.c','snow_update_snapshot.c',
               'snow_entry_attribution.c','snow_batch_frame.c','snow_entry_thunk.S','snow_motion_observation.c']
    with (out/'build.log').open('w') as log:
        subprocess.run(flags+['-shared']+[str(native/s) for s in sources]+['-o',str(out/'probe.dll')],
                       stdout=log,stderr=log,check=True,timeout=60)
        subprocess.run(flags+[str(ROOT/'tests/fixtures/snow_update_probe_fixture.c'),
                              str(ROOT/'tests/fixtures/snow_entry_caller.S'),'-o',str(out/'fixture.exe')],
                       stdout=log,stderr=log,check=True,timeout=60)
    env = dict(os.environ,WINEPREFIX=str(prefix),WINEDEBUG='-all')
    results = []
    for mode in ['normal','conflict','attributed','valid-attribution','invalid-frame','motion']:
        command = [str(wine),str(out/'fixture.exe'),'Z:'+str(out/'probe.dll').replace('/','\\')]
        if mode != 'normal': command.append(mode)
        logpath = out/(mode+'.log')
        with logpath.open('w') as log:
            try:
                run = subprocess.run(command,env=env,stdout=log,stderr=log,timeout=45)
                code = run.returncode
            except subprocess.TimeoutExpired:
                code = None
        with logpath.open('rb') as log:
            log.seek(max(0,logpath.stat().st_size-4096))
            tail = log.read().decode(errors='replace')
        results.append({'mode':mode,'exit_code':code,'passed':code==0 and 'PASS:' in tail})
        if not results[-1]['passed']: break
    receipt = {'game_launched':False,'synthetic_objects_only':True,'cases':results,
               'passed':len(results)==6 and all(x['passed'] for x in results)}
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
