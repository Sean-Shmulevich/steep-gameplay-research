"""Guarded live phase for the Snow mod host in the established local research workspace.

Loads native/snow_host into the verified running game, then drives it only through
the loopback command channel: status, pause, single world steps, resume, and a
20-second stability check. If the host cannot restore ordinary mode, the external
guarded byte restore in the private workspace is the fallback. No game addresses
appear in this script.
"""
import argparse, configparser, json, math, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snow_host_client import SnowHostClient, HostError, demo

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--build', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--port', type=int, default=47017)
parser.add_argument('--steps', type=int, default=10)
parser.add_argument('--plan', choices=['demo', 'acceptance', 'stress', 'speed', 'fast', 'animation', 'animation-motion', 'cached-parent', 'work-packet', 'update-capture'], default='demo')
parser.add_argument('--game-deadline', type=float)
parser.add_argument('--preloaded', action='store_true', help='Host was already loaded by the startup launcher')
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


def hold_forward(ident, ms=1500, scan=17):
    """Bounded SendInput hold on the verified game window; defaults to forward."""
    control = TB/'run3/control/input-control.exe'
    p = subprocess.run(helper + [str(control), 'windows', '--pid', str(ident['pid']), '--image', 'steep.exe'],
                       capture_output=True, text=True, timeout=20)
    rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
    tid = next(x for x in rows if x.get('kind') == 'target_identity')
    win = [x for x in rows if x.get('kind') == 'window' and x.get('title') == 'Steep' and x.get('visible')]
    assert len(win) == 1, 'game window not unique'
    argv = helper + [str(control), 'hold', '--pid', str(ident['pid']), '--image', 'steep.exe', '--hwnd', win[0]['hwnd'],
                     '--created', tid['creation_filetime'], '--mode', 'sendinput', '--scan', str(scan), '--duration-ms', str(ms), '--focus']
    return subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def animation_motion(client, ident):
    """One OS-delivered forward pulse, with sequential pose/body observations."""
    from animation_capture_probe import capture_animation
    record={'game_input_ingestion_verified': False, 'atomic_snapshot': False}
    record['before']=capture_animation(client,samples=8)
    child=hold_forward(ident,700)
    try:
        record['pulse_window']=capture_animation(client,samples=24)
    finally:
        # Bounded helper performs key-up in its finally block. Retain its report.
        text,_=child.communicate(timeout=20)
        (out/'animation-input.jsonl').write_text(text)
    events=[json.loads(line) for line in text.splitlines() if line.startswith('{')]
    released=any(e.get('kind')=='hold_complete' and e.get('all_injected_keys_released') for e in events)
    delivered=[e for e in events if e.get('kind')=='key_delivery']
    record['input']={'exit_code':child.returncode,'released':released,
                     'accepted_deliveries':sum(e.get('api_reported_sent')==1 for e in delivered),
                     'requested_duration_ms':700,'scan_code':17}
    record['after']=capture_animation(client,samples=8)
    record['ok']=child.returncode==0 and released and record['input']['accepted_deliveries']==2 and all(
        record[k]['ok'] for k in ('before','pulse_window','after'))
    return record


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


def fast_demo(client, ident):
    """Explicit high-speed visual experiment through the existing engine setter.

    Does not change the bounded boost API. One assignment only, never retry an
    uncertain setter response. Full 3D direction is preserved, including descent.
    """
    record = {'ok': False, 'target_speed': 90.0, 'eligibility': [], 'samples': []}
    result['fast'] = record
    # A recognized gameplay HUD can precede the actor. Wait while simulation is
    # running; only missing/changing-player refusals are retryable here.
    for _ in range(20):
        try:
            client.call('player.get')
            break
        except HostError as exc:
            if exc.response.get('result', {}).get('error') not in ('no_player', 'player_changed'):
                raise
            time.sleep(1)
    else:
        raise RuntimeError('Player body did not appear within 20 seconds')
    for attempt in range(6):
        client.call('simulation.pause', lease_ms=30000)
        try:
            before = client.call('player.get')
            record['eligibility'].append(before)
            speed = math.sqrt(sum(x*x for x in before['linear_velocity']))
            spin = math.sqrt(sum(x*x for x in before['angular_velocity']))
            if before['flags'] & 3 == 3 and 3 <= speed < 90 and spin <= .25:
                print('FAST_DEMO_READY: rider held; boost in 10 seconds', flush=True)
                for _ in range(10):
                    time.sleep(1)
                    client.call('host.heartbeat')
                v = [x * 90.0 / speed for x in before['linear_velocity']]
                record['before'] = before
                record['set'] = client.call('player.set_velocity', vx=v[0], vy=v[1], vz=v[2])
                after = record['set']['after']
                record['readback_matches'] = all(abs(a-b) < .001 for a,b in zip(after['linear_velocity'], v))
                (out/'fast-assignment.json').write_text(json.dumps(record, indent=2))
                break
        finally:
            client.call('simulation.resume')
        hold_forward(ident, 700).wait(timeout=20)
        time.sleep(.5)
    if 'set' not in record:
        raise RuntimeError('No eligible moving rider for fast demo')
    print('FAST_DEMO_RUNNING: 90 units/s assigned; watching for 30 seconds', flush=True)
    start = time.monotonic()
    while time.monotonic() - start < 30:
        time.sleep(1)
        record['samples'].append({'seconds': time.monotonic()-start, 'player': client.call('player.get')})
    record['ok'] = record['readback_matches'] and advancing(client, .5)
    return record


def speed_test(client, ident):
    from speed_acceptance import run_speed_acceptance
    def advance():
        child=hold_forward(ident,700)
        if child.wait(timeout=20):
            raise RuntimeError('Forward-input helper failed')
    return run_speed_acceptance(client,capture,advance)


subprocess.run([sys.executable, str(TB/'run13/identify_game.py'), '--output', str(out/'identity.json')], check=True, timeout=35, capture_output=True)
i = json.loads((out/'identity.json').read_text()); assert i['ok'] and int(i['base'], 16) == 0x140000000
client = None
try:
    dll = 'Z:' + str(H/'snow_host.dll').replace('/', '\\')
    result['load'] = {'ok': True, 'preloaded': True} if args.preloaded else run('host_load', [H/'host_loader.exe', i['pid'], i['created'], dll, args.port])
    assert result['load'].get('ok'), 'Host loader did not verify start'
    client = connect()
    ready_deadline = time.monotonic() + 30
    hello = client.call('host.hello')
    while not hello.get('ready', True) and time.monotonic() < ready_deadline:
        time.sleep(.25); hello = client.call('host.hello')
    result['hello'] = hello
    result['plugins_before'] = client.call('plugins.list')['plugins']
    assert hello.get('ready', True) and hello['bound'] and hello.get('ordinary'), 'Adapter not ready or engine not ordinary: ' + str(hello.get('bind_error') or hello.get('read_error'))
    def preparation_pulse():
        child=hold_forward(i,700)
        text,_=child.communicate(timeout=20)
        (out/'preparation-input.jsonl').write_text(text)
        events=[json.loads(line) for line in text.splitlines() if line.startswith('{')]
        return {'exit_code':child.returncode,'duration_ms':700,
                'keys_released':any(e.get('kind')=='hold_complete' and
                    e.get('all_injected_keys_released') for e in events)}
    if args.plan == 'update-capture':
        from update_capture_probe import capture_update
        from host_acceptance import prepare_rider
        result['preparation']=prepare_rider(client,preparation_pulse)
        assert result['preparation']['ok'], 'Rider preparation failed; capture not armed'
        result['player_before_capture']=client.call('player.get')
        time.sleep(.5)
        result['player_after_wait']=client.call('player.get')
        assert result['player_before_capture']['identity']==result['player_after_wait']['identity'], 'Player changed before capture'
        config=configparser.ConfigParser();config.read(H/'plugins/update_capture.ini')
        def steering_pulse():
            child=hold_forward(i,700,scan=30)
            text,_=child.communicate(timeout=20)
            (out/'capture-steering-input.jsonl').write_text(text)
            events=[json.loads(line) for line in text.splitlines() if line.startswith('{')]
            released=any(e.get('kind')=='hold_complete' and e.get('all_injected_keys_released') for e in events)
            deliveries=[e for e in events if e.get('kind')=='key_delivery']
            accepted=len(deliveries)==2 and all(e.get('api_reported_sent')==1 and e.get('scan_raw')==30 for e in deliveries)
            return {'ok':child.returncode==0 and released and accepted,'scan':30,'duration_ms':700,
                    'accepted_deliveries':sum(e.get('api_reported_sent')==1 for e in deliveries),
                    'exit_code':child.returncode,'keys_released':released,'os_delivery_only':True}
        pulse=steering_pulse if config.getboolean('capture','steering_pulse',fallback=False) else None
        result['update_capture']=capture_update(client,H,during_capture=pulse)
        assert result['update_capture']['ok'], 'Update capture failed; inspect plugin trace and host log'
    elif args.plan == 'acceptance':
        from host_acceptance import run_acceptance, prepare_rider
        result['preparation']=prepare_rider(client,preparation_pulse)
        assert result['preparation']['ok'], 'Rider preparation failed; no acceptance mutations attempted'
        result['acceptance'] = run_acceptance(client, lambda: speed_test(client, i), steps=args.steps, ready_wait_seconds=20)
        assert result['acceptance']['ok'], 'Acceptance stages incomplete; inspect individual results'
    elif args.plan == 'work-packet':
        if args.game_deadline is None:
            raise ValueError('work-packet requires actual game watchdog deadline')
        argv=[sys.executable,str(R/'analysis/animation-debugger/private/run_game_capture.py'),
              str(out/'identity.json'),str(out/'work-capture'),'--work-packet',
              '--game-deadline',str(args.game_deadline)]
        with (out/'work-capture.log').open('w') as log:
            subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=125)
        result['work_packet']=json.loads((out/'work-capture/result.json').read_text())
        wr=result['work_packet']
        assert (wr.get('debugger_exit')==0 and wr.get('detached') and wr.get('breakpoints_removed')
                and wr.get('code_unchanged') and not wr.get('errors') and not wr.get('outer_timeout')), 'Work observer did not finish cleanly'
    elif args.plan == 'cached-parent':
        from cached_parent_capture_probe import capture_cached_parent
        result['cached_parent'] = capture_cached_parent(client, samples=32)
        assert result['cached_parent']['ok'], 'No accepted cached-parent identity brackets; inspect retained responses'
    elif args.plan == 'animation-motion':
        result['animation_motion'] = animation_motion(client,i)
        assert result['animation_motion']['ok'], 'Animation/input trial incomplete; inspect retained evidence'
    elif args.plan == 'animation':
        from animation_capture_probe import capture_animation
        result['animation'] = capture_animation(client)
        assert result['animation']['ok'], 'No matching player/channel observations; inspect retained responses'
    elif args.plan == 'fast':
        result['fast'] = fast_demo(client, i)
        assert result['fast']['ok'], 'Fast demo readback or resume failed'
    elif args.plan == 'speed':
        result['speed'] = speed_test(client, i)
        assert result['speed']['ok'], 'Speed trial incomplete; inspect eligibility and readbacks'
    elif args.plan == 'stress':
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
