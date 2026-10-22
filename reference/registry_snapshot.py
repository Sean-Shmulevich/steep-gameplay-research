"""Bounded decoding of supplied registry memory into logical inspection nodes.

Recovered layout: CENTRAL_IMPULSE.md, Bounded registry snapshot decoder.
The caller owns stable reads and value identity. No process access is built in.
"""
from reference.type_registry import radix_type_registry_lookup, UnsupportedRegistryNode
from reference.ground_response_pose import compact_type_registry_index

# Each pair is (inclusive key-count ceiling, value-array start in 8-byte words).
# These describe recovered layout decisions, not dumped game objects.
_VALUE_STARTS = (
    ((6,1),(13,2)),
    ((4,1),(5,2),(12,3),(18,5),(25,7),(37,10),(51,13)),
    ((2,1),(5,2),(8,3),(10,4),(16,6),(23,9),(34,13),(46,18)),
    ((2,1),(4,2),(7,4),(10,5),(15,8),(21,11),(31,16),(42,21)),
    ((3,2),(4,3),(6,4),(9,6),(14,9),(19,12),(28,18),(39,25)),
    ((1,1),(4,3),(6,5),(8,6),(13,10),(18,14),(26,20),(36,27)),
    ((1,1),(3,3),(5,5),(8,7),(12,11),(17,15),(25,22),(34,30)),
    ((1,2),(2,3),(3,4),(5,6),(7,8),(11,12),(15,16),(23,24),(31,32)),
)


def _value_start(width, count):
    if count < 1:
        raise ValueError('nonempty key array required')
    for ceiling, words in _VALUE_STARTS[width-1]:
        if count <= ceiling:
            return 8 * words
    raise ValueError('key count exceeds recovered layout')


def decode_type_registry(read, tagged_root, resolve_value, *, max_nodes=4096,
                         max_bytes=1048576, resolve_slot=None):
    """Decode compact/null/tree roots using read(address,size) and value mapping.

    resolve_value(raw_uint64) must return a uint64 logical identity. Both callbacks
    are caller supplied. Reads must belong to one stable snapshot; this routine
    does not make sequential live reads atomic or pin object lifetime. It never
    writes memory. Limits and malformed-data rejection are authored safeguards.
    Optional resolve_slot(raw,address) replaces resolve_value and retains explicit
    slot identity for inspection adapters; it does not pin or validate lifetime.
    """
    if type(tagged_root) is not int or not 0 <= tagged_root < 2**64:
        raise ValueError('uint64 tagged root required')
    if type(max_nodes) is not int or not 1 <= max_nodes <= 4096:
        raise ValueError('node budget must be 1..4096')
    if type(max_bytes) is not int or not 1 <= max_bytes <= 1048576:
        raise ValueError('read budget must be 1..1048576')
    used = calls = 0

    def take(address, size):
        nonlocal used, calls
        if not 0 < address < 2**64 or size < 0 or address + size > 2**64:
            raise ValueError('invalid read range')
        if used + size > max_bytes:
            raise ValueError('registry read budget exceeded')
        if size == 0:
            return b''
        used += size
        calls += 1
        data = read(address, size)
        if not isinstance(data, (bytes, bytearray, memoryview)) or len(data) != size:
            raise ValueError('registry read must return exactly the requested bytes')
        return bytes(data)

    def words(data, width=8):
        return [int.from_bytes(data[i:i+width], 'little') for i in range(0,len(data),width)]

    def value(raw, address):
        logical = resolve_value(raw) if resolve_slot is None else resolve_slot(raw,address)
        if type(logical) is not int or not 0 <= logical < 2**64:
            raise ValueError('value resolver must return a uint64 logical identity')
        return logical

    def values(address, count):
        return [value(raw,address+8*i) for i,raw in enumerate(words(take(address,8*count)))] if count else []

    def keys(address, count, width):
        result = words(take(address,count*width), width)
        if any(a>b for a,b in zip(result,result[1:])):
            raise ValueError('unsorted registry keys')
        return result

    def finish(result):
        return {**result,'read_calls':calls,'bytes_read':used}

    if tagged_root == 0:
        return finish({'representation':'null'})
    tag = tagged_root & 7
    base = tagged_root & ~7
    if tag == 1:
        count = words(take(base,8))[0] + 1
        offset = _value_start(8,count)
        return finish({'representation':'compact','keys':keys(base+8,count,8),
                       'values':values(base+offset,count)})
    if tag != 3:
        raise UnsupportedRegistryNode('unsupported registry root tag')
    addresses, indices, nodes = [], {}, []

    def child(address):
        if address not in indices:
            if len(addresses) >= max_nodes:
                raise ValueError('registry node budget exceeded')
            indices[address] = len(addresses)
            addresses.append(address)
        return indices[address]

    child(base+8)
    current = 0
    while current < len(addresses):
        address = addresses[current]
        raw = take(address,16)
        pointer, metadata = words(raw)
        kind, prefix = raw[15], metadata & ((1<<56)-1)
        storage = pointer & ~7
        node = {'kind':kind}
        if 8 <= kind <= 14:
            pass
        elif 44 <= kind <= 50:
            node.update(prefix=prefix,value=value(pointer,address))
        elif 15 <= kind <= 21:
            header = take(storage,8)
            count = header[0]
            if not 1 <= count <= 7:
                raise ValueError('linear node count outside recovered header')
            node.update(prefix=prefix,labels=list(header[1:count+1]),
                        children=[child(storage+8+16*i) for i in range(count)])
        elif 22 <= kind <= 28 or kind == 43:
            branch = kind != 43
            group_count, bit_width = (8,32) if branch else (4,64)
            raw_groups = take(storage,16*group_count)
            groups = []
            for i in range(group_count):
                bitmap = int.from_bytes(raw_groups[16*i:16*i+bit_width//8],'little')
                packed = int.from_bytes(raw_groups[16*i+8:16*i+16],'little') & ~7
                count = bitmap.bit_count()
                group = {'bitmap':bitmap}
                if branch:
                    group['children'] = [child(packed+16*j) for j in range(count)]
                else:
                    group['values'] = values(packed,count)
                groups.append(group)
            node.update(prefix=prefix,groups=groups)
        elif 29 <= kind <= 34 or kind == 35 and current == 0:
            node.update(prefix=prefix,children=[child(storage+16*i) for i in range(256)])
        elif 36 <= kind <= 42:
            width, count = kind-35, raw[8]+1
            offset = _value_start(width,count)
            node.update(prefix=prefix,keys=keys(storage,count,width),
                        values=values(storage+offset,count))
        elif 51 <= kind <= 59:
            width = 1 if kind <= 56 else 2 if kind <= 58 else 3
            count = kind-49 if width == 1 else kind-55 if width == 2 else 2
            node.update(keys=keys(address+8,count,width),values=values(storage,count))
        else:
            raise UnsupportedRegistryNode('unsupported radix node kind or placement: %d' % kind)
        nodes.append(node)
        current += 1
    return finish({'representation':'radix','root':0,'nodes':nodes})


def decoded_type_registry_lookup(snapshot, key):
    """Look up a uint64 key in a decoded inspection snapshot."""
    representation = snapshot['representation']
    if representation == 'radix':
        return radix_type_registry_lookup(snapshot['nodes'],snapshot['root'],key)
    if representation == 'null':
        compact_type_registry_index(None,key)
        return None
    if representation != 'compact':
        raise ValueError('unknown decoded registry representation')
    index = compact_type_registry_index(snapshot['keys'],key)
    if len(snapshot['keys']) != len(snapshot['values']):
        raise ValueError('one value per compact key required')
    return None if index is None else snapshot['values'][index]



def decoded_type_registry_cursor(snapshot, key, *, advance=False):
    """Recovered first/next transition on a decoded registry; no process reads.

    Stop on value None. Maximum-key exhaustion wraps the cursor to zero, so a
    subsequent next call is not a persistent end marker. See registry contract.
    """
    from reference.type_registry import radix_type_registry_cursor
    from reference.ground_response_pose import compact_type_registry_cursor
    representation = snapshot['representation']
    if representation == 'radix':
        return radix_type_registry_cursor(snapshot['nodes'],snapshot['root'],key,advance=advance)
    if representation == 'null':
        cursor = compact_type_registry_cursor(None,key,advance=advance)
        return {'key':cursor['key'],'value':None}
    if representation != 'compact':
        raise ValueError('unknown decoded registry representation')
    if len(snapshot['keys']) != len(snapshot['values']):
        raise ValueError('one value per compact key required')
    cursor = compact_type_registry_cursor(snapshot['keys'],key,advance=advance)
    value = None if cursor['index'] is None else snapshot['values'][cursor['index']]
    return {'key':cursor['key'],'value':value}


def link_decoded_type_registry(snapshot, parent_keys, previous_parents, *, max_entries=4096):
    """Recovered parent-link pass using one decoded registry for both services.

    Registry values identify supplied descriptors. Missing parent keys preserve
    prior links; unregistered descriptors are untouched. Entry bounds and strictly
    increasing iteration keys are authored snapshot safeguards. No input mutation
    or native write occurs, including when validation raises.
    """
    from reference.ground_response_pose import link_type_parents
    if type(max_entries) is not int or not 1 <= max_entries <= 65536:
        raise ValueError('entry budget must be 1..65536')
    parents = link_type_parents(parent_keys,previous_parents,lambda key:None)
    visited_descriptors, visited_keys = [], []
    cursor = decoded_type_registry_cursor(snapshot,0)
    while cursor['value'] is not None:
        if len(visited_keys) >= max_entries:
            raise ValueError('registry entry budget exceeded')
        descriptor = cursor['value']
        if type(descriptor) is not int or not 0 <= descriptor < len(parents):
            raise ValueError('registry value outside supplied descriptors')
        if visited_keys and cursor['key'] <= visited_keys[-1]:
            raise ValueError('registry cursor did not advance monotonically')
        visited_descriptors.append(descriptor)
        visited_keys.append(cursor['key'])
        parent = decoded_type_registry_lookup(snapshot,parent_keys[descriptor])
        if parent is not None:
            if type(parent) is not int or not 0 <= parent < len(parents):
                raise ValueError('parent lookup outside supplied descriptors')
            parents[descriptor] = parent
        cursor = decoded_type_registry_cursor(snapshot,cursor['key'],advance=True)
    return {'parents':parents,'visited_descriptors':visited_descriptors,
            'visited_keys':visited_keys,'cursor_key':cursor['key']}


def dispatch_type_registration_callbacks(read_count, read_entry, invoke, *, max_calls=4096):
    """Recovered dynamic callback-list dispatch, with supplied callback bodies.

    read_count() supplies the current uint16 count. read_entry(index) resolves the
    current array and returns an entry with a uint64 'context' field. invoke(entry,
    context & ~3) supplies the body. The next count/entry is read after it returns.
    This models call order only, not native callback bodies or safe live mutation.
    """
    if type(max_calls) is not int or not 1 <= max_calls <= 65535:
        raise ValueError('callback budget must be 1..65535')
    index = 0
    while True:
        count = read_count()
        if type(count) is not int or not 0 <= count <= 65535:
            raise ValueError('uint16 callback count required')
        if index >= count:
            return index
        if index >= max_calls:
            raise ValueError('registration callback budget exceeded')
        entry = read_entry(index)
        context = entry['context']
        if type(context) is not int or not 0 <= context < 2**64:
            raise ValueError('uint64 callback context required')
        invoke(entry,context & ~3)
        index += 1
