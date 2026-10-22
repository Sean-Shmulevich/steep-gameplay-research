"""Recovered radix branch traversal over supplied logical nodes.

Evidence: docs/reconstruction/CENTRAL_IMPULSE.md, Radix registry branch traversal.
This is an inspection representation, not an original object layout or allocator.
Lookup and cursor traversal are modeled; allocation and live ownership remain open.
"""


class UnsupportedRegistryNode(ValueError):
    """The node requires a native branch not yet represented by this API."""


def radix_type_registry_lookup(nodes, root, key):
    """Resolve a logical value through recovered radix branches.

    Nodes use native numeric kinds and logical child indices. Linear nodes have
    labels/children, bitmap nodes have eight groups of bitmap/children, and dense
    nodes have 256 children. Single-value nodes carry prefix/value. Prefix bits
    are supplied decoded metadata. Empty kinds return None. Unsupported kinds
    raise, distinct from a missing key. Structural bounds are authored safeguards.
    """
    if not isinstance(nodes, (list, tuple)) or not 1 <= len(nodes) <= 4096:
        raise ValueError('1..4096 supplied nodes required')
    if type(key) is not int or not 0 <= key < 2**64:
        raise ValueError('uint64 key required')
    node_index = root
    first = True
    seen = set()
    while True:
        if type(node_index) is not int or not 0 <= node_index < len(nodes):
            raise ValueError('child outside supplied nodes')
        if node_index in seen:
            raise ValueError('cyclic registry path')
        seen.add(node_index)
        node = nodes[node_index]
        kind = node['kind']
        if type(kind) is not int or not 0 <= kind <= 255:
            raise ValueError('byte node kind required')
        if 8 <= kind <= 14:
            return None
        if 36 <= kind <= 43 or 51 <= kind <= 59:
            return _multi_value_leaf(node, key)
        if 44 <= kind <= 50:
            prefix = _prefix(node)
            value = node['value']
            if type(value) is not int or not 0 <= value < 2**64:
                raise ValueError('uint64 logical value required')
            return value if (prefix ^ key) & ((1 << 56) - 1) == 0 else None
        if 15 <= kind <= 21:
            mode, shift = 'linear', 8 * (kind - 14)
        elif 22 <= kind <= 28:
            mode, shift = 'bitmap', 8 * (kind - 21)
        elif 29 <= kind <= 34:
            mode, shift = 'dense', 8 * (kind - 28)
        elif kind == 35 and first:
            mode, shift = 'dense', 56
        else:
            raise UnsupportedRegistryNode('unsupported radix node kind or placement: %d' % kind)
        first = False
        if shift < 48:
            mask = ((1 << 56) - 1) ^ ((1 << (shift + 8)) - 1)
            if (_prefix(node) ^ key) & mask:
                return None
        digit = (key >> shift) & 255
        if mode == 'linear':
            labels, children = node['labels'], node['children']
            if not 1 <= len(labels) <= 7 or len(labels) != len(children):
                raise ValueError('linear branch requires 1..7 labels and children')
            if any(type(x) is not int or not 0 <= x <= 255 for x in labels):
                raise ValueError('byte branch labels required')
            try:
                selected = labels.index(digit)
            except ValueError:
                return None
            node_index = children[selected]
        elif mode == 'bitmap':
            groups = node['groups']
            if len(groups) != 8:
                raise ValueError('eight bitmap groups required')
            group = groups[digit >> 5]
            bitmap, children = group['bitmap'], group['children']
            if type(bitmap) is not int or not 0 <= bitmap < 2**32:
                raise ValueError('uint32 child bitmap required')
            if len(children) != bitmap.bit_count():
                raise ValueError('bitmap population must match packed children')
            bit = 1 << (digit & 31)
            if not bitmap & bit:
                return None
            node_index = children[(bitmap & (bit - 1)).bit_count()]
        else:
            children = node['children']
            if len(children) != 256:
                raise ValueError('256 dense children required')
            node_index = children[digit]


def _prefix(node):
    prefix = node['prefix']
    if type(prefix) is not int or not 0 <= prefix < 2**56:
        raise ValueError('56-bit prefix metadata required')
    return prefix


def _multi_value_leaf(node, key):
    kind = node['kind']
    if kind == 43:
        if (_prefix(node) ^ key) & (((1 << 56) - 1) ^ 255):
            return None
        groups = node['groups']
        if len(groups) != 4:
            raise ValueError('four leaf bitmap groups required')
        digit = key & 255
        group = groups[digit >> 6]
        bitmap, values = group['bitmap'], group['values']
        if type(bitmap) is not int or not 0 <= bitmap < 2**64:
            raise ValueError('uint64 value bitmap required')
        if len(values) != bitmap.bit_count():
            raise ValueError('bitmap population must match packed values')
        _values(values)
        bit = 1 << (digit & 63)
        if not bitmap & bit:
            return None
        return values[(bitmap & (bit - 1)).bit_count()]
    if 36 <= kind <= 42:
        width = kind - 35
        maximum = (13, 51, 46, 42, 39, 36, 34)[width - 1]
        expected = None
        if (_prefix(node) ^ key) & (((1 << 56) - 1) ^ ((1 << (8 * width)) - 1)):
            return None
    elif 51 <= kind <= 56:
        width, expected = 1, kind - 49
        maximum = expected
    elif 57 <= kind <= 58:
        width, expected = 2, kind - 55
        maximum = expected
    else:  # kind 59, two inline 24-bit keys
        width, expected, maximum = 3, 2, 2
    keys, values = node['keys'], node['values']
    if not 1 <= len(keys) <= maximum or len(keys) != len(values):
        raise ValueError('leaf key/value count outside supported layout')
    if expected is not None and len(keys) != expected:
        raise ValueError('inline kind has a fixed key count')
    if any(type(k) is not int or not 0 <= k < 2**(8 * width) for k in keys):
        raise ValueError('key does not fit leaf width')
    if any(a > b for a, b in zip(keys, keys[1:])):
        raise ValueError('sorted leaf keys required')
    _values(values)
    index = _packed_key_index(keys, key & ((1 << (8 * width)) - 1), width)
    return None if index is None else values[index]


def _values(values):
    if any(type(v) is not int or not 0 <= v < 2**64 for v in values):
        raise ValueError('uint64 logical values required')


def _packed_key_index(keys, key, width):
    # Aligned-width helpers scan forwards. Packed-width helpers first test block
    # tails, then scan the selected tail backwards. This matters for duplicate
    # keys in synthetic nodes, even though insertion may require uniqueness.
    if width in (1, 2, 4):
        for i, candidate in enumerate(keys):
            if key <= candidate:
                return i if key == candidate else None
        return None
    threshold = {3: 40, 5: 24, 6: 20, 7: 16}[width]
    block = 4 if width == 6 else 8
    start, count = 0, len(keys)
    if count > threshold:
        if key <= keys[threshold - 1]:
            count = threshold
        else:
            start, count = threshold, count - threshold
    while count >= block:
        tail = start + block - 1
        if key == keys[tail]:
            return tail
        if key < keys[tail]:
            count = block - 1
            break
        start += block
        count -= block
    for i in range(start + count - 1, start - 1, -1):
        if key >= keys[i]:
            return i if key == keys[i] else None
    return None


def radix_leaf_cursor(node, key, *, advance=False):
    """Recovered first/next transition for one radix leaf with no parent stack.

    This is not complete tree iteration: exhaustion returns to a caller that must
    search ancestor siblings. Cursor writes and packed duplicate selection follow
    the local native paths. See CENTRAL_IMPULSE.md, Radix leaf cursor transitions.
    """
    kind = node['kind']
    if type(kind) is not int or not 36 <= kind <= 59:
        raise UnsupportedRegistryNode('a supported radix leaf is required')
    if type(advance) is not bool:
        raise ValueError('boolean advance required')
    exact = radix_type_registry_lookup([node],0,key)
    if not advance and exact is not None:
        return {'key':key,'value':exact}
    previous = key
    key = (key+1) & (2**64-1)
    if previous == 2**64-1:
        return {'key':key,'value':None}
    if 44 <= kind <= 50:
        prefix = _prefix(node)
        low = key & ((1<<56)-1)
        if prefix < low:
            return {'key':key,'value':None}
        if prefix > low:
            mask = (1 << (8*(kind-43))) - 1
            key = (key & ~mask) | (prefix & mask)
        return {'key':key,'value':node['value']}
    if kind == 43:
        width = 1
        leaf_keys, leaf_values = [], []
        for group_index, group in enumerate(node['groups']):
            values = iter(group['values'])
            for bit in range(64):
                if group['bitmap'] & (1<<bit):
                    leaf_keys.append(group_index*64+bit)
                    leaf_values.append(next(values))
        if not leaf_keys:
            raise ValueError('nonempty bitmap leaf required')
    else:
        width = kind-35 if kind <= 42 else 1 if kind <= 56 else 2 if kind <= 58 else 3
        leaf_keys, leaf_values = node['keys'], node['values']
    mask = (1 << (8*width))-1
    if kind <= 43:
        prefix_mask = ((1<<56)-1) ^ mask
        wanted_prefix, node_prefix = key & prefix_mask, _prefix(node) & prefix_mask
        if wanted_prefix > node_prefix:
            return {'key':key,'value':None}
        if wanted_prefix < node_prefix:
            key = (key & ~((1<<56)-1)) | node_prefix | leaf_keys[0]
            return {'key':key,'value':leaf_values[0]}
    suffix = key & mask
    index = _packed_key_index(leaf_keys,suffix,width)
    if index is None:
        index = next((i for i,k in enumerate(leaf_keys) if k > suffix),None)
    if index is None:
        return {'key':key,'value':None}
    return {'key':(key & ~mask)|leaf_keys[index],'value':leaf_values[index]}


def radix_type_registry_cursor(nodes, root, key, *, advance=False):
    """Recovered first/next traversal with ancestor sibling continuation.

    Returns key/value, preserving cursor writes. Logical recursion replaces the
    native ancestor stack. Invalid graphs and empty minimum subtrees raise.
    See CENTRAL_IMPULSE.md, Radix branch iteration and sibling continuation.
    """
    if type(advance) is not bool:
        raise ValueError('boolean advance required')
    if not isinstance(nodes,(list,tuple)) or not 1 <= len(nodes) <= 4096:
        raise ValueError('1..4096 supplied nodes required')
    if type(root) is not int or not 0 <= root < len(nodes):
        raise ValueError('root outside supplied nodes')
    if type(key) is not int or not 0 <= key < 2**64:
        raise ValueError('uint64 key required')
    if not advance:
        exact = radix_type_registry_lookup(nodes,root,key)
        if exact is not None:
            return {'key':key,'value':exact}
    previous = key
    query = (key+1) & (2**64-1)
    if previous == 2**64-1:
        return {'key':query,'value':None}

    def get(index, path):
        if type(index) is not int or not 0 <= index < len(nodes):
            raise ValueError('child outside supplied nodes')
        if index in path:
            raise ValueError('cyclic registry path')
        return nodes[index], path | {index}

    def minimum(index, cursor, path):
        node, path = get(index,path)
        kind = node['kind']
        if 36 <= kind <= 59:
            return _leaf_minimum(node,cursor)
        shift, mask, edges = _iterator_branch(nodes,node)
        if mask:
            cursor = (cursor & ~mask) | (_prefix(node) & mask)
        if not edges:
            raise ValueError('empty subtree has no minimum')
        digit, child = edges[0]
        cursor = (cursor & ~(255<<shift)) | (digit<<shift)
        return minimum(child,cursor,path)

    def seek(index, path, depth):
        node, path = get(index,path)
        kind = node['kind']
        if 36 <= kind <= 59:
            return radix_leaf_cursor(node,query-1,advance=True)
        shift, mask, edges = _iterator_branch(nodes,node)
        if mask:
            prefix = _prefix(node) & mask
            wanted = query & mask
            if wanted > prefix:
                return {'key':query,'value':None}
            if wanted < prefix:
                return minimum(index,query,path-{index})
        digit = (query>>shift)&255
        exact_attempted = False
        for selected, child in edges:
            if selected < digit:
                continue
            if selected == digit and not exact_attempted:
                exact_attempted = True
                # Native exact-child descent has seven ancestor slots.
                if depth >= 7:
                    raise ValueError('native iterator ancestor depth exceeded')
                found = seek(child,path,depth+1)
                if found['value'] is not None:
                    return found
                continue
            cursor = (query & ~(255<<shift)) | (selected<<shift)
            return minimum(child,cursor,path)
        return {'key':query,'value':None}

    return seek(root,set(),0)


def _iterator_branch(nodes,node):
    kind = node['kind']
    if 15 <= kind <= 21:
        shift = 8*(kind-14)
        labels, children = node['labels'],node['children']
        if not 1 <= len(labels) <= 7 or len(labels) != len(children):
            raise ValueError('linear branch requires 1..7 labels and children')
        if any(type(d) is not int or not 0 <= d < 256 for d in labels):
            raise ValueError('byte labels required')
        if any(a>b for a,b in zip(labels,labels[1:])):
            raise ValueError('iterator requires sorted branch labels')
        edges = list(zip(labels,children))
    elif 22 <= kind <= 28:
        shift = 8*(kind-21)
        if len(node['groups']) != 8:
            raise ValueError('eight bitmap groups required')
        edges = []
        for group_index,group in enumerate(node['groups']):
            bitmap,children = group['bitmap'],group['children']
            if type(bitmap) is not int or not 0 <= bitmap < 2**32 or len(children) != bitmap.bit_count():
                raise ValueError('invalid packed child bitmap')
            digits = [group_index*32+b for b in range(32) if bitmap&(1<<b)]
            edges.extend(zip(digits,children))
    elif 29 <= kind <= 35:
        shift = 8*(kind-28)
        if len(node['children']) != 256:
            raise ValueError('256 dense children required')
        edges=[]
        for digit,child in enumerate(node['children']):
            if type(child) is not int or not 0 <= child < len(nodes):
                raise ValueError('child outside supplied nodes')
            if not 8 <= nodes[child]['kind'] <= 14:
                edges.append((digit,child))
    else:
        raise UnsupportedRegistryNode('iterator requires a branch or leaf')
    mask = ((1<<56)-1)^((1<<(shift+8))-1) if shift<48 else 0
    return shift,mask,edges


def _leaf_minimum(node, cursor):
    kind = node['kind']
    if 44 <= kind <= 50:
        mask = (1<<(8*(kind-43)))-1
        return {'key':(cursor&~mask)|(_prefix(node)&mask),'value':node['value']}
    if kind == 43:
        for group_index,group in enumerate(node['groups']):
            if group['bitmap']:
                lowbit=(group['bitmap'] & -group['bitmap']).bit_length()-1
                digit=group_index*64+lowbit
                key=(cursor&~((1<<56)-1))|(_prefix(node)&~255)|digit
                return {'key':key,'value':group['values'][0]}
        raise ValueError('empty bitmap leaf has no minimum')
    width=kind-35 if kind<=42 else 1 if kind<=56 else 2 if kind<=58 else 3
    mask=(1<<(8*width))-1
    if kind<=42:
        prefix_mask=((1<<56)-1)^mask
        cursor=(cursor&~prefix_mask)|(_prefix(node)&prefix_mask)
    return {'key':(cursor&~mask)|node['keys'][0],'value':node['values'][0]}
