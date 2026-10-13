"""Designed serial job executor informed by scheduler dependency research.

These lifecycle strings are OUR states, not the original scheduler's numeric
codes. Claim exhaustion is not completion. A claim retains a Python callable
until execute returns; slot replacement, removal and reset require quiescence.
No original-process hook, thread suspension or native lifetime guarantee exists.

Handlers are {name: {version: nonempty_string, callback: callable}}. Version
tokens must describe caller-controlled implementation revisions; matching tokens
do not independently prove identical code, closures or external state. A callback
receives the caller's context and returns JSON data. Context side effects are not
rolled back on failure and must be checkpointed separately for replay.

snapshot() is inspectable at any stage. restore() accepts only snapshots with no
claimed/running jobs: Python call frames and retained callable identity cannot be
serialized. Replay also requires matching handler versions and caller context.
"""
import copy
import json

from .assets import canonical
from .trace import Trace

STAGES = ('pending', 'claimed', 'running', 'completed', 'failed')
EVIDENCE = 'designed_serial_dependency_executor'


def _name(value):
    if not isinstance(value, str) or not value:
        raise ValueError('job, handler and version identifiers must be nonempty strings')
    return value


class JobExecutor:
    """A deterministic declaration-order executor with explicit delayed claims.

    definitions: [{id, handler, depends_on?: [job IDs], handler_version?: token}].
    claim() does not run a callback. execute(id, context) runs exactly its claim.
    run_ready() repeatedly claims/executes ready jobs, bounded by max_jobs.
    A failure is terminal until reset and blocks dependents but not unrelated jobs.
    """
    def __init__(self, definitions, handlers, trace_capacity=4096):
        if not isinstance(handlers, dict):
            raise ValueError('handlers must be a versioned registry')
        self._handlers = {}
        for name, spec in handlers.items():
            _name(name)
            if not isinstance(spec, dict) or set(spec) != {'version', 'callback'}:
                raise ValueError('handler requires version and callback')
            _name(spec['version'])
            if not callable(spec['callback']):
                raise ValueError('handler callback must be callable')
            self._handlers[name] = dict(spec)
        if not isinstance(definitions, list) or len(definitions) > 100000:
            raise ValueError('job definitions must be a bounded list')
        self._definitions = []
        names = set()
        for raw in definitions:
            if not isinstance(raw, dict) or set(raw) - {'id', 'handler', 'depends_on', 'handler_version'}:
                raise ValueError('invalid job definition')
            name, handler = _name(raw.get('id')), _name(raw.get('handler'))
            if name in names or handler not in self._handlers:
                raise ValueError('duplicate job or missing handler')
            names.add(name)
            dependencies = raw.get('depends_on', [])
            if not isinstance(dependencies, list) or any(not isinstance(x, str) for x in dependencies) or len(set(dependencies)) != len(dependencies):
                raise ValueError('dependencies must be unique job names')
            version = raw.get('handler_version', self._handlers[handler]['version'])
            if version != self._handlers[handler]['version']:
                raise ValueError('handler version mismatch')
            self._definitions.append(dict(id=name, handler=handler, depends_on=list(dependencies), handler_version=version))
        self._by_id = {row['id']: row for row in self._definitions}
        for row in self._definitions:
            if any(name not in names for name in row['depends_on']):
                raise ValueError('missing dependency')
        # Kahn traversal avoids Python recursion limits for long caller graphs.
        remaining = {row['id']: set(row['depends_on']) for row in self._definitions}
        reverse = {name: [] for name in names}
        for name, deps in remaining.items():
            for dep in deps:
                reverse[dep].append(name)
        ready = [name for name, deps in remaining.items() if not deps]
        seen = 0
        while ready:
            name = ready.pop()
            seen += 1
            for child in reverse[name]:
                remaining[child].remove(name)
                if not remaining[child]:
                    ready.append(child)
        if seen != len(names):
            raise ValueError('dependency cycle')
        self._records = {name: self._fresh() for name in names}
        self._claimed = {}
        self.epoch = 0
        self.trace = Trace(trace_capacity)

    @staticmethod
    def _fresh():
        return dict(stage='pending', claimed_handler=None, result=None, error=None)

    def drained(self):
        """No retained/in-progress callbacks; does not mean all jobs succeeded."""
        return not self._claimed and not any(row['stage'] in ('claimed', 'running') for row in self._records.values())

    def ready(self):
        return [row['id'] for row in self._definitions
                if self._records[row['id']]['stage'] == 'pending'
                and all(self._records[dep]['stage'] == 'completed' for dep in row['depends_on'])]

    def claim(self, job_id=None):
        candidates = self.ready()
        if job_id is None:
            if not candidates:
                return None
            job_id = candidates[0]
        if job_id not in candidates:
            raise ValueError('job is not ready to claim')
        definition = self._by_id[job_id]
        binding = self._handlers[definition['handler']]
        self._claimed[job_id] = binding['callback']
        identity = dict(id=definition['handler'], version=binding['version'])
        self._records[job_id].update(stage='claimed', claimed_handler=identity)
        self.trace.emit('job_claimed', epoch=self.epoch, job=job_id, handler=identity)
        return job_id

    def execute(self, job_id, context=None):
        if job_id not in self._claimed or self._records[job_id]['stage'] != 'claimed':
            raise ValueError('job requires an outstanding claim')
        if any(row['stage'] == 'running' for row in self._records.values()):
            raise RuntimeError('nested execution is not supported by the serial executor')
        row = self._records[job_id]
        row['stage'] = 'running'
        self.trace.emit('job_running', epoch=self.epoch, job=job_id)
        try:
            result = self._claimed[job_id](context)
            # Roundtrip both checks finite JSON and detaches callback-owned data.
            result = json.loads(canonical(result))
        except BaseException as exc:
            row.update(stage='failed', error=dict(type=type(exc).__name__, message=str(exc)))
            self.trace.emit('job_failed', epoch=self.epoch, job=job_id, error=row['error'])
            raise
        else:
            row.update(stage='completed', result=result)
            self.trace.emit('job_completed', epoch=self.epoch, job=job_id)
            return copy.deepcopy(result)
        finally:
            del self._claimed[job_id]

    def run_ready(self, context=None, max_jobs=100000):
        if type(max_jobs) is not int or not 0 <= max_jobs <= 100000:
            raise ValueError('max_jobs must be in 0..100000')
        if any(row['stage'] == 'running' for row in self._records.values()):
            raise RuntimeError('nested execution is not supported by the serial executor')
        results = []
        for _ in range(max_jobs):
            name = self.claim()
            if name is None:
                break
            results.append(dict(job=name, result=self.execute(name, context)))
        return results

    def replace_handler(self, handler_id, callback, version):
        """Replace a binding only when ALL claims and running callbacks drain."""
        if not self.drained():
            raise RuntimeError('handler replacement requires a drained executor')
        _name(version)
        if handler_id not in self._handlers or not callable(callback):
            raise ValueError('unknown handler or noncallable replacement')
        if version == self._handlers[handler_id]['version']:
            raise ValueError('replacement requires a new version token')
        self._handlers[handler_id] = dict(callback=callback, version=version)
        for row in self._definitions:
            if row['handler'] == handler_id:
                row['handler_version'] = version
        self.trace.emit('job_handler_replaced', epoch=self.epoch, handler=handler_id, version=version)

    def remove_job(self, job_id):
        if not self.drained():
            raise RuntimeError('job removal requires a drained executor')
        if job_id not in self._by_id:
            raise ValueError('unknown job')
        if any(job_id in row['depends_on'] for row in self._definitions):
            raise ValueError('cannot remove a job with dependents')
        self._definitions = [row for row in self._definitions if row['id'] != job_id]
        del self._by_id[job_id]
        del self._records[job_id]
        self.trace.emit('job_removed', epoch=self.epoch, job=job_id)

    def reset(self):
        """Begin a new execution epoch only after retained callbacks drain."""
        if not self.drained():
            raise RuntimeError('reset requires a drained executor')
        self._records = {row['id']: self._fresh() for row in self._definitions}
        self.epoch += 1
        self.trace.emit('jobs_reset', epoch=self.epoch)

    def snapshot(self):
        return copy.deepcopy(dict(schema_version=1, evidence=EVIDENCE, epoch=self.epoch,
                                  definitions=self._definitions, jobs=self._records,
                                  trace=self.trace.snapshot(), drained=self.drained()))

    @classmethod
    def restore(cls, snapshot, handlers):
        """Restore quiescent JSON state using a caller-supplied versioned registry."""
        canonical(snapshot)
        snapshot = copy.deepcopy(snapshot)
        if not isinstance(snapshot, dict) or set(snapshot) != {'schema_version', 'evidence', 'epoch', 'definitions', 'jobs', 'trace', 'drained'}:
            raise ValueError('invalid executor snapshot schema')
        if snapshot['schema_version'] != 1 or snapshot['evidence'] != EVIDENCE or snapshot['drained'] is not True:
            raise ValueError('only drained executor snapshots can be restored')
        if type(snapshot['epoch']) is not int or snapshot['epoch'] < 0:
            raise ValueError('invalid execution epoch')
        executor = cls(snapshot['definitions'], handlers, snapshot['trace']['capacity'])
        records = snapshot['jobs']
        if not isinstance(records, dict) or set(records) != set(executor._records):
            raise ValueError('snapshot job set differs from definitions')
        for name, row in records.items():
            if not isinstance(row, dict) or set(row) != {'stage', 'claimed_handler', 'result', 'error'}:
                raise ValueError('invalid job record')
            stage = row['stage']
            if stage not in ('pending', 'completed', 'failed'):
                raise ValueError('claimed/running Python callback identity cannot be restored')
            if stage == 'pending' and row != executor._fresh():
                raise ValueError('pending job contains execution data')
            if stage != 'pending':
                identity = row['claimed_handler']
                if not isinstance(identity, dict) or set(identity) != {'id', 'version'} or identity['id'] != executor._by_id[name]['handler']:
                    raise ValueError('invalid captured handler identity')
                _name(identity['version'])
                if any(records[dep]['stage'] != 'completed' for dep in executor._by_id[name]['depends_on']):
                    raise ValueError('executed job has incomplete dependencies')
            if stage == 'completed' and row['error'] is not None:
                raise ValueError('completed job has an error')
            if stage == 'failed' and (row['result'] is not None or not isinstance(row['error'], dict) or set(row['error']) != {'type', 'message'}):
                raise ValueError('failed job requires error metadata')
        executor._records = records
        executor.epoch = snapshot['epoch']
        executor.trace = Trace.restore(snapshot['trace'])
        return executor
