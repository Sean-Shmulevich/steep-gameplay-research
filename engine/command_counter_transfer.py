"""Authored interleaving harness for recovered command preparation counters.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, command participants preparation.
Each event represents one atomic instruction, not a Python thread-safe operation.
Caller supplies event order; native producer identity/publication is unresolved.
"""

def replay_counter_transfers(initial, events):
    """Replay exchange/add boundaries for pairs A and B, returning every state.

    initial maps A/B to (active, deferred) uint32. Events are (operation,pair,value).
    'exchange' captures and clears deferred for that pair; 'add' consumes that
    captured value. Their value must be None. 'submit' is an explicitly supplied
    synthetic atomic increment, not a claimed recovered producer implementation.
    A transfer may remain pending at the end to expose the intermediate state.
    """
    def word(value):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('uint32 counter required')
        return value
    if set(initial) != {'A','B'}:
        raise ValueError('two named counter pairs required')
    counters={k:[word(v[0]),word(v[1])] for k,v in initial.items() if len(v)==2}
    if len(counters)!=2:raise ValueError('active and deferred required')
    pending={};trace=[]
    for operation,pair,value in events:
        if pair not in counters:raise ValueError('unknown counter pair')
        active,deferred=counters[pair]
        if operation=='submit':
            counters[pair][1]=(deferred+word(value))&0xffffffff
        elif operation=='exchange' and value is None:
            if pair in pending:raise ValueError('prior transfer still pending')
            pending[pair]=deferred;counters[pair][1]=0
        elif operation=='add' and value is None:
            if pair not in pending:raise ValueError('exchange required before add')
            counters[pair][0]=(active+pending.pop(pair))&0xffffffff
        else:raise ValueError('unsupported event')
        trace.append(dict(counters={k:list(v) for k,v in counters.items()},pending=dict(pending)))
    return dict(counters=counters,pending=pending,trace=trace,
                native_concurrency_proved=False)
