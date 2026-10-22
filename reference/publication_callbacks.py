"""Recovered callback-category filtering around the publication handoff.

Evidence: CENTRAL_IMPULSE.md, Callback phases around publication readiness.
This is an immutable invocation plan. Callback side effects and dynamic registry
mutation are not modeled.
"""


def plan_publication_callbacks(categories, skip_mask):
    if type(skip_mask) is not int or not 0 <= skip_mask < 2**32:
        raise ValueError('uint32 skip mask required')
    calls = []
    for index, category in enumerate(categories):
        flags = category['flags']
        if type(flags) is not int or not 0 <= flags < 2**32:
            raise ValueError('uint32 category flags required')
        if flags & skip_mask:
            continue
        for entry in reversed(category['entries']):
            obj, tag = entry['object'], entry['tag']
            if type(obj) is not int or not 0 <= obj < 2**64:
                raise ValueError('uint64 logical object required')
            if type(tag) is not int or not 0 <= tag < 2**32:
                raise ValueError('uint32 tag required')
            if obj:
                calls.append(dict(category=index, object=obj, tag=tag, callback='primary'))
                if entry['secondary']:
                    calls.append(dict(category=index, object=obj, tag=tag, callback='secondary'))
    return calls
