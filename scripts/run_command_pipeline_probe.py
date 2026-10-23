#!/usr/bin/env python3
"""Build/run the authored C command pipeline with a synthetic dispatcher only."""
import argparse
import json
import os
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='cc', help='Native 64-bit C11 compiler for this OS')
    args = parser.parse_args()
    cc = shutil.which(args.cc)
    if not cc:
        parser.error('native C compiler unavailable: ' + args.cc)
    env = os.environ.copy()
    if sys.platform == 'darwin' and not env.get('SDKROOT'):
        sdk = subprocess.run(['xcrun', '--sdk', 'macosx', '--show-sdk-path'],
                             check=True, capture_output=True, text=True, timeout=10)
        env['SDKROOT'] = sdk.stdout.strip()
    src = ROOT / 'native/snow_host'
    with tempfile.TemporaryDirectory(prefix='snow-command-pipeline-') as tmp:
        exe = Path(tmp) / ('probe.exe' if os.name == 'nt' else 'probe')
        command = [cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(src)]
        command += [str(src / name) for name in ('snow_command_admission.c',
            'snow_command_observation.c', 'snow_delegate_trace.c', 'examples/command_pipeline_probe.c')]
        subprocess.run(command + ['-o', str(exe)], check=True, timeout=60, env=env)
        result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=10)
        sys.path.insert(0, str(ROOT))
        from engine.command_phase import correlate_command_phases
        report = json.loads(result.stdout)
        domain = dict(session_id='synthetic-probe', clock_id='monotonic-counter', ticks_per_second=1)
        report['phase_correlation'] = correlate_command_phases(
            report['command_records'], report['phase_records'],
            command_domain=domain, phase_domain=domain,
            command_dropped=sum(r['recorder_dropped'] for r in report['requests']))
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
