#!/usr/bin/env python3
"""Run the bounded late-load experiment in an already configured research workspace.

--experiment probe (default) loads the attachment-only diagnostic DLL.
--experiment host loads the Snow mod host and drives pause/step/resume through
its command channel. The host build needs the private game adapter in the workspace.
--load-at startup uses the native launcher to load the host during process startup;
gameplay navigation and validation use that same preloaded instance.

Only source is published. Highball, the owned game, and earlier private research
helpers must already exist in --workspace. No game DLL is replaced.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import uuid

REPO = Path(__file__).resolve().parents[1]
ORIGINAL_XINPUT_SHA256 = '756cad002e1553cfa1a91ebe8c1b9380ffabe0b4b1916c4a4db802396ddfbef8'
REQUIRED = [
    'steep.exe', 'XINPUT1_3.dll', 'runtime/highball-cli', 'runtime/bounded-test.py',
    'runtime/testbench/run23/navigate_startup.py', 'runtime/testbench/run13/identify_game.py',
    'runtime/testbench/wine_helper.py', 'runtime/testbench/run36/observe.py',
    'runtime/testbench/run36/probe.exe', 'runtime/testbench/attachment/probe.exe',
    'runtime/testbench/run3/mac-game-capture', 'runtime/testbench/run3/control/input-control.exe',
    'runtime/highball/bottles/snow-research/bottle.json',
    'analysis/engine-event-reset-wait/private/modewrite/NativeCall.exe',
    'analysis/engine-event-reset-wait/private/modewrite/ModeWrite.exe',
]
HOST_ADAPTER = 'analysis/mod-host/private/steep_adapter.c'
HOST_RESTORE = 'analysis/mod-host/private/restore_mode.py'


def preflight(root, experiment='probe'):
    required = REQUIRED + ([HOST_ADAPTER, HOST_RESTORE] if experiment == 'host' else [])
    missing = [str(p) for p in required if not (root / p).is_file()]
    cc = shutil.which('x86_64-w64-mingw32-gcc')
    if not cc:
        missing.append('x86_64-w64-mingw32-gcc on PATH')
    if missing:
        raise RuntimeError('Missing prerequisites:\n  ' + '\n  '.join(missing))
    if hashlib.sha256((root / 'XINPUT1_3.dll').read_bytes()).hexdigest() != ORIGINAL_XINPUT_SHA256:
        raise RuntimeError('Original XINPUT1_3.dll hash differs; refusing to launch or replace it.')
    if not all(flag in (root / 'runtime/bounded-test.py').read_text() for flag in ['--native-xinput', '--result-dir']):
        raise RuntimeError('Local bounded launcher needs --native-xinput and --result-dir support.')
    check_intel_runtime()
    return cc


def check_intel_runtime():
    """Check execution, not Rosetta package presence, for this Intel Wine setup."""
    if sys.platform != 'darwin' or platform.machine() != 'arm64':
        return
    try:
        probe = subprocess.run(['/usr/bin/arch', '-x86_64', '/usr/bin/true'],
                               capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('Could not verify Intel execution; no game launched: '+str(exc)) from exc
    if probe.returncode:
        raise RuntimeError('Intel execution is unavailable on this Mac. The configured Wine engine '
                           'requires working Rosetta. Repair/install Rosetta before retrying; '
                           'no game launched. Probe: '+probe.stderr.strip()[:300])


def stop_child(child, interrupt=False, timeout=20):
    if child is None or child.poll() is not None:
        return
    child.send_signal(signal.SIGINT if interrupt else signal.SIGTERM)
    try:
        child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=5)


def wait_stage(child, watchdog, timeout):
    end = time.monotonic() + timeout
    while child.poll() is None:
        if watchdog.poll() is not None:
            raise RuntimeError('Game watchdog stopped during this stage; inspect launch.log.')
        if time.monotonic() >= end:
            raise RuntimeError('Stage deadline reached.')
        time.sleep(.25)
    if child.returncode:
        raise RuntimeError(f'Stage failed with exit {child.returncode}; inspect its session log.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=REPO.parent)
    parser.add_argument('--check', action='store_true', help='Check local prerequisites without launching Wine or the game')
    parser.add_argument('--experiment', choices=['probe', 'host'], default='probe')
    parser.add_argument('--load-at', choices=['gameplay', 'startup'], default='gameplay', help='Load host automatically during process startup or after gameplay is verified')
    parser.add_argument('--steps', type=int, default=10, help='World steps for --experiment host (1..60)')
    parser.add_argument('--plan', choices=['demo', 'acceptance', 'stress', 'speed', 'fast', 'animation', 'animation-motion', 'cached-parent', 'work-packet', 'update-capture'], default='demo', help='Host experiment; cached-parent performs read-only animation observations after binding')
    args = parser.parse_args()
    if not 1 <= args.steps <= 60:
        raise RuntimeError('--steps must be 1..60')
    if args.load_at == 'startup' and args.experiment != 'host':
        raise RuntimeError('--load-at startup requires --experiment host')
    root = args.workspace.expanduser().resolve()
    cc = preflight(root, args.experiment)
    if args.load_at == 'startup' and '--launcher' not in (root/'runtime/bounded-test.py').read_text():
        raise RuntimeError('Local bounded launcher needs --launcher support')
    if args.check:
        print(f'Prerequisites OK: {root}\nOriginal DLL verified. No game launched.')
        return 0
    session_root = root / 'runtime/mod-loader/sessions'
    session_root.mkdir(parents=True, exist_ok=True)
    lock = (session_root / '.experiment.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError('Another late-load experiment holds the workspace lock.')
    cli = root / 'runtime/highball-cli'
    active = subprocess.run([str(cli), 'bottle', 'ps', 'snow-research'], capture_output=True, text=True, timeout=10, check=True)
    if 'no processes' not in active.stdout:
        raise RuntimeError('Research bottle is already active. Close that session before running this command.')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = session_root / (stamp + '-' + uuid.uuid4().hex[:8])
    out.mkdir()
    build = out / 'build'
    build.mkdir()
    (build / 'plugins').mkdir()
    result = {'ok': False, 'session': str(out), 'experiment': args.experiment, 'load_at': args.load_at, 'original_dll_replaced': False}
    children = []; handles = []; watchdog = None

    def start(argv, name):
        log = (out / (name + '.log')).open('w')
        handles.append(log)
        child = subprocess.Popen(argv, cwd=root, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        children.append(child)
        return child

    try:
        print(f'Session: {out}', flush=True)
        src = REPO / 'native/mod_loader'
        host = REPO / 'native/snow_host'
        if args.experiment == 'host':
            print('Building the mod host and its loader...', flush=True)
            commands = [
                [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2', '-shared', '-I', str(host), '-o', str(build/'snow_host.dll'), str(host/'snow_host.c'), str(host/'snow_plugins.c'), str(root/HOST_ADAPTER), '-lws2_32'],
                [cc, '-Wall', '-Wextra', '-Werror', '-O2', '-municode', '-o', str(build/'host_loader.exe'), str(host/'host_loader.c')],
                # Example plugin, loaded by the host from build/plugins.
                [cc, '-Wall', '-Wextra', '-Werror', '-O2', '-shared', '-I', str(host), '-o', str(build/'plugins/step_logger.dll'), str(host/'examples/step_logger.c')],
            ]
        else:
            print('Building the attachment-only DLL and guarded loader...', flush=True)
            commands = [
                [cc, '-Wall', '-Wextra', '-Werror', '-O2', '-shared', '-nostdlib', '-Wl,--entry,LoaderEntry', '-o', str(build/'late_probe.dll'), str(src/'late_probe.c'), '-lkernel32'],
                [cc, '-Wall', '-Wextra', '-Werror', '-O2', '-municode', '-o', str(build/'load_probe.exe'), str(src/'load_probe.c')],
            ]
        if args.experiment == 'host' and args.plan == 'update-capture':
            commands.append([cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2', '-shared', '-I', str(host),
                '-o', str(build/'plugins/update_capture.dll'),
                *[str(host/name) for name in ('examples/update_capture.c','steep_adapter.c','snow_update_probe.c','snow_update_trace.c','snow_update_snapshot.c')]])
            (build/'plugins/update_capture.ini').write_text('[capture]\nenabled=1\nseconds=2\n')
        if args.load_at == 'startup':
            commands.append([cc, '-Wall', '-Wextra', '-Werror', '-O2', '-municode', '-o', str(build/'startup_launcher.exe'), str(host/'startup_launcher.c'), '-luser32'])
        with (out / 'build.log').open('w') as log:
            for command in commands:
                subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        print('Launching original game (five-minute maximum, memory watchdog active)...', flush=True)
        launch_args = [sys.executable, str(root/'runtime/bounded-test.py'), '--renderer', 'd3dmetal', '--seconds', '480' if args.plan == 'stress' else '300', '--direct', '--disable-d3d10', '--native-xinput', '--result-dir', str(out/'watchdog')]
        if args.load_at == 'startup':
            win = lambda p: 'Z:' + str(p).replace('/', '\\')
            launch_args += ['--launcher', str(build/'startup_launcher.exe'), '--launcher-arg', win(root/'steep.exe'), '--launcher-arg', win(build/'snow_host.dll'), '--launcher-arg', '47017']
        game_deadline = time.time() + (480 if args.plan == 'stress' else 300)
        watchdog = start(launch_args, 'launch')
        if args.load_at == 'startup':
            print('Loading the host automatically during startup...', flush=True)
            early = start([sys.executable, str(REPO/'scripts/startup_host_probe.py'), '--workspace', str(root), '--build', str(build), '--output', str(out/'startup')], 'startup')
        print('Advancing recognized startup screens; please leave controls alone.', flush=True)
        nav = start([sys.executable, str(root/'runtime/testbench/run23/navigate_startup.py'), str(out/'navigation'), '200'], 'navigation')
        if args.load_at == 'startup':
            wait_stage(early, watchdog, 90)
            result['startup'] = json.loads((out/'startup/result.json').read_text())
            if not result['startup']['ok']:
                raise RuntimeError('Startup host loading was not verified')
        wait_stage(nav, watchdog, 220)
        nav_result = json.loads((out/'navigation/navigation-result.json').read_text())
        if not nav_result.get('gameplay_hud_observed'):
            raise RuntimeError('Gameplay HUD was not verified; no pause or load attempted.')
        if args.experiment == 'host':
            print(f'Gameplay verified. Running host plan {args.plan}, then 20 seconds of observation...', flush=True)
            probe = start([sys.executable, str(REPO/'scripts/host_session_probe.py'), '--workspace', str(root), '--build', str(build), '--output', str(out/'probe'), '--steps', str(args.steps), '--plan', args.plan, '--game-deadline', str(game_deadline)] + (['--preloaded'] if args.load_at == 'startup' else []), 'probe')
        else:
            print('Gameplay verified. Pausing, loading, resuming, and observing for 20 seconds...', flush=True)
            probe = start([sys.executable, str(REPO/'scripts/late_load_probe.py'), '--workspace', str(root), '--build', str(build), '--output', str(out/'probe')], 'probe')
        wait_stage(probe, watchdog, 300 if args.plan == 'stress' else 160 if args.plan in ('work-packet', 'acceptance') else 90 + (3 * args.steps if args.experiment == 'host' else 0))
        result['probe'] = json.loads((out/'probe/result.json').read_text())
        if not result['probe'].get('ok'):
            raise RuntimeError('Probe did not pass all checks; see probe/result.json.')
        result['ok'] = True
    except KeyboardInterrupt:
        result['error'] = 'Interrupted by user; closing the owned experiment.'
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        print('Closing test session and restoring temporary launch settings...', flush=True)
        cleanup_errors = []
        for child in reversed(children):
            if child is not watchdog:
                try:
                    stop_child(child, interrupt=True)
                except Exception as exc:
                    cleanup_errors.append(str(exc))
        if watchdog is not None:
            try:
                stop_child(watchdog, interrupt=True, timeout=25)
            except Exception as exc:
                cleanup_errors.append(str(exc))
            # A recorded watchdog loop proves this launcher started its own session.
            # If its normal finally block failed, close that bottle and use its backups.
            backups = out/'watchdog'
            paths_file = backups/'restore-paths.json'
            launch_text = (out/'launch.log').read_text(errors='replace')
            if paths_file.exists() and not (backups/'result.json').exists() and '"elapsed":' in launch_text:
                try:
                    subprocess.run([str(cli), 'bottle', 'kill', 'snow-research'], check=True, capture_output=True, timeout=15)
                    paths = json.loads(paths_file.read_text())
                    for key, filename in [('config', 'bottle-before.json'), ('settings', 'settings-before.ini')]:
                        target = Path(paths[key]).resolve()
                        if not target.is_relative_to(root/'runtime/highball/bottles/snow-research'):
                            raise RuntimeError('Invalid restoration destination')
                        target.write_bytes((backups/filename).read_bytes())
                    result['fallback_cleanup'] = True
                except Exception as exc:
                    cleanup_errors.append('Fallback cleanup: '+str(exc))
            if paths_file.exists():
                paths = json.loads(paths_file.read_text())
                result['settings_restored'] = all(Path(paths[key]).read_bytes() == (backups/filename).read_bytes() for key, filename in [('config', 'bottle-before.json'), ('settings', 'settings-before.ini')])
                if not result['settings_restored']:
                    cleanup_errors.append('Launch settings do not match their pre-launch backups')
            if (backups/'result.json').exists() or result.get('fallback_cleanup'):
                try:
                    status = subprocess.run([str(cli), 'bottle', 'ps', 'snow-research'], capture_output=True, text=True, timeout=10, check=True)
                    result['bottle_stopped'] = 'no processes' in status.stdout
                    if not result['bottle_stopped']:
                        cleanup_errors.append('Research bottle still has processes')
                except Exception as exc:
                    cleanup_errors.append(str(exc))
        if cleanup_errors:
            result['cleanup_errors'] = cleanup_errors
            result['ok'] = False
        for log in handles:
            log.close()
        result['original_dll_verified'] = hashlib.sha256((root/'XINPUT1_3.dll').read_bytes()).hexdigest() == ORIGINAL_XINPUT_SHA256
        if not result['original_dll_verified']:
            result['ok'] = False
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(('PASS' if result['ok'] else 'FAILED') + f': {out / "result.json"}', flush=True)
        if result.get('error'):
            print(result['error'], file=sys.stderr)
        lock.close()
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
