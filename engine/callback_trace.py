"""Pair bounded receiver-entry/return records without claiming job completion.

Records must be in recorder reservation order, with all receiver calls included.
Per-thread stacks support nesting. Capture loss makes pairing inconclusive.
"""


def pair_receiver_calls(records, *, dropped=0, incomplete=0):
    if any(type(n) is not int or n < 0 for n in (dropped, incomplete)):
        raise ValueError('nonnegative loss counts required')
    stacks, pairs, errors = {}, [], []
    for index, row in enumerate(records):
        if row['kind'] not in ('enter', 'return'):
            raise ValueError('receiver entry/return records required')
        for key in ('thread', 'tick', 'started', 'requested'):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError('nonnegative integer trace fields required')
        if type(row['target']) is not bool:
            raise ValueError('boolean receiver match required')
        stack = stacks.setdefault(row['thread'], [])
        if row['kind'] == 'enter':
            stack.append((index, row))
            continue
        if not stack:
            errors.append(dict(index=index, reason='return_without_entry'))
            continue
        entry_index, entry = stack.pop()
        if entry['target'] != row['target'] or row['tick'] < entry['tick']:
            errors.append(dict(index=index, reason='receiver_or_time_mismatch'))
            continue
        pairs.append(dict(entry_index=entry_index, return_index=index,
                          thread=row['thread'], target=row['target'],
                          duration_ticks=row['tick'] - entry['tick'],
                          request_unchanged=(entry['started'],entry['requested']) ==
                                            (row['started'],row['requested'])))
    pending = sum(len(stack) for stack in stacks.values())
    return dict(pairs=pairs, errors=errors, unmatched_entries=pending,
                pairing_complete=not (errors or pending or dropped or incomplete),
                dropped=dropped, incomplete=incomplete,
                job_completion_established=False, lifetime_established=False)
