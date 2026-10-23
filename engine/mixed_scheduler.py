"""Serial mixed scheduler reference with explicit native-derived job kinds.

See docs/reconstruction/MIXED_SCHEDULER_IMPLEMENTATION.md. Request/hold rules,
immediate normal/alternate propagation, callback reservation and dispatch return
accounting follow inspected paths. Queue choice, versioned Python handlers,
immutable topology, fail-stop errors and bounds are adapter policy. No native
threads, priorities, TLS, exception unwinding or safe process hooks are claimed.

Body handler: callback(context, receiver), with receiver=None for callback jobs.
Predicate handler: callback(context)->bool. Registry entries are
{name:{version:nonempty_string,callback:callable}}. Version labels are caller
assertions, not independent hashes of Python closure state. Callbacks may submit
another root before returning, as EndFrame does; direct topology edits are absent.
"""
import copy
from contextlib import contextmanager
from dataclasses import dataclass
import json
import uuid

from .assets import canonical
from .trace import Trace
from . import request_state as requests
from . import queue_policy as selection
from . import queue_producers as producers


@dataclass(frozen=True)
class DispatchToken:
    scheduler_id: str
    dispatch: int


@dataclass(frozen=True)
class RangeToken:
    scheduler_id: str
    dispatch: int
    sequence: int
    start: int
    count: int


class MixedScheduler:
    def __init__(self, definitions, handlers=None, trace_capacity=4096, max_transitions=10000, queue_policy=None):
        if type(max_transitions) is not int or not 1 <= max_transitions <= 100000:
            raise ValueError('max_transitions must be in 1..100000')
        if not isinstance(definitions, list) or len(definitions) > 128:
            raise ValueError('definitions must contain at most128 jobs')
        canonical(definitions)
        self._handlers = {}
        if handlers is not None and not isinstance(handlers, dict):
            raise ValueError('handlers must be a versioned registry')
        for name, binding in (handlers or {}).items():
            if not isinstance(name, str) or not name or not isinstance(binding, dict) or set(binding) != {'version', 'callback'}:
                raise ValueError('invalid handler binding')
            if not isinstance(binding['version'], str) or not binding['version'] or not callable(binding['callback']):
                raise ValueError('handler needs a version and callable')
            self._handlers[name] = dict(binding)
        allowed = {'id', 'kind', 'successors', 'credit_recipients', 'secondary', 'secondary_credits',
                   'handler', 'predicate', 'condition', 'receivers', 'chunk_size', 'tail_threshold',
                   'max_concurrency', 'credit_gate', 'credits', 'front_insert', 'early_exit_enabled'}
        self._definitions, self._jobs, self._lists = {}, {}, {}
        for original in definitions:
            if not isinstance(original, dict) or set(original) - allowed:
                raise ValueError('unknown job definition field')
            spec = copy.deepcopy(original)
            name, kind = spec.get('id'), spec.get('kind')
            if not isinstance(name, str) or not name or name in self._jobs or kind not in ('range', 'callback', 'terminal', 'conditional'):
                raise ValueError('invalid job identity/kind')
            if kind != 'conditional' and any(key in spec for key in ('secondary', 'secondary_credits', 'condition', 'predicate')):
                raise ValueError('conditional-only fields on other job')
            if kind not in ('range', 'callback') and 'handler' in spec:
                raise ValueError('body handler requires executable job kind')
            for key in ('handler', 'predicate'):
                if key in spec and spec[key] not in self._handlers:
                    raise ValueError('unresolved versioned handler')
            if kind == 'conditional':
                if 'predicate' in spec and 'condition' in spec:
                    raise ValueError('choose predicate or supplied condition')
                if 'predicate' not in spec:
                    spec.setdefault('condition', True)
                    if type(spec['condition']) is not bool:
                        raise ValueError('condition must be boolean')
            for key, default in (('chunk_size', 1), ('tail_threshold', 0), ('max_concurrency', 1)):
                spec.setdefault(key, default)
                if type(spec[key]) is not int or not (0 if key == 'tail_threshold' else 1) <= spec[key] <= 100000:
                    raise ValueError('invalid range/concurrency setting')
            receivers = spec.get('receivers', [])
            if not isinstance(receivers, list) or len(receivers) > 100000 or (receivers and kind != 'range'):
                raise ValueError('invalid receiver array')
            job = requests.new_job(credit_gate=spec.get('credit_gate', False), credits=spec.get('credits', 0))
            for flag in ('front_insert', 'early_exit_enabled'):
                if type(spec.get(flag,False)) is not bool:raise ValueError('queue flags must be boolean')
                spec.setdefault(flag,False)
            self._definitions[name] = spec
            self._jobs[name] = dict(job, executions=0, outstanding_dispatches=0, remaining=len(receivers),
                                    receivers=receivers, terminal_begins=0, usage=False)
            primary = requests.new_dependency_list(spec.get('successors', []), spec.get('credit_recipients', []))
            self._lists[name] = {'primary': primary}
            if kind == 'conditional':
                self._lists[name]['secondary'] = requests.new_dependency_list(spec.get('secondary', []), spec.get('secondary_credits', []))
        edges = {}
        for name, lists in self._lists.items():
            edges[name] = set()
            for dependencies in lists.values():
                targets = dependencies['successors'] + dependencies['credit_recipients']
                if any(target not in self._jobs for target in targets):
                    raise ValueError('unknown successor')
                edges[name].update(targets)
        visiting, visited = set(), set()
        def visit(name):
            if name in visiting:
                raise ValueError('static dependency cycles are outside adapter scope')
            if name in visited:
                return
            visiting.add(name)
            for child in edges[name]:
                visit(child)
            visiting.remove(name)
            visited.add(name)
        for name in self._jobs:
            visit(name)
        self._queue_policy = None
        self._selection_jobs = {}
        self._queue_destinations = {}
        if queue_policy is not None:
            if not isinstance(queue_policy,dict) or set(queue_policy) not in ({'shared_default','worker_mask','jobs'}, {'shared_default','worker_slots','jobs'}):
                raise ValueError('queue policy needs default, worker mask and explicit job mappings')
            policy=copy.deepcopy(queue_policy)
            topology = 'worker_slots' in policy
            if topology:
                slots = policy['worker_slots']
                if not isinstance(slots,list) or not 1 <= len(slots) <= 128 or any(type(v) is not bool for v in slots) or not any(slots):
                    raise ValueError('worker slots require 1..128 explicit presence flags and one worker')
            executable={name for name,spec in self._definitions.items() if spec['kind'] in ('range','callback')}
            if not isinstance(policy['jobs'],dict) or set(policy['jobs'])!=executable:
                raise ValueError('queue policy must map every executable job')
            for name,mapping in policy['jobs'].items():
                if not isinstance(mapping,dict) or set(mapping)-{'category','queue','limit','required_mask','excluded_mask','optional_eligible'}:
                    raise ValueError('invalid queue job mapping')
                if type(mapping.get('category')) is not int or mapping['category'] not in range(3) or (not topology and mapping.get('queue') not in ('local','shared')):
                    raise ValueError('explicit category and queue required')
                if topology:
                    if 'queue' in mapping:raise ValueError('worker topology derives queue destinations')
                    self._queue_destinations[name] = producers.enqueue_destination(mapping['category'], mapping.get('required_mask',0), slots)
                self._selection_jobs[name]=dict(kind=self._definitions[name]['kind'],executions=0,
                    limit=mapping['limit'],required_mask=mapping.get('required_mask',0),
                    excluded_mask=mapping.get('excluded_mask',0),optional_eligible=mapping.get('optional_eligible'))
            selection.select_categories(self._selection_jobs,[[],[],[]],[[],[],[]],
                shared_default=policy['shared_default'],worker_mask=0 if topology else policy['worker_mask'])
            self._queue_policy=policy
        self._identity = uuid.uuid4().hex
        self._queue, self._dispatches = [], {}
        self._queue_change, self._front_count = 0, 0
        self._next_dispatch = 0
        self._depth, self._worker_depth = 0, 0
        self._max_transitions, self._budget = max_transitions, max_transitions
        self._fault = None
        self.trace = Trace(trace_capacity)

    @contextmanager
    def _operation(self):
        if self._fault:
            raise RuntimeError('mixed scheduler is faulted; inspect and construct a fresh instance')
        if self._depth == 0:
            self._budget = self._max_transitions
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1

    def _emit(self, kind, **fields):
        self._budget -= 1
        if self._budget < 0:
            self._fault = {'type': 'TransitionBudgetExceeded'}
            raise RuntimeError('mixed scheduler transition budget exhausted')
        self.trace.emit(kind, **fields)

    def _job(self, name):
        if not isinstance(name, str) or name not in self._jobs:
            raise ValueError('unknown job')
        return self._jobs[name]

    def _invoke(self, key, context, receiver=None, predicate=False):
        try:
            callback = self._handlers[key]['callback']
            result = callback(context) if predicate else callback(context, copy.deepcopy(receiver))
            if predicate and type(result) is not bool:
                raise ValueError('predicate must return bool')
            canonical(result)
            return result
        except BaseException as exc:
            self._fault = dict(type=type(exc).__name__, message=str(exc)[:2048], handler=key)
            self.trace.emit('mixed_handler_failed', **self._fault)
            raise

    def _activate_list(self, owner, which, recurse=False):
        dependencies = self._lists[owner][which]
        if dependencies['active'] and not recurse:
            return
        if not dependencies['active']:
            for target in dependencies['successors']:
                job = self._jobs[target]
                old = job['holds']
                job['holds'] += 1
                if old == 0:
                    job['requested'] += 1
                self._emit('mixed_hold_added', owner=owner, branch=which, job=target, holds=job['holds'], requested=job['requested'])
            dependencies['active'] = True
            self._emit('mixed_list_activated', owner=owner, branch=which)
        for target in dependencies['successors']:
            self._activate(target, False)

    def _activate(self, name, recurse=False):
        for which in self._lists[name]:
            self._activate_list(name, which, recurse)

    def activate(self, name, *, recurse=False):
        self._job(name)
        if type(recurse) is not bool:
            raise ValueError('recurse must be boolean')
        with self._operation():
            self._activate(name, recurse)

    def _normal_release(self, owner, which, context):
        dependencies = self._lists[owner][which]
        if not dependencies['active']:
            return
        dependencies['active'] = False
        self._emit('mixed_normal_list_cleared', owner=owner, branch=which)
        for target in dependencies['successors']:
            job = self._jobs[target]
            old = job['holds']
            if old <= 0:
                self._fault = {'type': 'HoldUnderflow'}
                raise RuntimeError('dependency hold underflow')
            job['holds'] -= 1
            self._emit('mixed_normal_hold_released', job=target, previous_holds=old, holds=job['holds'])
            if old == 1 and job['started'] != job['requested']:
                if job['credit_gate'] and job['credits'] <= 0:
                    job['deferred'] = True
                    self._emit('mixed_begin_deferred', job=target)
                else:
                    if job['credit_gate']:
                        job['credits'] -= 1
                    self._begin(target, context)
        for target in dependencies['credit_recipients']:
            job = self._jobs[target]
            job['credits'] += 1
            self._emit('mixed_credit_added', job=target, credits=job['credits'])
            if job['credits'] > 0 and job['holds'] == 0 and job['requested'] != job['started'] and job['deferred']:
                job['credits'] -= 1
                job['deferred'] = False
                self._begin(target, context)

    def _alternate_release(self, owner, which):
        dependencies = self._lists[owner][which]
        if not dependencies['active']:
            return
        for target in dependencies['successors']:
            job = self._jobs[target]
            old = job['holds']
            if old <= 0:
                self._fault = {'type': 'HoldUnderflow'}
                raise RuntimeError('alternate hold underflow')
            job['holds'] -= 1
            self._emit('mixed_alternate_hold_released', job=target, previous_holds=old, holds=job['holds'], source_active=dependencies['active'])
            if old == 1 and job['holds'] == 0:
                self._emit('mixed_alternate_callback', job=target, job_kind=self._definitions[target]['kind'])
                for child_branch in self._lists[target]:
                    self._alternate_release(target, child_branch)
        dependencies['active'] = False
        self._emit('mixed_alternate_list_cleared', owner=owner, branch=which)

    def _begin(self, name, context):
        job, spec = self._jobs[name], self._definitions[name]
        kind = spec['kind']
        self._emit('mixed_begin_enter', job=name, job_kind=kind, state=job['state'])
        if kind == 'conditional':
            selected = self._invoke(spec['predicate'], context, predicate=True) if 'predicate' in spec else spec['condition']
            self._emit('mixed_branch_selected', job=name, selected=selected)
            self._alternate_release(name, 'secondary' if selected else 'primary')
            self._normal_release(name, 'primary' if selected else 'secondary', context)
            return
        if job['state'] == requests.SCHEDULED:
            return
        job['started'] = job['requested']
        self._activate(name)
        if kind == 'terminal':
            job['terminal_begins'] += 1
            self._emit('mixed_terminal_begin', job=name, started=job['started'])
            self._normal_release(name, 'primary', context)
            job['state'] = requests.UNSCHEDULED
        elif kind == 'range' and job['remaining'] <= 0:
            job['state'] = requests.DONE
            self._emit('mixed_empty_begin_done', job=name)
            self._finalize(name, context)
        else:
            job['state'] = requests.SCHEDULED
            if name not in self._queue:
                if spec['front_insert']:
                    self._queue.insert(0,name)
                    self._front_count += 1
                else:
                    self._queue.append(name)
                self._queue_change = (self._queue_change + 1) & 0xffffffff
            if self._queue_policy is not None and self._selection_jobs[name]['limit']==selection.INT_MAX:
                self._selection_jobs[name]['limit']=self._queue_policy['shared_default']
            self._emit('mixed_job_queued', job=name, started=job['started'], queue_change=self._queue_change, front_count=self._front_count)

    def submit(self, name, context=None):
        """Native local gate; allowed inside another job's callback.

        There is deliberately no all-jobs-drained prerequisite. EndFrame can
        submit an UNSCHEDULED root while EndFrame accounting is still positive.
        Conditional roots require explicit activation before submission.
        """
        job = self._job(name)
        with self._operation():
            if job['state'] == requests.UNSCHEDULED:
                job['requested'] += 1
                self._emit('mixed_request_submitted', job=name, requested=job['requested'])
                if job['holds'] == 0:
                    self._begin(name, context)
            job['usage'] = True
            return job['state'] == requests.SCHEDULED

    def _finalize(self, name, context):
        job = self._jobs[name]
        self._emit('mixed_finalize_enter', job=name, executions=job['executions'], outstanding_dispatches=job['outstanding_dispatches'])
        self._normal_release(name, 'primary', context)
        job['state'] = requests.UNSCHEDULED
        self._emit('mixed_finalized', job=name, outstanding_dispatches=job['outstanding_dispatches'])

    def _remove_queued(self, name):
        self._queue.remove(name)
        if self._definitions[name]['front_insert']:
            self._front_count -= 1

    def _validate_worker(self, worker_index):
        topology = self._queue_policy is not None and 'worker_slots' in self._queue_policy
        if topology:
            slots = self._queue_policy['worker_slots']
            if type(worker_index) is not int or not 0 <= worker_index < len(slots) or not slots[worker_index]:
                raise ValueError('explicit present worker index required')
        elif worker_index is not None:
            raise ValueError('worker index requires topology policy')

    def _worker_busy(self, worker_index):
        return worker_index is not None and any(d['worker_index']==worker_index for d in self._dispatches.values())

    def _select_queue(self, records, order, worker_index=None):
        local=[[],[],[]];shared=[[],[],[]]
        for name in order:
            if self._jobs[name]['state'] != requests.SCHEDULED:continue
            mapping=self._queue_destinations[name] if self._queue_destinations else self._queue_policy['jobs'][name]
            if self._queue_destinations and mapping['queue']=='local' and mapping['worker_index']!=worker_index:continue
            (local if mapping['queue']=='local' else shared)[mapping['category']].append(name)
            records[name]['executions']=self._jobs[name]['executions']
        return selection.select_categories(records,local,shared,
            shared_default=self._queue_policy['shared_default'],worker_mask=producers.worker_mask(worker_index) if 'worker_slots' in self._queue_policy else self._queue_policy['worker_mask'])

    def ready(self, *, worker_index=None):
        """Read-only eligible selection order; preview uses copied limit state.

        Under optional policy, repeatedly selects/removes candidates without
        reserving them. Only the first entry predicts the immediate next choice.
        """
        self._validate_worker(worker_index)
        if self._worker_busy(worker_index):return []
        if self._queue_policy is not None:
            records=copy.deepcopy(self._selection_jobs);order=list(self._queue);result=[]
            while order:
                chosen=self._select_queue(records,order,worker_index)['selected']
                if chosen is None:break
                result.append(chosen);order.remove(chosen)
            return result
        return [name for name in self._queue if self._jobs[name]['state'] == requests.SCHEDULED
                and self._jobs[name]['executions'] < self._definitions[name]['max_concurrency']]

    def reserve(self, name=None, *, worker_index=None):
        """Ordinary queue route; optional policy disallows a forced nonwinner."""
        self._validate_worker(worker_index)
        if self._worker_busy(worker_index):
            if name is not None:raise ValueError('worker already has an outstanding dispatch')
            return None
        with self._operation():
            if self._queue_policy is not None:
                if name is not None:
                    preview=self._select_queue(copy.deepcopy(self._selection_jobs),self._queue,worker_index)
                    if preview['selected']!=name:raise ValueError('requested job is not policy winner')
                result=self._select_queue(self._selection_jobs,self._queue,worker_index)
                name=result['selected']
                self._emit('mixed_queue_selected',selection=result,worker_index=worker_index)
                if name is None:return None
            else:
                ready = self.ready()
                if name is None:
                    if not ready:return None
                    name = ready[0]
                if name not in ready:raise ValueError('job is not queue-reservable')
            job = self._jobs[name]
            job['outstanding_dispatches'] += 1
            job['executions'] += 1
            token = DispatchToken(self._identity, self._next_dispatch)
            self._next_dispatch += 1
            self._dispatches[token.dispatch] = dict(job=name, stage='reserved', range=None, range_sequence=0, callback_ran=False, worker_index=worker_index)
            self._emit('mixed_dispatch_reserved', job=name, dispatch=token.dispatch,
                       executions=job['executions'], outstanding_dispatches=job['outstanding_dispatches'], worker_index=worker_index)
            if self._definitions[name]['kind'] == 'callback':
                job['state'] = requests.DONE
                self._remove_queued(name)
                self._emit('mixed_callback_done_on_reservation', job=name, dispatch=token.dispatch)
            return token

    def reserve_helper(self, name, *, helper_id):
        """One explicit helper invocation for an active range job.

        Bypasses queue selection and its concurrency cap. The caller retains
        lifecycle ownership; no native TLS or blocking wait is represented.
        """
        if type(helper_id) is not str or not helper_id or len(helper_id) > 128:
            raise ValueError('bounded nonempty helper identity required')
        job = self._job(name)
        if self._definitions[name]['kind'] != 'range':
            raise ValueError('helper requires a compatible range job')
        if any(d.get('helper_id') == helper_id for d in self._dispatches.values()):
            raise ValueError('helper context already has an outstanding dispatch')
        with self._operation():
            if job['remaining'] <= 0:
                return None
            if job['state'] != requests.SCHEDULED:
                raise ValueError('helper requires an active scheduled request')
            job['outstanding_dispatches'] += 1
            job['executions'] += 1
            token = DispatchToken(self._identity, self._next_dispatch)
            self._next_dispatch += 1
            self._dispatches[token.dispatch] = dict(job=name, stage='reserved',
                range=None, range_sequence=0, callback_ran=False,
                worker_index=None, helper_id=helper_id)
            self._emit('mixed_dispatch_reserved', job=name, dispatch=token.dispatch,
                executions=job['executions'], outstanding_dispatches=job['outstanding_dispatches'],
                worker_index=None, helper_id=helper_id, route='helper')
            return token

    def teardown_wait_status(self, name):
        """Inspect the local destructor predicate without destroying anything.

        See SCHEDULER_DELEGATES.md, "Submission enables the teardown wait".
        This serial observation is not permission to unload a native plugin.
        """
        job = self._job(name)
        would_wait = job['usage'] and (
            job['state'] != requests.UNSCHEDULED or job['outstanding_dispatches'] > 0)
        return dict(wait_enabled=job['usage'], would_wait=bool(would_wait),
                    state=job['state'], executions=job['executions'],
                    outstanding_dispatches=job['outstanding_dispatches'],
                    scope='local teardown predicate; no submission exclusion or unload permission')

    def helper_wait_status(self, name):
        """Owned serial observation of the helper's two distinct predicates."""
        job = self._job(name)
        if self._definitions[name]['kind'] != 'range':
            raise ValueError('helper status requires a compatible range job')
        return dict(empty=job['remaining'] <= 0,
            wait_complete=job['state'] == requests.UNSCHEDULED and job['outstanding_dispatches'] <= 0,
            state=job['state'], executions=job['executions'],
            outstanding_dispatches=job['outstanding_dispatches'],
            scope='owned serial observation; not native atomic snapshot or submission exclusion')

    def _dispatch(self, token):
        if (type(token) is not DispatchToken or type(token.scheduler_id) is not str
                or token.scheduler_id != self._identity or type(token.dispatch) is not int
                or token.dispatch < 0 or token.dispatch not in self._dispatches):
            raise ValueError('invalid/stale dispatch token')
        return self._dispatches[token.dispatch]

    def claim_range(self, token):
        with self._operation():
            dispatch = self._dispatch(token)
            name = dispatch['job']
            job, spec = self._jobs[name], self._definitions[name]
            if spec['kind'] != 'range' or dispatch['range'] is not None:
                raise ValueError('range claim requires a range worker without an open range')
            if dispatch.get('yield_requested',False):return None
            old, chunk, tail = job['remaining'], spec['chunk_size'], spec['tail_threshold']
            if old <= 0:
                return None
            proposed = old - chunk if old >= tail + chunk else tail if old > tail else old - 1
            # The first comparison is conditional on old>tail in the native loop.
            if old <= tail:
                proposed = old - 1
            job['remaining'] = proposed
            dispatch['range_sequence'] += 1
            result = RangeToken(self._identity, token.dispatch, dispatch['range_sequence'], proposed, old-proposed)
            dispatch['range'] = result
            if 'captured_queue_change' not in dispatch:
                dispatch['captured_queue_change'] = self._queue_change
            self._emit('mixed_range_claimed', job=name, dispatch=token.dispatch, start=proposed,
                       count=old-proposed, remaining=proposed, executions=job['executions'])
            return result

    def execute_range(self, token, claimed_range, context=None):
        with self._operation():
            dispatch = self._dispatch(token)
            if (type(claimed_range) is not RangeToken or type(claimed_range.scheduler_id) is not str
                    or any(type(getattr(claimed_range, field)) is not int for field in ('dispatch', 'sequence', 'start', 'count'))
                    or claimed_range.dispatch < 0 or claimed_range.sequence < 1
                    or claimed_range.start < 0 or claimed_range.count < 1
                    or dispatch['range'] != claimed_range):
                raise ValueError('range token does not match retained claim')
            claimed_range = dispatch['range']
            if self._worker_depth:
                raise RuntimeError('nested worker execution is outside serial adapter scope')
            name, spec = dispatch['job'], self._definitions[dispatch['job']]
            dispatch['stage'] = 'running'
            self._worker_depth += 1
            try:
                for index in range(claimed_range.start + claimed_range.count - 1, claimed_range.start - 1, -1):
                    receiver = self._jobs[name]['receivers'][index]
                    self._emit('mixed_receiver_enter', job=name, dispatch=token.dispatch, receiver_index=index)
                    if 'handler' in spec:
                        self._invoke(spec['handler'], context, receiver)
                    self._emit('mixed_receiver_return', job=name, dispatch=token.dispatch, receiver_index=index)
                dispatch['range'] = None
                dispatch['stage'] = 'reserved'
                dispatch['yield_requested'] = producers.range_should_yield(
                    dispatch['captured_queue_change'], self._queue_change,
                    spec['early_exit_enabled'], self._front_count)
                if dispatch['yield_requested']:
                    self._emit('mixed_range_yield_requested', job=name, dispatch=token.dispatch,
                        captured_change=dispatch['captured_queue_change'], current_change=self._queue_change,
                        front_count=self._front_count, remaining=self._jobs[name]['remaining'])
            finally:
                self._worker_depth -= 1

    def execute_callback(self, token, context=None):
        with self._operation():
            dispatch = self._dispatch(token)
            spec = self._definitions[dispatch['job']]
            if spec['kind'] != 'callback' or dispatch['callback_ran']:
                raise ValueError('callback requires an unexecuted callback-job reservation')
            if self._worker_depth:
                raise RuntimeError('nested worker execution is outside serial adapter scope')
            dispatch['stage'] = 'running'
            self._worker_depth += 1
            try:
                self._emit('mixed_callback_enter', job=dispatch['job'], dispatch=token.dispatch)
                if 'handler' in spec:
                    self._invoke(spec['handler'], context)
                dispatch['callback_ran'] = True
                dispatch['stage'] = 'reserved'
                self._emit('mixed_callback_return', job=dispatch['job'], dispatch=token.dispatch)
            finally:
                self._worker_depth -= 1

    def finish_dispatch(self, token, *, early_exit=False, context=None):
        if type(early_exit) is not bool:
            raise ValueError('early_exit must be boolean')
        with self._operation():
            dispatch = self._dispatch(token)
            name = dispatch['job']
            job, spec = self._jobs[name], self._definitions[name]
            if dispatch['range'] is not None or dispatch['stage'] == 'running':
                raise ValueError('cannot finish a callback/range that has not returned')
            if spec['kind'] == 'callback' and not dispatch['callback_ran']:
                raise ValueError('callback body has not returned')
            if spec['kind'] == 'range' and job['remaining'] > 0 and not early_exit and not dispatch.get('yield_requested',False):
                raise ValueError('positive unclaimed range needs explicit early_exit observation')
            job['executions'] -= 1
            self._emit('mixed_execution_returned', job=name, dispatch=token.dispatch, executions=job['executions'], remaining=job['remaining'])
            if job['state'] == requests.SCHEDULED and spec['kind'] == 'range' and job['remaining'] <= 0:
                job['state'] = requests.DONE
                if name in self._queue:
                    self._remove_queued(name)
                self._emit('mixed_range_done', job=name, executions=job['executions'])
            if job['state'] == requests.DONE and job['executions'] == 0:
                self._finalize(name, context)
            job['outstanding_dispatches'] -= 1
            del self._dispatches[token.dispatch]
            self._emit('mixed_dispatch_accounting_returned', job=name, dispatch=token.dispatch,
                       outstanding_dispatches=job['outstanding_dispatches'])

    def dispatch_next(self, context=None, *, worker_index=None):
        with self._operation():
            token = self.reserve(worker_index=worker_index)
            if token is None:
                return False
            name = self._dispatch(token)['job']
            if self._definitions[name]['kind'] == 'callback':
                self.execute_callback(token, context)
            else:
                while True:
                    claimed = self.claim_range(token)
                    if claimed is None:
                        break
                    self.execute_range(token, claimed, context)
            self.finish_dispatch(token, context=context)
            return True

    def run_ready(self, context=None, max_dispatches=1000, *, worker_index=None):
        if type(max_dispatches) is not int or not 0 <= max_dispatches <= 100000:
            raise ValueError('invalid dispatch bound')
        count = 0
        while count < max_dispatches and self.dispatch_next(context, worker_index=worker_index):
            count += 1
        return count

    def prepare_range(self, name, receivers):
        """Adapter refill only when this target is UNSCHEDULED and drained.

        Does not require other jobs (such as EndFrame) to have returned. This is
        an explicit caller-facing fixture gate, not a native owner-lifetime proof.
        Dependency holds/activated outgoing lists are allowed: gather can prepare
        a held job before its begin. They are not executing callback reservations.
        """
        job = self._job(name)
        if not isinstance(receivers, list) or len(receivers) > 100000:
            raise ValueError('receiver array must be bounded')
        value = json.loads(canonical(receivers))
        with self._operation():
            if self._definitions[name]['kind'] != 'range' or job['state'] != requests.UNSCHEDULED or job['executions'] or job['outstanding_dispatches']:
                raise RuntimeError('target receiver storage is not safely refillable in this adapter')
            job['receivers'], job['remaining'] = value, len(value)
            self._emit('mixed_receiver_storage_prepared', job=name, count=len(value))

    def snapshot(self):
        dispatches = {}
        for key, record in self._dispatches.items():
            item = copy.deepcopy(record)
            if item['range'] is not None:
                r = item['range']
                item['range'] = dict(sequence=r.sequence, start=r.start, count=r.count)
            dispatches[str(key)] = item
        selection_jobs=copy.deepcopy(self._selection_jobs)
        for name,record in selection_jobs.items():record['executions']=self._jobs[name]['executions']
        return copy.deepcopy(dict(schema_version=1, jobs=self._jobs, lists=self._lists,
                                  queue=self._queue, dispatches=dispatches, fault=self._fault,
                                  queue_change=self._queue_change, front_count=self._front_count,
                                  handler_versions={key: value['version'] for key, value in self._handlers.items()},
                                  trace=self.trace.snapshot(),
                                  queue_policy=self._queue_policy, selection_jobs=selection_jobs, queue_destinations=self._queue_destinations,
                                  scope='serial selected-job semantics; not native concurrent scheduler'))
