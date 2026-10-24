"""Local markup-query rules over caller-supplied graph records.

Evidence: CENTRAL_IMPULSE.md, Animation-interface markup query. These functions
neither acquire a graph nor generate its records/selector values. Integer float
bits preserve native comparison cases, including unordered NaNs.
"""
import struct


def _uint(value, bits):
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise ValueError('expected uint' + str(bits))
    return value


def candidate_eligible(record_key, start_bits, end_bits, query_key):
    """Original coarse key/interval gate; this does not evaluate a clip clock."""
    key = _uint(record_key, 32)
    query = _uint(query_key, 32)
    start = struct.unpack('<f', struct.pack('<I', _uint(start_bits, 32)))[0]
    end = struct.unpack('<f', struct.pack('<I', _uint(end_bits, 32)))[0]
    largest = struct.unpack('<f', bytes.fromhex('ffff7f7f'))[0]
    # Native COMISS/JA rejects strict greater only; unordered does not reject.
    return key == query and not start > largest and not 0.0 > end


def selector_matches(selector, values):
    """Post-collection rule over the uint32 second word of each pair.

    All-ones accepts even an empty collection. Zero requires every value to be
    zero, including the empty case. Other selectors require an exact match.
    The native collector still runs before the all-ones decision.
    """
    selector = _uint(selector, 32)
    values = [_uint(v, 32) for v in values]
    if selector == 0xffffffff:
        return True
    if selector == 0:
        return all(v == 0 for v in values)
    return selector in values


def query_markup(records, key, selector, collect_values):
    """Return first accepted record index or None, with external collection.

    Record shape: (key_u32, start_float_bits, end_float_bits, flags_u8).
    This interface follows the query packet's mode=2: record flag bit1 required.
    The collection callback runs once for each eligible flagged candidate, even
    for selector all-ones. Native allocation/destruction remains external.
    """
    key = _uint(key, 32)
    selector = _uint(selector, 32)
    records = list(records)
    if len(records) > 4096 or not callable(collect_values):
        raise ValueError('bounded records and a collection callback required')
    for i, (record_key, start, end, flags) in enumerate(records):
        eligible = candidate_eligible(record_key, start, end, key)
        flags = _uint(flags, 8)
        if eligible and flags & 2:
            if selector_matches(selector, collect_values(i)):
                return i
    return None


def query_markup_records(records, key, selector):
    """Inspect complete records through the observed null-context query route.

    Each record is (key, start_bits, end_bits, flags, pairs), where each pair
    contains two uint32 words. The native collector copies all pairs on this
    route; selection reads the second word. Record production remains external.
    The return is an inspection index, not the original boolean ABI.
    """
    rows = []
    values = []
    for record in records:
        if len(rows) >= 4096:
            raise ValueError('at most 4096 records required')
        record_key, start, end, flags, pairs = record
        words = []
        for pair in pairs:
            if len(words) >= 4096:
                raise ValueError('at most 4096 pairs per record required')
            first, second = pair
            _uint(first, 32)
            words.append(_uint(second, 32))
        rows.append((record_key, start, end, flags))
        values.append(words)
    return query_markup(rows, key, selector, values.__getitem__)
