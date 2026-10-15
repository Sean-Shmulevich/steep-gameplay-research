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
parser.add_argument('--plan', choices=['demo', 'stress'], default='demo')
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


def capture(name):
    subprocess.run([str(TB/'run3/mac-game-capture'), str(out/(name + '.png'))], capture_output=True, timeout=15)


def advancing(client, wait=1.0):
    a = client.call('simulation.status')['engine']; time.sleep(wait); b = client.call('simulation.status')['engine']
    return not b['held'] and a['step'] != b['step']


def steps_ok(r):
    return r['completed'] == r['requested'] and r['exactly_one'] == r['requested']


def hold_forward(ident, ms=1500):
    """Background SendInput hold of the forward key (scan 17) on the verified game window."""
    control = TB/'run3/control/input-control.exe'
    p = subprocess.run(helper + [str(control), 'windows', '--pid', str(ident['pid']), '--image', 'steep.exe'],
                       capture_output=True, text=True, timeout=20)
    rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
    tid = next(x for x in rows if x.get('kind') == 'target_identity')
    win = [x for x in rows if x.get('kind') == 'window' and x.get('title') == 'Steep' and x.get('visible')]
    assert len(win) == 1, 'game window not unique'
    argv = helper + [str(control), 'hold', '--pid', str(ident['pid']), '--image', 'steep.exe', '--hwnd', win[0]['hwnd'],
                     '--created', tid['creation_filetime'], '--mode', 'sendinput', '--scan', '17', '--duration-ms', str(ms), '--focus']
    return subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def stress(client, ident):
    """Long run, repeated toggles, then pause/step while moving. Every phase ends resumed."""
    s = {}
    # 1. One pause, 300 single steps in batches of 60.
    batches = []
    try:
        client.call('simulation.pause', lease_ms=30000)
        for _ in range(5):
            r = client.call('simulation.step_world', count=60)
            batches.append({'ok': steps_ok(r), 'max_release_ms': r.get('max_release_ms')})
    finally:
        client.request('simulation.resume')
    s['long'] = {'batches': batches, 'ok': len(batches) == 5 and all(b['ok'] for b in batches), 'resumed': advancing(client)}
    # 2. Ten pause/step(5)/resume cycles.
    cycles = []
    for _ in range(10):
        try:
            client.call('simulation.pause', lease_ms=30000)
            cycles.append(steps_ok(client.call('simulation.step_world', count=5)))
        finally:
            client.request('simulation.resume')
        cycles.append(advancing(client, .5))
    s['toggles'] = {'ok': all(cycles) and len(cycles) == 20}
    # 3. Moving: hold forward 1.5 s, pause mid-hold, step while frames are captured.
    motion = {}
    for k in range(2):
        hold_forward(ident).wait(timeout=20)
    hold = hold_forward(ident); time.sleep(.8)
    try:
        client.call('simulation.pause', lease_ms=30000); capture('motion-0-paused')
        hold.wait(timeout=20)  # key released while paused
        time.sleep(1.0); capture('motion-1-held-1s')
        r1 = client.call('simulation.step_world', count=30); capture('motion-2-after-30')
        r2 = client.call('simulation.step_world', count=30); capture('motion-3-after-60')
        motion['steps_ok'] = steps_ok(r1) and steps_ok(r2)
    finally:
        client.request('simulation.resume')
    motion['resumed'] = advancing(client)
    s['motion'] = motion
    s['ok'] = s['long']['ok'] and s['long']['resumed'] and s['toggles']['ok'] and motion.get('steps_ok') and motion['resumed']
    return s


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
    result['plugins_before'] = client.call('plugins.list')['plugins']
    assert hello['bound'] and hello['ordinary'], 'Adapter not bound or engine not ordinary: ' + str(hello.get('bind_error') or hello.get('read_error'))
    if args.plan == 'stress':
        result['stress'] = stress(client, i)
        assert result['stress']['ok'], 'Stress plan failed; see result.json'
    else:
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
    result['plugins_after'] = client.call('plugins.list')['plugins']
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
