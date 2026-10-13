"""Recovered serial ordinary-queue selection, with caller-supplied meanings.

See SCHEDULER_QUEUE_ELIGIBILITY.md. No locks, native callbacks, notification
operations or category/mask producers are reconstructed here. Only limit fields
mutate. Selection does not reserve or increment execution counters.
"""
INT_MAX = 2147483647
INT_MIN = -2147483648


def _i32(value):
    if type(value) is not int or not INT_MIN <= value <= INT_MAX:
        raise ValueError('signed int32 required')
    return value


def _mask(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('uint32 mask required')
    return value


def validate_job(job):
    if not isinstance(job,dict) or job.get('kind') not in ('range','callback'):
        raise ValueError('known range or callback kind required')
    _i32(job['limit']);_i32(job['executions'])
    _mask(job.get('required_mask',0));_mask(job.get('excluded_mask',0))
    if job.get('optional_eligible') is not None and type(job['optional_eligible']) is not bool:
        raise ValueError('optional eligibility must be a supplied boolean or None')


def occupancy_score(executions, limit, shared_default):
    """Signed low-32-bit multiplication followed by truncation toward zero."""
    _i32(executions);_i32(limit);_i32(shared_default)
    if limit <= 0:return shared_default
    product=((executions*shared_default+2**31)%2**32)-2**31
    return (abs(product)//limit)*(-1 if product<0 else 1)


def _validate(jobs, orders, shared_default, worker_mask):
    _i32(shared_default);_mask(worker_mask)
    if not isinstance(jobs,dict):raise ValueError('jobs must be a mapping')
    for name,job in jobs.items():
        if not isinstance(name,str) or not name:raise ValueError('job IDs must be nonempty strings')
        validate_job(job)
    if len({id(j) for j in jobs.values()})!=len(jobs):raise ValueError('aliased job records unsupported')
    for order in orders:
        if not isinstance(order,list) or any(not isinstance(n,str) or n not in jobs for n in order):raise ValueError('invalid queue order')
        if len(set(order))!=len(order):raise ValueError('duplicate queue entries unsupported')


def _select(jobs, order, shared_default, worker_mask, local):
    result=dict(selected=None,score=None,rejected_by_affinity=False,visited=[])
    best=INT_MAX
    for name in order:
        job=jobs[name];result['visited'].append(name)
        if job.get('optional_eligible') is False:continue
        # The range virtual resolves the sentinel before affinity. Callback
        # eligibility is constant true; its sentinel survives affinity rejection.
        if job['kind']=='range':
            if job['limit']==INT_MAX:job['limit']=shared_default
            if not job['executions']<job['limit']:continue
        if not local and ((job.get('required_mask',0) and not worker_mask&job['required_mask']) or worker_mask&job.get('excluded_mask',0)):
            result['rejected_by_affinity']=True;continue
        if job['limit']==INT_MAX:job['limit']=shared_default
        score=occupancy_score(job['executions'],job['limit'],shared_default)
        if score<best:
            result.update(selected=name,score=score);best=score
            if score==0:break
    return result


def select_queue(jobs, order, *, shared_default, worker_mask, local=False):
    if type(local) is not bool:raise ValueError('local must be boolean')
    _validate(jobs,[order],shared_default,worker_mask)
    return _select(jobs,order,shared_default,worker_mask,local)


def select_categories(jobs, local, shared, *, shared_default, worker_mask):
    """Visit local then shared for each category, returning first selected job."""
    if not isinstance(local,list) or not isinstance(shared,list) or len(local)!=3 or len(shared)!=3:
        raise ValueError('three local and shared categories required')
    _validate(jobs,local+shared,shared_default,worker_mask)
    names=[n for order in local+shared for n in order]
    if len(set(names))!=len(names):raise ValueError('job present in multiple queues')
    visits=[];rejected=False
    for category in range(3):
        for source,queues in (('local',local),('shared',shared)):
            result=_select(jobs,queues[category],shared_default,worker_mask,source=='local')
            visits.append(dict(category=category,source=source,visited=result['visited']))
            rejected=rejected or result['rejected_by_affinity']
            if result['selected'] is not None:
                return dict(result,category=category,source=source,rejected_by_affinity=rejected,scans=visits)
    return dict(selected=None,score=None,category=None,source=None,rejected_by_affinity=rejected,visited=[],scans=visits)
