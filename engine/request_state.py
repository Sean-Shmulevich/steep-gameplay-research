"""Narrow serial reducers for recovered request/hold/credit operations.

See docs/reconstruction/REQUEST_STATE_MODEL.md and SCHEDULER_REARM.md.
Returned effects identify virtual-call boundaries; they are NOT executed jobs.
The caller must resolve/consume them at their proper position before relying on
further native ordering. There is no recursive graph interpreter, lock, atomic
operation, callback registry, queue drain, alternative release or native barrier.
Range validation/transactional failures are adapter protections, not native code.
"""
import copy

UNSCHEDULED, SCHEDULED, DONE = 'UNSCHEDULED', 'SCHEDULED', 'DONE'
STATES = (UNSCHEDULED, SCHEDULED, DONE)
MAX_COUNT = 2**31 - 1


def _integer(value, name, minimum=0):
    if type(value) is not int or not minimum <= value <= MAX_COUNT:
        raise ValueError(name + ' outside supported signed-count domain')
    return value


def new_job(*, state=UNSCHEDULED, requested=0, started=0, holds=0,
            credit_gate=False, credits=0, deferred=False):
    job = dict(state=state, requested=requested, started=started, holds=holds,
               credit_gate=credit_gate, credits=credits, deferred=deferred)
    _validate_job(job)
    return job


def _validate_job(job):
    if not isinstance(job, dict) or set(job) != {'state', 'requested', 'started', 'holds', 'credit_gate', 'credits', 'deferred'}:
        raise ValueError('invalid request job schema')
    if job['state'] not in STATES:
        raise ValueError('unknown lifecycle state')
    for name in ('requested', 'started', 'holds'):
        _integer(job[name], name)
    _integer(job['credits'], 'credits', -(2**31))
    if type(job['credit_gate']) is not bool or type(job['deferred']) is not bool:
        raise ValueError('credit flags must be boolean')


def new_dependency_list(successors=(), credit_recipients=()):
    """Caller-supplied topology; entries retain order and may repeat."""
    result = dict(active=False, successors=list(successors), credit_recipients=list(credit_recipients))
    _validate_list(result)
    return result


def _validate_list(dependencies):
    if not isinstance(dependencies, dict) or set(dependencies) != {'active', 'successors', 'credit_recipients'}:
        raise ValueError('invalid dependency list schema')
    if type(dependencies['active']) is not bool:
        raise ValueError('list activation flag must be boolean')
    for key in ('successors', 'credit_recipients'):
        values = dependencies[key]
        if not isinstance(values, list) or len(values) > 65535 or any(not isinstance(x, str) or not x for x in values):
            raise ValueError('dependency recipients must be bounded identifier lists')


def submit(job):
    """Only UNSCHEDULED increments requested; zero holds emits invoke_begin.

    This local submit path does not consult credit_gate. Its native usage flag,
    profiling and boolean return based on the later lifecycle state are omitted.
    """
    _validate_job(job)
    if job['state'] != UNSCHEDULED:
        return []
    requested = _integer(job['requested'] + 1, 'requested')
    job['requested'] = requested
    return [{'kind': 'invoke_begin', 'source': 'submit'}] if job['holds'] == 0 else []


def begin_ordinary(job):
    """Selected ordinary begin prefix, stopping before virtual work effects.

    SCHEDULED is the actual local no-op gate. DONE is not rejected here. This
    prefix has no holds/credit/started==requested guard of its own. Caller must
    establish why begin was invoked, and perform its selected queue/empty path.
    """
    _validate_job(job)
    if job['state'] == SCHEDULED:
        return []
    job['started'] = job['requested']
    return [dict(kind='invoke_activation', recurse=False),
            dict(kind='evaluate_empty_then_queue_or_finalize')]


def add_hold(job):
    """One hold; only the zero-to-one transition increments requested."""
    _validate_job(job)
    holds = _integer(job['holds'] + 1, 'holds')
    requested = _integer(job['requested'] + (job['holds'] == 0), 'requested')
    job.update(holds=holds, requested=requested)


def release_one_dependency(job):
    """Normal hold-release local branch; never emulates alternative release."""
    _validate_job(job)
    if job['holds'] == 0:
        raise ValueError('adapter refuses dependency-hold underflow')
    previous = job['holds']
    job['holds'] -= 1
    if previous != 1 or job['started'] == job['requested']:
        return []
    if job['credit_gate']:
        if job['credits'] <= 0:
            job['deferred'] = True
            return [dict(kind='begin_deferred', source='last_hold')]
        job['credits'] -= 1
    # This branch does not clear a previously set deferred flag in the source.
    return [dict(kind='invoke_begin', source='last_hold')]


def release_one_credit(job):
    """The separate credit-recipient loop inside NORMAL list release.

    Credits increment first. Positive post-increment credit + zero holds + an
    unstarted request + deferred flag consume one credit, clear deferred and
    invoke begin. This is not the receiver-specific alternative dependency route.
    """
    _validate_job(job)
    job['credits'] = _integer(job['credits'] + 1, 'credits', -(2**31))
    if job['credits'] <= 0 or job['holds'] != 0:
        return []
    if job['started'] == job['requested'] or not job['deferred']:
        return []
    job['credits'] -= 1
    job['deferred'] = False
    return [dict(kind='invoke_begin', source='credit_recipient')]


def _copy_recipients(dependencies, jobs):
    _validate_list(dependencies)
    if not isinstance(jobs, dict):
        raise ValueError('jobs must map recipient IDs to job states')
    targets = dependencies['successors'] + dependencies['credit_recipients']
    selected = {}
    identities = {}
    for target in targets:
        if target not in jobs:
            raise ValueError('missing dependency recipient: ' + target)
        _validate_job(jobs[target])
        identity = id(jobs[target])
        if identity in identities and identities[identity] != target:
            raise ValueError('adapter requires one canonical ID per recipient object')
        identities[identity] = target
        selected[target] = copy.deepcopy(jobs[target])
    return selected


def activate(dependencies, jobs, *, recurse=False):
    """Normal activation prefix plus ordered opaque successor-call effects.

    An inactive list adds all holds, then marks active before propagating. An
    already active list with recurse=False does nothing. recurse=True propagates
    again without adding holds. Child calls still receive recurse=False: the
    selected parent routine supplies zero to its list walker, even when its own
    incoming recurse flag was true. Resolving those virtual methods is caller work.
    """
    if type(recurse) is not bool:
        raise ValueError('recurse must be boolean')
    _validate_list(dependencies)
    if dependencies['active'] and not recurse:
        return []
    selected = _copy_recipients(dependencies, jobs)
    if not dependencies['active']:
        for target in dependencies['successors']:
            add_hold(selected[target])
        for target, value in selected.items():
            jobs[target].update(value)
        dependencies['active'] = True
    return [dict(kind='invoke_activation', job=target, recurse=False)
            for target in dependencies['successors']]


def release_normal(dependencies, jobs):
    """Nonrecursive normal-list reducer, with ordered virtual-call receipts.

    Inactive lists are no-ops, including credit recipients. Caller must use the
    one-recipient reducers instead if callback effects can alter later recipients:
    this batch helper collects opaque calls but deliberately does not execute them.
    Native normal release clears active BEFORE successor calls. This helper
    commits its detached arithmetic transaction at the end, then returns opaque
    effects with active already false; it is not a recursive execution model.
    """
    _validate_list(dependencies)
    if not dependencies['active']:
        return []
    selected = _copy_recipients(dependencies, jobs)
    effects = []
    for target in dependencies['successors']:
        effects.extend(dict(effect, job=target) for effect in release_one_dependency(selected[target]))
    for target in dependencies['credit_recipients']:
        effects.extend(dict(effect, job=target) for effect in release_one_credit(selected[target]))
    for target, value in selected.items():
        jobs[target].update(value)
    dependencies['active'] = False
    return effects
