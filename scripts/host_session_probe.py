"""Guarded live phase for the Snow mod host in the established local research workspace.

Loads native/snow_host into the verified running game, then drives it only through
the loopback command channel: status, pause, single world steps, resume, and a
20-second stability check. If the host cannot restore ordinary mode, the external
guarded byte restore in the private workspace is the fallback. No game addresses
appear in this script.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snow_host_client import SnowHostClient, demo

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--build', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--port', type=int, default=47017)
parser.add_argument('--steps', type=int, default=10)
args = parser.parse_args()
H = args.build.resolve(); R = args.workspace.resolve(); TB = R/'runtime/testbench'
out = args.output.resolve(); out.mkdir(exist_ok=False)
helper = [sys.executable, str(TB/'wine_helper.py')]
result = {'ok': False}
RESTORE = 'analysis/mod-host/private/restore_mode.py'


def run(tag, argv, timeout=60):
    p = subprocess.run(helper + [str(x) for x in argv], capture_output=True, text=True, timeout=timeout)
    (out/(tag + '.txt')).write_text(p.stdout + p.stderr)
    rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
    return rows[-1] if rows else {'ok': False, 'exit': p.returncode}


def connect(wait=15):
    end = time.monotonic() + wait
    while True:
        try:
            return SnowHostClient(port=args.port)
        except OSError:
            if time.monotonic() > end:
                raise
            time.sleep(.3)


def external_restore():
    """Last resort: the private, build-specific guarded compare-then-write restore."""
    argv = [sys.executable, str(R/RESTORE), str(out/'identity.json'), str(out)]
    if result.get('baseline_group'):
        argv.append(result['baseline_group'])
    p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    (out/'external_restore.txt').write_text(p.stdout + p.stderr)
    rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
    return rows[-1] if rows else {'ok': False, 'exit': p.returncode}


subprocess.run([sys.executable, str(TB/'run13/identify_game.py'), '--output', str(out/'identity.json')], check=True, timeout=35, capture_output=True)
i = json.loads((out/'identity.json').read_text()); assert i['ok'] and int(i['base'], 16) == 0x140000000
client = None
try:
    dll = 'Z:' + str(H/'snow_host.dll').replace('/', '\\')
    result['load'] = run('host_load', [H/'host_loader.exe', i['pid'], i['created'], dll, args.port])
    assert result['load'].get('ok'), 'Host loader did not verify start'
    client = connect()
    hello = client.call('host.hello')
    result['hello'] = hello
    assert hello['bound'] and hello['ordinary'], 'Adapter not bound or engine not ordinary: ' + str(hello.get('bind_error') or hello.get('read_error'))
    record = demo(client, args.steps, 30000)
    result['demo'] = record
    result['baseline_group'] = (record.get('pause') or {}).get('baseline_group')
    assert record['ok'], 'Demo failed: ' + str(record.get('error') or record.get('resume'))
    stability = []
    for k in range(5):
        if k:
            time.sleep(5)
        stability.append(client.call('simulation.status')['engine'])
    result['stability'] = stability
    result['stable_20_seconds'] = all(not s['held'] for s in stability) and all(a['step'] != b['step'] for a, b in zip(stability, stability[1:]))
    result['ok'] = result['stable_20_seconds']
except Exception as e:
    result['error'] = str(e)
finally:
    try:
        if client:
            client.close()  # The host resumes a held pause on disconnect.
            time.sleep(1.5)
        with connect(5) as c:
            final = c.call('simulation.status')
        result['final_status'] = final
        restored = final.get('ordinary', False)
    except Exception as e:
        result['final_status_error'] = str(e); restored = False
    if not restored:  # No-op when the group is already ordinary.
        try:
            result['external_restore'] = external_restore()
        except Exception as e:
            result['external_restore_error'] = str(e)
    result['ok'] = result['ok'] and restored
    (out/'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result.get(k) for k in ['ok', 'error', 'stable_20_seconds', 'final_status_error']}), flush=True)
raise SystemExit(0 if result['ok'] else 2)
