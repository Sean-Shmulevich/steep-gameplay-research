#!/usr/bin/env python3
"""Build independently authored Windows mod-host sources; never launches a game."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--adapter', choices=('fixture', 'steep'), default='fixture')
    ap.add_argument('--capture-plugin', action='store_true', help='Build opt-in experimental update capture plugin; steep adapter only')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--cc', default='x86_64-w64-mingw32-gcc')
    args = ap.parse_args()
    if args.capture_plugin and args.adapter != 'steep':
        ap.error('--capture-plugin requires --adapter steep')
    cc = shutil.which(args.cc)
    if not cc:
        ap.error('MinGW x64 compiler unavailable: '+args.cc)
    out = args.out.resolve()
    if out.is_relative_to(ROOT):
        ap.error('Use an output directory outside the findings repository')
    out.mkdir(parents=True, exist_ok=True)
    (out/'plugins').mkdir(exist_ok=True)
    src = ROOT/'native/snow_host'
    flags = [cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(src)]
    def build(name, sources, extra):
        subprocess.run(flags+[str(src/s) for s in sources]+extra+['-o', str(out/name)], check=True, timeout=120)
    build('snow_host.dll', ['snow_host.c','snow_plugins.c', args.adapter+'_adapter.c'] + (['snow_update_snapshot.c'] if args.adapter=='steep' else []), ['-shared','-lws2_32'])
    build('host_loader.exe', ['host_loader.c'], ['-municode'])
    build('startup_launcher.exe', ['startup_launcher.c'], ['-municode','-luser32'])
    build('plugins/step_logger.dll', ['examples/step_logger.c'], ['-shared'])
    build('plugins/player_logger.dll', ['examples/player_logger.c'], ['-shared'])
    build('snow_update_probe.dll', ['snow_update_probe.c','snow_update_trace.c','snow_update_snapshot.c','snow_entry_attribution.c','snow_entry_thunk.S'], ['-shared'])
    if args.capture_plugin:
        build('plugins/update_capture.dll', ['examples/update_capture.c','steep_adapter.c','snow_update_probe.c','snow_update_trace.c','snow_update_snapshot.c','snow_entry_attribution.c','snow_entry_thunk.S'], ['-shared'])
    (out/'build.json').write_text(json.dumps({'adapter':args.adapter,'game_launched':False},indent=2)+'\n')
    print(json.dumps({'ok':True,'adapter':args.adapter,'output':str(out),'game_launched':False}))

if __name__ == '__main__':
    main()
