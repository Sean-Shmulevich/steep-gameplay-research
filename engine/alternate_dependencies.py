"""Serial alternate-release reference for explicitly selected callback bindings.

See docs/reconstruction/ALTERNATE_DEPENDENCY_RELEASE.md. Ordinary callbacks
propagate through one outgoing list; conditional callbacks propagate through
both, without evaluating a predicate. List activation clears AFTER traversal.
No normal begin, request acknowledgement, credit mutation, execution cancellation
or native exclusion is implied. Platform locks/atomics are not emulated.

Graph: {jobs: {id: request_state.new_job(...)},
        lists: {id: request_state.new_dependency_list(...)},
        bindings: {job_id: {kind:'ordinary', outgoing:list_id} OR
                           {kind:'conditional', primary:list_id, secondary:list_id}}}.
Use an empty outgoing list for a leaf. Bindings are caller evidence, not guessed
from job names. Transactions, limits, alias and cycle rejection are adapter policy.
"""
import copy

from . import request_state as requests


def new_graph(jobs, lists, bindings):
    graph = dict(jobs=jobs, lists=lists, bindings=bindings)
    _validate(graph)
    return copy.deepcopy(graph)


def _validate(graph):
    if not isinstance(graph, dict) or set(graph) != {'jobs', 'lists', 'bindings'}:
        raise ValueError('invalid alternate graph schema')
    jobs, lists, bindings = graph['jobs'], graph['lists'], graph['bindings']
    if not all(isinstance(x, dict) for x in (jobs, lists, bindings)):
        raise ValueError('graph sections must be objects')
    if len(jobs) > 128 or len(lists) > 256 or set(jobs) != set(bindings):
        raise ValueError('bounded jobs need exactly one callback binding each')
    for objects in (jobs, lists):
        if any(not isinstance(name, str) or not name for name in objects):
            raise ValueError('graph identifiers must be nonempty strings')
        if len({id(value) for value in objects.values()}) != len(objects):
            raise ValueError('one canonical ID per graph object is required')
    for job in jobs.values():
        requests._validate_job(job)
    for dependencies in lists.values():
        requests._validate_list(dependencies)
        if any(target not in jobs for target in dependencies['successors'] + dependencies['credit_recipients']):
            raise ValueError('unknown dependency recipient')
    edges = {}
    for job_id, binding in bindings.items():
        if not isinstance(binding, dict):
            raise ValueError('invalid callback binding')
        if binding.get('kind') == 'ordinary' and set(binding) == {'kind', 'outgoing'}:
            outgoing = [binding['outgoing']]
        elif binding.get('kind') == 'conditional' and set(binding) == {'kind', 'primary', 'secondary'}:
            outgoing = [binding['primary'], binding['secondary']]
        else:
            raise ValueError('unsupported alternate callback kind')
        if any(not isinstance(name, str) or name not in lists for name in outgoing):
            raise ValueError('unknown outgoing list')
        edges[job_id] = {target for name in outgoing for target in lists[name]['successors']}
    # Reject cycles even if currently inactive: this adapter does not model
    # reentrant cyclic ownership or native recursive-lock semantics.
    remaining = {name: len(targets) for name, targets in edges.items()}
    incoming = {name: [] for name in jobs}
    for name, targets in edges.items():
        for target in targets:
            incoming[target].append(name)
    ready = [name for name, count in remaining.items() if not count]
    visited = 0
    while ready:
        name = ready.pop()
        visited += 1
        for source in incoming[name]:
            remaining[source] -= 1
            if remaining[source] == 0:
                ready.append(source)
    if visited != len(jobs):
        raise ValueError('cyclic alternate propagation is outside adapter scope')


def decrement_alternate_hold(job):
    """Return old==1 after one decrement, without executing its callback.

    A caller may add a hold before calling on_alternate_last_hold to test the
    separate current-count check. That explicit interleaving is a synthetic
    fixture, not concurrent execution or a native race observation.
    """
    requests._validate_job(job)
    if job['holds'] == 0:
        raise ValueError('adapter refuses alternate hold underflow')
    previous = job['holds']
    job['holds'] -= 1
    return previous == 1


def _transaction(graph, target, entry, max_events):
    _validate(graph)
    if type(max_events) is not int or not 1 <= max_events <= 100000:
        raise ValueError('max_events must be in 1..100000')
    section = 'lists' if entry == 'list' else 'jobs'
    if not isinstance(target, str) or target not in graph[section]:
        raise ValueError('unknown alternate release target')
    work = copy.deepcopy(graph)
    events = []

    def emit(kind, **fields):
        if len(events) >= max_events:
            raise ValueError('alternate propagation event limit exceeded')
        events.append(dict(sequence=len(events), kind=kind, **fields))

    def callback(job_id):
        job = work['jobs'][job_id]
        binding = work['bindings'][job_id]
        emit('alternate_callback', job=job_id, callback_kind=binding['kind'], current_holds=job['holds'])
        if job['holds'] != 0:
            emit('alternate_callback_blocked', job=job_id, reason='current_hold_count_nonzero')
            return
        names = [binding['outgoing']] if binding['kind'] == 'ordinary' else [binding['primary'], binding['secondary']]
        for name in names:
            if work['lists'][name]['active']:
                release(name)

    def release(list_id):
        dependencies = work['lists'][list_id]
        emit('alternate_list_enter', list=list_id, active=dependencies['active'])
        if not dependencies['active']:
            return
        for job_id in dependencies['successors']:
            job = work['jobs'][job_id]
            previous = job['holds']
            last = decrement_alternate_hold(job)
            emit('alternate_hold_released', list=list_id, job=job_id,
                 previous_holds=previous, current_holds=job['holds'],
                 source_list_active=dependencies['active'])
            if last:
                callback(job_id)
        # Credit-recipient arrays are intentionally untouched by this helper.
        dependencies['active'] = False
        emit('alternate_list_cleared', list=list_id, active=False)

    release(target) if entry == 'list' else callback(target)
    # Commit only changed hold/activation values, preserving caller graph object
    # identity. No requested, started, credit, deferred or lifecycle writes.
    for name, job in work['jobs'].items():
        graph['jobs'][name]['holds'] = job['holds']
    for name, dependencies in work['lists'].items():
        graph['lists'][name]['active'] = dependencies['active']
    return events


def release_alternate(graph, list_id, *, max_events=4096):
    """Release one active list, recursively following declared callback kinds."""
    return _transaction(graph, list_id, 'list', max_events)


def on_alternate_last_hold(graph, job_id, *, max_events=4096):
    """Invoke the selected callback with its independent current-hold recheck."""
    return _transaction(graph, job_id, 'callback', max_events)
