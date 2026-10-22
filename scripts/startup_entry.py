#!/usr/bin/env python3
"""Natively gated startup entry: reach gameplay through the game's own screen transitions.

Drop-in alternative to the private run23/navigate_startup.py (same positional
arguments and navigation-result.json). It sends only the existing menu
transitions the original navigator uses (Enter on the title, offline notice and
tutorial prompt; the map key on the startup map) and nothing during gameplay.
Unlike the OCR-only navigator, gameplay is accepted only when the recognized HUD
agrees with the startup-loaded host: commands ready, world step advancing and a
player body in a physics world. Host reads are read-only; no pause, write or
step. Every input and native sample is recorded, including which screen was
showing when the player body first appeared.

This skips menu interaction delay, not asset or world loading. Spawn location is
whatever the profile's startup map closes onto; no map or spawn selection.

Usage: startup_entry.py OUT_DIR [BUDGET_SECONDS] [--workspace W] [--port P]
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from snow_host_client import SnowHostClient, HostError

ENTER, MAP_KEY = 28, 50
# Existing transitions only; same keys as the original navigator.
TRANSITIONS = {'title': ENTER, 'offline_notice': ENTER, 'tutorial': ENTER, 'map': MAP_KEY}
RETRY_SECONDS = 5.0      # same screen still showing after an input
MAX_INPUTS_PER_STATE = 4
NATIVE_CONFIRMATIONS = 2  # consecutive native samples agreeing with the HUD


def classify(text, legacy):
    text = text.upper()
    if 'CHANGE SPORT' in text and 'BINOCULARS' in text:
        return 'gameplay'
    return legacy(text)[0]


def native_in_world(sample):
    return bool(sample and sample.get('ready') and sample.get('advancing') and sample.get('player_flags', 0) & 3 == 3)


class Policy:
    """Pure decision state: which existing transition to send, and when gameplay is proven."""

    def __init__(self, retry=RETRY_SECONDS, max_inputs=MAX_INPUTS_PER_STATE, confirmations=NATIVE_CONFIRMATIONS):
        self.retry, self.max_inputs, self.confirmations = retry, max_inputs, confirmations
        self.inputs = {}
        self.last_input = None  # (state, time)
        self.native_streak = 0
        self.first_in_world_state = None

    def step(self, state, native, now):
        """Return ('send', scan) | ('wait', reason) | ('entered', None) | ('abort', reason)."""
        if native_in_world(native):
            if self.first_in_world_state is None:
                self.first_in_world_state = state
        if state == 'gameplay':
            self.native_streak = self.native_streak + 1 if native_in_world(native) else 0
            if self.native_streak >= self.confirmations:
                return 'entered', None
            return 'wait', 'hud_without_native_confirmation'
        self.native_streak = 0
        scan = TRANSITIONS.get(state)
        if scan is None:
            return 'wait', 'unrecognized_screen'
        if self.last_input and self.last_input[0] == state and now - self.last_input[1] < self.retry:
            return 'wait', 'transition_pending'
        if self.inputs.get(state, 0) >= self.max_inputs:
            return 'abort', f'{state} did not advance after {self.max_inputs} inputs'
        self.inputs[state] = self.inputs.get(state, 0) + 1
        self.last_input = (state, now)
        return 'send', scan


class Game:
    """Private workspace helpers: window capture/OCR, verified-window input, host reads."""

    def __init__(self, workspace, out, port):
        tb = workspace / 'runtime/testbench'
        sys.path.insert(0, str(tb / 'run3'))
        from startup_state import classify as legacy
        self.legacy, self.out, self.port = legacy, out, port
        self.capture_tool = tb / 'run3/mac-game-capture'
        helper = [sys.executable, str(tb / 'wine_helper.py')]
        self.control = helper + [str(tb / 'run3/control/input-control.exe')]
        self.probe = helper + [str(tb / 'attachment/probe.exe')]
        self.last_step = None

    @staticmethod
    def _run(cmd, timeout):
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout)
        return r, [json.loads(x) for x in r.stdout.splitlines() if x.startswith('{')]

    def screen(self, i, timeout):
        r, rows = self._run([self.capture_tool, self.out / f'frame-{i:02}.png'], timeout)
        (self.out / f'capture-{i:02}.txt').write_text(r.stdout + r.stderr)
        text = ' '.join(rows[-1].get('recognized_text', [])) if rows else ''
        return text, classify(text, self.legacy)

    def native(self):
        """Read-only host sample, or an error before the command service answers.

        The host serves one client at a time, so each sample uses its own short
        connection and never blocks the startup probe or the later session probe.
        """
        try:
            with SnowHostClient(port=self.port, timeout=3) as client:
                return self._sample(client)
        except (OSError, HostError) as exc:
            return {'error': type(exc).__name__}

    def _sample(self, client):
        status = client.call('simulation.status')
        engine = status.get('engine') or {}
        step = engine.get('step')
        sample = {'ready': bool(status.get('ready')), 'step': step,
                  'advancing': step is not None and self.last_step is not None and step != self.last_step
                               and not engine.get('held')}
        self.last_step = step
        if not sample['ready']:
            return sample
        try:
            sample['player_flags'] = client.call('player.get').get('flags', 0)
        except HostError as exc:
            sample['player_error'] = (exc.response.get('result') or {}).get('error')
            if sample['player_error'] == 'no_player':
                try:  # in-process read-only acquisition, as the session probe does
                    client.call('player.bind')
                    sample['player_flags'] = client.call('player.get').get('flags', 0)
                except HostError as exc2:
                    sample['bind_error'] = (exc2.response.get('result') or {}).get('error')
        return sample

    def send(self, i, scan):
        _, procs = self._run(self.probe + ['processes'], 15)
        games = [x for x in procs if x.get('name', '').lower() == 'steep.exe']
        if len(games) != 1:
            return False, 'expected exactly one game process'
        pid = str(games[0]['pid'])
        r, rows = self._run(self.control + ['windows', '--pid', pid, '--image', 'steep.exe'], 15)
        (self.out / f'windows-{i:02}.jsonl').write_text(r.stdout)
        ident = next((x for x in rows if x.get('kind') == 'target_identity'), None)
        wins = [x for x in rows if x.get('kind') == 'window' and x.get('title') == 'Steep' and x.get('visible')]
        if not ident or len(wins) != 1:
            return False, 'game window identity not verified'
        r, _ = self._run(self.control + ['hold', '--pid', pid, '--image', 'steep.exe', '--hwnd', wins[0]['hwnd'],
                                         '--created', ident['creation_filetime'], '--mode', 'sendinput',
                                         '--scan', str(scan), '--duration-ms', '100', '--focus'], 15)
        (self.out / f'input-{i:02}.jsonl').write_text(r.stdout)
        return r.returncode == 0, None if r.returncode == 0 else f'input exit {r.returncode}'


def navigate(game, budget, clock=time.monotonic, sleep=time.sleep, policy=None, max_frames=200):
    policy = policy or Policy()
    start = clock(); deadline = start + budget
    result = {'gameplay_hud_observed': False, 'gameplay_native_verified': False, 'gameplay_inputs_sent': False,
              'inputs': [], 'screens': [], 'outcome': 'budget_exhausted'}
    for i in range(max_frames):
        remaining = deadline - clock()
        if remaining <= 0:
            break
        try:
            text, state = game.screen(i, min(30, remaining))
        except subprocess.TimeoutExpired:
            text, state = '', 'capture_timeout'
        native = game.native()
        t = round(clock() - start, 1)
        action, detail = policy.step(state, native, clock())
        row = {'frame': i, 't': t, 'state': state, 'native': native, 'action': action}
        result['screens'].append(row)
        print(json.dumps({**row, 'text': text[:120]}), flush=True)
        if state == 'gameplay':
            result['gameplay_hud_observed'] = True
        if action == 'entered':
            result['gameplay_native_verified'] = True
            result['outcome'] = 'entered'
            print('GAMEPLAY_HUD_OBSERVED', flush=True)
            break
        if action == 'abort':
            result['outcome'] = 'abort: ' + detail
            break
        if action == 'send':
            ok, why = game.send(i, detail)
            result['inputs'].append({'frame': i, 't': t, 'state': state, 'scan': detail, 'ok': ok, 'error': why})
            if not ok:
                result['outcome'] = 'input_failed: ' + why
                break
        sleep(1.0)
    result['first_player_in_world_screen'] = policy.first_in_world_state
    result['elapsed_seconds'] = round(clock() - start, 1)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('out', type=Path)
    p.add_argument('budget', type=int, nargs='?', default=150)
    p.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument('--port', type=int, default=47017)
    a = p.parse_args(argv)
    if not 30 <= a.budget <= 210:
        p.error('Navigation budget must be 30..210 seconds')
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    game = Game(a.workspace.resolve(), out, a.port)
    result = navigate(game, a.budget)
    (out / 'navigation-result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['gameplay_native_verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
