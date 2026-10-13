"""Exclusive pause/step control of OUR Engine, never the original game.

All submissions and mutations through one controller share a serial lock. A
successful pause returns only after prior work has returned and the submission
gate is closed. Merely observing drained=True does not close that gate. A pause
request waiting for the lock has not yet excluded contenders; ordering is lock
acquisition order, not wall-clock request order.

The controller exclusively owns its Engine. Calling that Engine directly, or
sharing it with another controller, bypasses this guarantee and is unsupported.
Callback side effects outside the owned Engine cannot be checkpointed/rolled
back. Pause tokens are control capabilities, not a security boundary or proof of
native process quiescence. Their random controller identity never enters physics
state, hashes, replay commands or checkpointed numerical state.
"""
import copy
from contextlib import contextmanager
from dataclasses import dataclass
import threading
import uuid

from .assets import canonical
from .runtime import Engine


@dataclass(frozen=True)
class PauseToken:
    controller_id: str
    generation: int
    pause_serial: int


class SchedulerController:
    """Public API: submit_frame, pause, step_once, step_frame_once, resume,
    reset, restore, snapshot, checkpoint and export_replay. All calls serialize;
    callbacks must not reenter.

    submit_frame(frame_dt, actions=None) and step_once(token, actions=None)
    return read-only-copy snapshots. pause/reset/restore return a PauseToken.
    resume(token) returns a snapshot. step_once retains the current token;
    resume, reset, restore or execution failure invalidates it. Repeated pause
    while already paused returns the same token. A later pause uses a new serial.
    """
    def __init__(self, scenario=None, *, engine=None):
        if engine is not None and scenario is not None:
            raise ValueError('supply either scenario or an exclusively owned Engine')
        if engine is not None and not isinstance(engine, Engine):
            raise ValueError('engine must be an Engine')
        self._engine = Engine(scenario) if engine is None else engine
        self._lock = threading.Lock()
        self._owner = None
        self._identity = uuid.uuid4().hex
        self._generation = 0
        self._pause_serial = 1 if self._engine.state['paused'] else 0
        self._paused = bool(self._engine.state['paused'])
        self._active = False
        self._incidents = []

    @contextmanager
    def _serial(self):
        owner = threading.get_ident()
        if self._owner == owner:
            raise RuntimeError('scheduler controller does not allow callback reentry')
        with self._lock:
            self._owner = owner
            try:
                yield
            finally:
                self._owner = None

    def _token(self):
        return PauseToken(self._identity, self._generation, self._pause_serial)

    def _require_token(self, token):
        if not self._paused or not isinstance(token, PauseToken) or token != self._token():
            raise ValueError('a current paused-generation token is required')

    def _snapshot(self):
        return dict(state=self._engine.snapshot(), trace=self._engine.trace.snapshot(),
                    control=dict(paused=self._paused, submissions_excluded=self._paused,
                                 drained=not self._active, generation=self._generation,
                                 pause_serial=self._pause_serial,
                                 scope='owned Engine serial exclusion; not native game control'),
                    incidents=copy.deepcopy(self._incidents))

    def snapshot(self):
        """Read a copy without advancing simulation, input, scheduler or replay."""
        with self._serial():
            return self._snapshot()

    def checkpoint(self):
        """Complete owned Engine checkpoint plus replay/recovery bookkeeping.

        Engine.checkpoint alone omits its command segment, last-good recovery
        state and incident list. Preserve them here; resources/world are rebuilt
        from the embedded scenario by Engine.restore. No live token is serialized.
        """
        with self._serial():
            auxiliary = {name: copy.deepcopy(getattr(self._engine, name))
                         for name in ('commands', 'replay_base', 'last_good', 'incidents')}
            result = dict(schema_version=1, engine=self._engine.checkpoint(),
                          engine_aux=auxiliary, paused=self._paused,
                          incidents=copy.deepcopy(self._incidents))
            canonical(result)
            return result

    def export_replay(self):
        """Read-only command recording for this owned Engine's replay API."""
        from .replay import record
        with self._serial():
            return record(self._engine)

    def pause(self):
        with self._serial():
            if not self._paused:
                self._engine.pause(True)
                self._paused = True
                self._pause_serial += 1
            return self._token()

    def resume(self, token):
        with self._serial():
            self._require_token(token)
            self._engine.pause(False)
            self._paused = False
            self._generation += 1
            return self._snapshot()

    def _execute(self, operation, actions, frame_dt=None):
        # A failed frame must also undo a newly supplied input and its replay log.
        # Numerical Engine.advance has its own rollback, but controller ownership
        # requires a wider transaction including commands, events and trace.
        before = copy.deepcopy(self._engine.__dict__)
        self._active = True
        try:
            if actions is not None:
                self._engine.set_input(actions)
            if operation in ('step_once', 'step_frame_once'):
                self._engine.pause(False)
                if operation == 'step_once':
                    self._engine.step(1)
                else:
                    self._engine.advance(frame_dt)
                self._engine.pause(True)
            else:
                self._engine.advance(frame_dt)
        except BaseException as exc:
            self._engine.__dict__.clear()
            self._engine.__dict__.update(before)
            self._engine.pause(True)
            self._paused = True
            self._generation += 1
            self._pause_serial += 1
            self._incidents.append(dict(operation=operation, tick=self._engine.state['tick'],
                                        error=type(exc).__name__, message=str(exc)[:2048]))
            self._incidents = self._incidents[-100:]
            raise
        finally:
            self._active = False
        return self._snapshot()

    def submit_frame(self, frame_dt, actions=None):
        """Submit one frame only while the gate is open; never silently queue it."""
        with self._serial():
            if self._paused:
                raise RuntimeError('frame submission excluded while paused')
            return self._execute('submit_frame', actions, frame_dt)

    def step_once(self, token, actions=None):
        """Execute one configured fixed developer tick while excluding submissions.

        Uses Engine.step(1), not its frame subdivision planner. The temporary
        unpause/step/re-pause commands remain inside the serial lock and replay log.
        This does not bypass the configured Engine.step timestep-domain checks.
        """
        with self._serial():
            self._require_token(token)
            return self._execute('step_once', actions)

    def step_frame_once(self, token, frame_dt, actions=None):
        """Plan and execute one outer frame, then remain paused.

        Unlike step_once, this uses Engine.advance and the configured scheduler,
        including smoothing history, retained time and zero/multiple substeps.
        It is an owned reconstruction frame, not a native game stepping hook.
        """
        with self._serial():
            self._require_token(token)
            return self._execute('step_frame_once', actions, frame_dt)

    def reset(self, scenario=None):
        """Atomically replace the Engine with a validated scenario; remain paused."""
        with self._serial():
            candidate = Engine(copy.deepcopy(self._engine.scenario if scenario is None else scenario))
            candidate.pause(True)
            self._engine = candidate
            self._paused = True
            self._generation += 1
            self._pause_serial += 1
            self._incidents = []
            return self._token()

    def restore(self, checkpoint):
        """Restore owned state transactionally and issue a fresh paused token.

        Restoring a running checkpoint deliberately adds a pause command. Epochs
        are never restored: an old token cannot become valid through rollback.
        """
        with self._serial():
            checkpoint = copy.deepcopy(checkpoint)
            canonical(checkpoint)
            if not isinstance(checkpoint, dict) or set(checkpoint) != {'schema_version', 'engine', 'engine_aux', 'paused', 'incidents'}:
                raise ValueError('invalid controller checkpoint schema')
            if checkpoint['schema_version'] != 1 or type(checkpoint['paused']) is not bool:
                raise ValueError('invalid controller checkpoint version/pause')
            auxiliary = checkpoint['engine_aux']
            if not isinstance(auxiliary, dict) or set(auxiliary) != {'commands', 'replay_base', 'last_good', 'incidents'}:
                raise ValueError('invalid engine auxiliary checkpoint')
            if not isinstance(auxiliary['commands'], list) or not isinstance(auxiliary['incidents'], list):
                raise ValueError('invalid engine command/incident records')
            if not isinstance(checkpoint['incidents'], list) or len(checkpoint['incidents']) > 100:
                raise ValueError('invalid controller incidents')
            candidate = Engine()
            candidate.restore(checkpoint['engine'])
            if candidate.state['paused'] != checkpoint['paused']:
                raise ValueError('engine and controller paused states differ')
            # Validate recovery state through the same Engine checkpoint contract.
            recovery = copy.deepcopy(checkpoint['engine'])
            recovery['state'] = auxiliary['last_good']
            Engine().restore(recovery)
            if auxiliary['replay_base'] is not None:
                Engine().restore(auxiliary['replay_base'])
            for name, value in auxiliary.items():
                setattr(candidate, name, value)
            if not candidate.state['paused']:
                candidate.pause(True)
            self._engine = candidate
            self._paused = True
            self._generation += 1
            self._pause_serial += 1
            self._incidents = checkpoint['incidents']
            return self._token()
