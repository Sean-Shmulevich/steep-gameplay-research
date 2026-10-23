"""Authored interval correlation, not recovered command or scheduler policy.

See REQUEST_COMMAND_LIFECYCLE.md, Command-to-phase correlation.
Inputs must be copied after recorder close/drain. Caller supplies acquisition
provenance; this function cannot verify that provenance against a live process.
No addresses are emitted. Containment is not proof of call ancestry or safety.
"""


def correlate_command_phases(commands, phases, *, command_domain, phase_domain,
                             command_dropped=0, phase_dropped=0):
    """Match each invocation to enclosing phase intervals on the same thread.

    Domains require nonempty session_id and clock_id strings and a positive
    integer ticks_per_second. Both streams must come from the same acquisition
    session and clock. Phase indexes are record indexes, never persistent IDs.
    Repeated request IDs are preserved as separate deliveries. No nearest-frame
    fallback is used when a phase was lost or the capture windows differ.
    """
    def uint(v, positive=False):
        return type(v) is int and (1 if positive else 0) <= v < 2**64

    def domain(d):
        if not isinstance(d, dict) or any(
                not isinstance(d.get(k), str) or not d[k] for k in ('session_id', 'clock_id')):
            raise ValueError('session and clock identifiers required')
        if not uint(d.get('ticks_per_second'), True):
            raise ValueError('positive uint64 clock frequency required')
        return tuple(d[k] for k in ('session_id', 'clock_id', 'ticks_per_second'))

    if domain(command_domain) != domain(phase_domain):
        raise ValueError('capture sessions and clock domains must match')
    if not uint(command_dropped) or not uint(phase_dropped):
        raise ValueError('uint64 recorder drop counts required')
    commands, phases = list(commands), list(phases)
    for records, is_command in ((commands, True), (phases, False)):
        for r in records:
            if not isinstance(r, dict) or any(not uint(r.get(k)) for k in
                    ('thread', 'entry_tick', 'exit_tick')):
                raise ValueError('uint64 thread and interval fields required')
            if r['entry_tick'] > r['exit_tick']:
                raise ValueError('exit precedes entry')
            if is_command and not uint(r.get('result'), True):
                raise ValueError('positive request ID required')
    matches = []
    for i, cmd in enumerate(commands):
        enclosing = [j for j, phase in enumerate(phases)
                     if phase['entry_tick'] <= cmd['entry_tick'] and
                     cmd['exit_tick'] <= phase['exit_tick']]
        candidates = [j for j in enclosing if phases[j]['thread'] == cmd['thread']]
        status = 'unique_containment' if len(candidates) == 1 else (
            'ambiguous_containment' if candidates else 'not_matched')
        matches.append(dict(command_index=i, request_id=cmd['result'], status=status,
                            phase_indexes=candidates,
                            other_thread_enclosing_count=len(enclosing)-len(candidates)))
    return dict(matches=matches, command_records=len(commands), phase_records=len(phases),
                command_dropped=command_dropped, phase_dropped=phase_dropped,
                capture_loss_observed=bool(command_dropped or phase_dropped),
                call_ancestry_proved=False, admission_proved=False,
                native_phase_proved=False, lifetime_or_unload_proved=False)
