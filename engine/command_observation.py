"""Interpret authored native command-observer records without game addresses.

See REQUEST_COMMAND_LIFECYCLE.md, Native observation callback preparation.
This is diagnostic policy, not recovered admission or completion semantics.
Caller supplies copied records after recorder close/drain and verifies ABI.
No record or counter proves owner lifetime, exclusive phase, or safe mutation.
"""


def summarize_deliveries(request_ids, records, *, dropped_records=0):
    """Group by the observer's result/request ID, never temporary storage.

    Each record supplies result, function_storage, thread, caller, entry_tick,
    exit_tick as uint64 values. Addresses are used only to detect shared storage;
    output does not include them. Ticks are reported as ticks, not seconds.
    dropped_records refers to recorder exhaustion only, not queue rejection.
    Absence remains 'not_observed' even when dropped_records is zero: closure,
    pending work or failed publication are still possible.
    """
    def u64(value, *, positive=False):
        return type(value) is int and (1 if positive else 0) <= value < 2**64

    ids = list(request_ids)
    if any(not u64(v, positive=True) for v in ids) or len(set(ids)) != len(ids):
        raise ValueError('unique positive uint64 request IDs required')
    if not u64(dropped_records):
        raise ValueError('uint64 dropped record count required')
    groups = {v: [] for v in ids}
    storage_users = {}
    count = 0
    for record in records:
        fields = ('result', 'function_storage', 'thread', 'caller', 'entry_tick', 'exit_tick')
        if any(not u64(record.get(k)) for k in fields) or not record['result']:
            raise ValueError('record requires uint64 fields and nonzero request ID')
        if record['exit_tick'] < record['entry_tick']:
            raise ValueError('exit tick precedes entry; clock interpretation unresolved')
        rid = record['result']
        groups.setdefault(rid, []).append(record)
        storage_users.setdefault(record['function_storage'], set()).add(rid)
        count += 1
    requests = []
    for rid, deliveries in groups.items():
        requests.append(dict(
            request_id=rid,
            submitted_in_this_manifest=rid in ids,
            status='observed' if deliveries else 'not_observed',
            observed_deliveries=len(deliveries),
            repeated_delivery_observed=len(deliveries) > 1,
            observed_threads=sorted({r['thread'] for r in deliveries}),
            first_entry_tick=min((r['entry_tick'] for r in deliveries), default=None),
            last_exit_tick=max((r['exit_tick'] for r in deliveries), default=None),
        ))
    return dict(
        requests=requests,
        captured_records=count,
        recorder_dropped_records=dropped_records,
        shared_storage_between_request_ids=any(len(v) > 1 for v in storage_users.values()),
        unknown_request_ids=sorted(set(groups)-set(ids)),
        capture_loss_observed=dropped_records > 0,
        admission_proved=False,
        engine_phase_proved=False,
        drain_or_unload_proved=False,
    )
