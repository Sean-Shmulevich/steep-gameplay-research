#!/usr/bin/env python3
"""Natively gated startup entry: reach gameplay through the game's own screen transitions.

Drop-in alternative to the private run23/navigate_startup.py (same positional
arguments and navigation-result.json). It sends only the existing menu
transitions the original navigator uses (Enter on the title, offline notice and
tutorial prompt; the map key on the startup map) and nothing during gameplay.
Unlike the OCR-only navigator, gameplay is accepted only when the recognized HUD
agrees with the startup-loaded host: commands ready, world step advancing and the
player acquired with valid flags. An idle freshly spawned rider is not yet in a
physics world (IN_WORLD sets after the first movement input), so IN_WORLD is
recorded but not required. Host reads are read-only; no pause, write or step.
Every input and native sample is recorded, including which screen was showing
when the player was first acquired.

This skips menu interaction delay, not asset or world loading. Spawn location is
whatever the profile's startup map closes onto; no map or spawn selection.
The idle player's position at entry is recorded as spawn_position; --expect-spawn
makes a different spawn a failure. --intro-key enter|escape is an experiment: bounded presses on visible pre-title
screens, to measure whether the timed videos/notices can be skipped.

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

ENTER, MAP_KEY, ESCAPE = 28, 50, 1
INTRO_KEYS = {'enter': ENTER, 'escape': ESCAPE}
# Existing transitions only; same keys as the original navigator.
TRANSITIONS = {'title': ENTER, 'offline_notice': ENTER, 'tutorial': ENTER, 'map': MAP_KEY}
RETRY_SECONDS = 5.0      # same screen still showing after an input
MAX_INPUTS_PER_STATE = 4
NATIVE_CONFIRMATIONS = 2  # consecutive native samples agreeing with the HUD
# Opt-in experiment: Enter (the title's own key) while pre-title videos/notices show.
INTRO_INTERVAL_SECONDS = 4.0
MAX_INTRO_INPUTS = 6


def classify(text, legacy):
    text = text.upper()
    if 'CHANGE SPORT' in text and 'BINOCULARS' in text:
        return 'gameplay'
    return legacy(text)[0]


def native_player_ready(sample):
    """Host ready, world stepping and player acquired with valid flags (IN_WORLD not required)."""
    return bool(sample and sample.get('ready') and sample.get('advancing') and sample.get('player_flags', 0) & 1)


class Policy:
    """Pure decision state: which existing transition to send, and when gameplay is proven."""

    def __init__(self, retry=RETRY_SECONDS, max_inputs=MAX_INPUTS_PER_STATE, confirmations=NATIVE_CONFIRMATIONS,
                 intro_key=None, intro_interval=INTRO_INTERVAL_SECONDS, max_intro=MAX_INTRO_INPUTS):
        self.retry, self.max_inputs, self.confirmations = retry, max_inputs, confirmations
        self.intro_key, self.intro_interval, self.max_intro = intro_key, intro_interval, max_intro
        self.intro_inputs = []
        self.inputs = {}
        self.last_input = None  # (state, time)
        self.native_streak = 0
        self.first_player_state = None
        self.first_in_world_state = None

    def step(self, state, native, now):
        """Return ('send', scan) | ('wait', reason) | ('entered', None) | ('abort', reason)."""
        if native_player_ready(native) and self.first_player_state is None:
            self.first_player_state = state
        if native_player_ready(native) and native['player_flags'] & 2 and self.first_in_world_state is None:
            self.first_in_world_state = state
        if state == 'gameplay':
            self.native_streak = self.native_streak + 1 if native_player_ready(native) else 0
            if self.native_streak >= self.confirmations:
                return 'entered', None
            return 'wait', 'hud_without_native_confirmation'
        self.native_streak = 0
        if state == 'intro':
            # Only before any menu transition, bounded, and never a failure reason.
            if (self.intro_key is None or self.inputs or len(self.intro_inputs) >= self.max_intro
                    or (self.intro_inputs and now - self.intro_inputs[-1] < self.intro_interval)):
                return 'wait', 'intro'
            self.intro_inputs.append(now)
            return 'send', self.intro_key
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

    def native(self, want_player=True):
        """Read-only host sample, or an error before the command service answers.

        The host serves one client at a time, so each sample uses its own short
        connection and never blocks the startup probe or the later session probe.
        """
        try:
            with SnowHostClient(port=self.port, timeout=3) as client:
                return self._sample(client, want_player)
        except (OSError, HostError) as exc:
            return {'error': type(exc).__name__}

    def _sample(self, client, want_player):
        status = client.call('simulation.status')
        engine = status.get('engine') or {}
        step = engine.get('step')
        sample = {'ready': bool(status.get('ready')), 'step': step,
                  'advancing': step is not None and self.last_step is not None and step != self.last_step
                               and not engine.get('held')}
        self.last_step = step
        if not sample['ready'] or not want_player:
            return sample
        try:
            player = client.call('player.get')
            sample['player_flags'] = player.get('flags', 0)
            sample['position'] = player.get('position')
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


def spawn_matches(position, expected, tolerance):
    return bool(position) and len(position) == 3 and all(abs(a - b) <= tolerance for a, b in zip(position, expected))


def navigate(game, budget, clock=time.monotonic, sleep=time.sleep, policy=None, max_frames=200,
             expect_spawn=None, spawn_tolerance=0.01, stop_at=None):
    policy = policy or Policy()
    start = clock(); deadline = start + budget
    result = {'gameplay_hud_observed': False, 'gameplay_native_verified': False, 'gameplay_inputs_sent': False,
              'inputs': [], 'screens': [], 'outcome': 'budget_exhausted', 'intro_key': policy.intro_key,
              'title_first_t': None}
    for i in range(max_frames):
        remaining = deadline - clock()
        if remaining <= 0:
            break
        try:
            text, state = game.screen(i, min(30, remaining))
        except subprocess.TimeoutExpired:
            text, state = '', 'capture_timeout'
        if state == 'title' and result['title_first_t'] is None:
            result['title_first_t'] = round(clock() - start, 1)
        if 'LOADING' in text.upper():
            result['loading_seen'] = True  # an intro key may skip the title straight into loading
        if (state == 'unknown' and text.strip() and result['title_first_t'] is None and not policy.inputs
                and not result.get('loading_seen')):
            state = 'intro'  # a visible pre-title screen (videos, notices)
        # The player cannot exist before the title; skip refused reads until a menu transition.
        native = game.native(want_player=bool(policy.inputs))
        t = round(clock() - start, 1)
        if stop_at is not None and state == stop_at:
            action, detail = 'stopped', None  # leave this screen to the caller, no input
        else:
            action, detail = policy.step(state, native, clock())
        row = {'frame': i, 't': t, 'state': state, 'native': native, 'action': action}
        result['screens'].append(row)
        print(json.dumps({**row, 'text': text[:120]}), flush=True)
        if state == 'gameplay':
            result['gameplay_hud_observed'] = True
        if action == 'entered':
            result['gameplay_native_verified'] = True
            result['outcome'] = 'entered'
            result['spawn_position'] = native.get('position')
            if expect_spawn is not None:
                result['spawn_matches_expected'] = spawn_matches(native.get('position'), expect_spawn, spawn_tolerance)
                if not result['spawn_matches_expected']:
                    result['outcome'] = 'entered_unexpected_spawn'
            print('GAMEPLAY_HUD_OBSERVED', flush=True)
            break
        if action == 'stopped':
            result['outcome'] = 'stopped_at_' + state
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
    result['first_player_acquired_screen'] = policy.first_player_state
    result['first_player_in_world_screen'] = policy.first_in_world_state
    result['elapsed_seconds'] = round(clock() - start, 1)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('out', type=Path)
    p.add_argument('budget', type=int, nargs='?', default=150)
    p.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument('--port', type=int, default=47017)
    p.add_argument('--expect-spawn', help='x,y,z the idle player must occupy at entry (fails otherwise)')
    p.add_argument('--spawn-tolerance', type=float, default=0.01)
    p.add_argument('--stop-at', choices=['map'], help='Stop without input when this screen is recognized')
    p.add_argument('--intro-key', choices=sorted(INTRO_KEYS), help='Experiment: press this key during pre-title videos/notices')
    a = p.parse_args(argv)
    if not 30 <= a.budget <= 210:
        p.error('Navigation budget must be 30..210 seconds')
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    game = Game(a.workspace.resolve(), out, a.port)
    expect = None
    if a.expect_spawn:
        expect = [float(v) for v in a.expect_spawn.split(',')]
        if len(expect) != 3:
            p.error('--expect-spawn needs x,y,z')
    result = navigate(game, a.budget, policy=Policy(intro_key=INTRO_KEYS.get(a.intro_key)),
                      expect_spawn=expect, spawn_tolerance=a.spawn_tolerance, stop_at=a.stop_at)
    (out / 'navigation-result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['outcome'] in ('entered', 'stopped_at_' + str(a.stop_at)) else 2


if __name__ == '__main__':
    raise SystemExit(main())
