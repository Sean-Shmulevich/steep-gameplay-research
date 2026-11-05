"""Island stage C5: changed-link attachment 0x18e2200 as one byte-level composition.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Changed-link attachment" (this pass).
RVAs: 0x18e2200 attach, 0x18e21a0 group merge, 0x1957d80 group absorb, 0x1957430
group link append. Bound reconstructed services (adapters over the existing dict
models): 0x18e11b0 finalize (pose_group_finalize), 0x19573c0 body append
(pose_body_membership.append_pose_body), 0x18e2660 context group removal
(pose_group_removal). Body removal 0x1957fc0 (pose_body_membership.remove_pose_body
plus constraint pruning and its link-clear service) stays a supplied service here.

Byte layout (evidence anchors, build specific):
  link    +0x08/+0x10 endpoints, +0x80 index in group link array, +0x84 flags (bit1 skips)
  body    +0x10 group, +0x1c index, +0x30 metadata (+0x50 word bit15, +0x53 kind nibble)
  group   +0x00 vtable (slot0 deleting destructor), +0x0c context index, +0x10/+0x18/+0x1c
          bodies ptr/count/capacity, +0x40/+0x48/+0x4c links, +0x90/+0x98/+0x9c poses,
          +0xa0 flag byte
  pose    +0x60 group, +0x68 index
  context +0x408/+0x410 special groups, +0x418/+0x428 group lists, +0x468 merge counter,
          +0x470 tracked bodies, +0x490/+0x498 pending links (cleared on attach entry)
Memory: PoseFlatMemory-like (q/d/w/b/set_*/view). Growth/allocation are services.
"""
import struct

from .pose_group_finalize import finalize_pose_group
from .pose_body_membership import append_pose_body
from .pose_group_removal import remove_pose_group
from .pose_island_action_tree import reset_body_quiet_state

POSE_ARRAY_TAG = 0x37


class _Qwords:
    """Live qword list over flat memory (pointer, element count)."""

    def __init__(self, mem, pointer, length):
        self.mem, self.pointer, self.length = mem, pointer, length

    def __len__(self):
        return self.length

    def __getitem__(self, i):
        if not 0 <= i < self.length:
            raise IndexError(i)
        return self.mem.q(self.pointer + 8 * i)

    def __setitem__(self, i, value):
        if not 0 <= i < self.length:
            raise IndexError(i)
        self.mem.set_q(self.pointer + 8 * i, value)


def _array(mem, at, length=None):
    count, capacity = mem.d(at + 8), mem.d(at + 12)
    return dict(count=count, capacity=capacity,
                slots=_Qwords(mem, mem.q(at), capacity if length is None else length))


def _store_array(mem, at, array):
    mem.set_d(at + 8, array['count'])
    mem.set_d(at + 12, array['capacity'])


class _LazyGroups(dict):
    """Group dicts created on first access (token, index +0xc), so only touched groups load."""

    def __init__(self, mem):
        super().__init__()
        self.mem = mem

    def __missing__(self, token):
        value = dict(token=token, index=self.mem.d(token + 0xc))
        self[token] = value
        return value


# ---------------------------------------------------------------- bound services

def finalize_group_bytes(mem, context, group, *, virtual40=None, grow=None):
    """0x18e11b0 on flat memory through pose_group_finalize.finalize_pose_group.

    virtual40 defaults to body table 0x29c99a8 slot 0x28 (quiet reset). grow is the
    capacity service grow(array_dict, capacity); it must update the dict's
    capacity/slots and the backing memory (fixtures that never grow may pass None).
    """
    names = (('groups418', 0x418), ('groups428', 0x428), ('tracked', 0x470),
             ('pending_links', 0x490))
    ctx = {name: _array(mem, context + off) for name, off in names}
    ctx['group408'], ctx['group410'] = mem.q(context + 0x408), mem.q(context + 0x410)
    groups = _LazyGroups(mem)
    g = groups[group]
    g.update(flag_a0=mem.b(group + 0xa0), count=mem.d(group + 0x18),
             slots=_Qwords(mem, mem.q(group + 0x10), mem.d(group + 0x18)),
             link_count=mem.d(group + 0x48),
             link_slots=_Qwords(mem, mem.q(group + 0x40), mem.d(group + 0x48)))

    class _Bodies(dict):
        def __missing__(self, token):
            meta = mem.q(token + 0x30)
            value = dict(token=token, metadata=dict(kind8=mem.b(meta + 0x53)))
            self[token] = value
            return value

    class _Links(dict):
        def __missing__(self, token):
            value = dict(first=mem.q(token + 8))
            self[token] = value
            return value

    def v40(body):
        (virtual40 or (lambda t: reset_body_quiet_state(mem, t)))(body['token'])

    def grow_dict(array, capacity):
        if grow is None:
            raise ValueError('Growth service required by this fixture')
        grow(array, capacity)

    done = finalize_pose_group(ctx, g, groups=groups, bodies=_Bodies(), links=_Links(),
                               virtual40=v40, grow=grow_dict)
    if done:
        for name, off in names:
            _store_array(mem, context + off, ctx[name])
        for t, record in groups.items():
            mem.set_d(t + 0xc, record['index'])
        mem.set_b(group + 0xa0, g['flag_a0'])
    return done


def append_body_bytes(mem, group, body, *, grow):
    """0x19573c0 on flat memory through pose_body_membership.append_pose_body."""
    g = dict(token=group, count=mem.d(group + 0x18), capacity=mem.d(group + 0x1c))
    g['slots'] = _Qwords(mem, mem.q(group + 0x10), g['capacity'])
    b = dict(token=body, flags16=mem.w(mem.q(body + 0x30) + 0x50),
             group=mem.q(body + 0x10), index=mem.d(body + 0x1c))

    def grow_dict(record, capacity):
        mem.set_q(body + 0x10, b['group'])
        mem.set_d(body + 0x1c, b['index'])
        grow(group + 0x10, capacity)
        record['capacity'] = mem.d(group + 0x1c)
        record['count'] = mem.d(group + 0x18)
        record['slots'] = _Qwords(mem, mem.q(group + 0x10), record['capacity'])

    ok = append_pose_body(g, b, grow=grow_dict)
    if ok:
        mem.set_q(body + 0x10, b['group'])
        mem.set_d(body + 0x1c, b['index'])
        mem.set_d(group + 0x18, g['count'])
    return ok


def remove_group_bytes(mem, context, group):
    """0x18e2660 on flat memory through pose_group_removal.remove_pose_group."""
    flag = mem.b(group + 0xa0)
    at = context + (0x428 if flag else 0x418)
    array = _array(mem, at)
    name = 'groups428' if flag else 'groups418'
    groups = _LazyGroups(mem)
    groups[group].update(flag_a0=flag)
    remove_pose_group({name: array}, groups[group], groups=groups)
    mem.set_d(at + 8, array['count'])
    for t, record in groups.items():
        if t != group:
            mem.set_d(t + 0xc, record['index'])


# ------------------------------------------------------- recovered in this pass

def append_group_link(mem, group, link, *, grow_links):
    """0x1957430: link+0x80 = count before growth; grow on count == capacity (cap*2)."""
    mem.set_d(link + 0x80, mem.d(group + 0x48))
    capacity = mem.d(group + 0x4c)
    if mem.d(group + 0x48) == capacity:
        grow_links(group + 0x40, (capacity * 2) & 0xFFFFFFFF)
    count = mem.d(group + 0x48)
    mem.set_q(mem.q(group + 0x40) + 8 * count, link)
    mem.set_d(group + 0x48, count + 1)


def _grow_doubling(needed, capacity):
    if capacity == 0:
        raise ValueError('Native doubling from zero capacity never terminates')
    while needed > capacity:
        capacity = (capacity * 2) & 0xFFFFFFFF
        if capacity == 0:
            raise ValueError('Native capacity doubling wrapped')
    return capacity


def absorb_island_group(mem, destination, source, *, grow_bodies, grow_links, allocator,
                        copy=None):
    """0x1957d80(destination, source): append bodies, links and poses, then zero source counts.

    grow_bodies(descriptor, capacity) = 0x19582a0 on destination+0x10, grow_links = 0x1958380
    on destination+0x40, both only when needed > capacity (doubling, never from zero).
    Poses (+0x90) grow inline through allocator(alloc/realloc/free) with tag 0x37 and
    alignment 0x10: capacity doubles from nonzero, or becomes exactly `needed` from zero.
    Each copied element is then renumbered: bodies +0x1c index and +0x10 group, links +0x80
    index only, poses +0x68 index and +0x60 group. copy(dst, src, size) = 0x1c6afb0.
    """
    copy = copy or (lambda dst, src, size: mem.view(dst, size).__setitem__(
        slice(0, size), mem.view(src, size).tobytes()) if size else None)

    def section(array, count_off, grow, renumber):
        old = mem.d(destination + count_off)
        needed = (mem.d(source + count_off) + old) & 0xFFFFFFFF
        capacity = mem.d(destination + count_off + 4)
        if needed > capacity:
            grow(destination + array, _grow_doubling(needed, capacity))
        mem.set_d(destination + count_off, needed)
        size = mem.d(source + count_off) * 8
        copy(mem.q(destination + array) + old * 8, mem.q(source + array), size)
        end = mem.d(destination + count_off)
        for i in range(old, end):
            renumber(mem.q(mem.q(destination + array) + 8 * i), i)

    def body(element, i):
        mem.set_d(element + 0x1c, i)
        mem.set_q(element + 0x10, destination)

    section(0x10, 0x18, grow_bodies, body)
    section(0x40, 0x48, grow_links, lambda element, i: mem.set_d(element + 0x80, i))

    old = mem.d(destination + 0x98)
    needed = (mem.d(source + 0x98) + old) & 0xFFFFFFFF
    capacity = mem.d(destination + 0x9c)
    if needed > capacity:
        new = needed if capacity == 0 else _grow_doubling(needed, capacity)
        if new != capacity:
            pointer = mem.q(destination + 0x90)
            if pointer:
                if new:
                    pointer = allocator.reallocate(pointer, new * 8, 0x10, POSE_ARRAY_TAG)
                else:
                    allocator.release(pointer)
                    pointer = 0
            else:
                pointer = allocator.allocate(new * 8, 0x10, POSE_ARRAY_TAG)
            mem.set_q(destination + 0x90, pointer)
            mem.set_d(destination + 0x9c, new)
            if mem.d(destination + 0x98) > new:
                mem.set_d(destination + 0x98, new)
    mem.set_d(destination + 0x98, needed)
    size = mem.d(source + 0x98) * 8
    copy(mem.q(destination + 0x90) + old * 8, mem.q(source + 0x90), size)
    end = mem.d(destination + 0x98)
    for i in range(old, end):
        element = mem.q(mem.q(destination + 0x90) + 8 * i)
        mem.set_d(element + 0x68, i)
        mem.set_q(element + 0x60, destination)
    mem.set_d(source + 0x18, 0)
    mem.set_d(source + 0x48, 0)
    mem.set_d(source + 0x98, 0)


def merge_island_groups(mem, context, first, second, *, absorb, remove_group, destroy):
    """0x18e21a0: the group with more bodies absorbs the other (ties keep `first`).

    absorb(destination, source); context+0x468 += 1; remove_group(context, source);
    destroy(source, 1) through its vtable slot 0 when source is nonnull.
    """
    if mem.d(second + 0x18) > mem.d(first + 0x18):
        destination, source = second, first
    else:
        destination, source = first, second
    absorb(destination, source)
    mem.set_d(context + 0x468, mem.d(context + 0x468) + 1)
    remove_group(context, source)
    if source:
        destroy(source, 1)
    return destination


def attach_changed_links(mem, context, links, count, *, finalize, remove_body,
                         append_body, merge, append_link):
    """0x18e2200(context, links, count).

    Clears pending count +0x498 first, then for each captured link slot (count captured):
    flags+0x84 bit1 skips the link entirely. Otherwise capture both endpoint groups,
    finalize(context, g1) then finalize(context, g2). If the *captured* groups differ:
    reload metadata of body1 then both groups; when both bodies' metadata+0x50 bit15 is
    set: if g1 == context+0x410 move body1 into g2; elif g2 == +0x410 move body2 into g1;
    else merge(context, g1, g2). Always: append_link(body1.group reloaded, link).
    """
    mem.set_d(context + 0x498, 0)
    for k in range(count & 0xFFFFFFFF):
        link = mem.q(links + 8 * k)
        if mem.b(link + 0x84) & 2:
            continue
        body1, body2 = mem.q(link + 8), mem.q(link + 0x10)
        group1, group2 = mem.q(body1 + 0x10), mem.q(body2 + 0x10)
        finalize(context, group1)
        finalize(context, group2)
        if group1 != group2:
            meta1 = mem.q(body1 + 0x30)
            group1, group2 = mem.q(body1 + 0x10), mem.q(body2 + 0x10)
            if mem.w(meta1 + 0x50) & 0x8000 and mem.w(mem.q(body2 + 0x30) + 0x50) & 0x8000:
                special = mem.q(context + 0x410)
                if group1 == special:
                    remove_body(group1, body1)
                    append_body(group2, body1)
                elif group2 == special:
                    remove_body(group2, body2)
                    append_body(group1, body2)
                else:
                    merge(context, group1, group2)
        append_link(mem.q(body1 + 0x10), link)


def bind_island_attach(mem, *, remove_body, grow_bodies, grow_links, grow_arrays,
                       allocator, destroy_group, virtual40=None, copy=None):
    """Return attach(context, links, count) with every recovered callee bound.

    Supplied: remove_body (0x1957fc0), growth services, allocator, group destructor.
    """
    def absorb(destination, source):
        absorb_island_group(mem, destination, source, grow_bodies=grow_bodies,
                            grow_links=grow_links, allocator=allocator, copy=copy)

    def attach(context, links, count):
        attach_changed_links(
            mem, context, links, count,
            finalize=lambda c, g: finalize_group_bytes(mem, c, g, virtual40=virtual40,
                                                       grow=grow_arrays),
            remove_body=remove_body,
            append_body=lambda g, b: append_body_bytes(mem, g, b, grow=grow_bodies),
            merge=lambda c, a, b: merge_island_groups(
                mem, c, a, b, absorb=absorb,
                remove_group=lambda cc, g: remove_group_bytes(mem, cc, g),
                destroy=destroy_group),
            append_link=lambda g, l: append_group_link(mem, g, l, grow_links=grow_links))
    return attach


def publish_pending_links(mem, owner, publish):
    """C6 loop of 0x18b9710 on flat memory (same rule as pose_update_stage).

    Pending span = context(owner+0x30)+0x490/+0x498 captured once; each slot and the
    interface owner+0x28 are read when reached; null publishes null, else link+8.
    """
    context = mem.q(owner + 0x30)
    start, count = mem.q(context + 0x490), mem.d(context + 0x498)
    for k in range(count):
        link = mem.q(start + 8 * k)
        publish(mem.q(owner + 0x28), (link + 8) & 0xFFFFFFFFFFFFFFFF if link else 0)


# ------------------------------------------- broadphase receivers (table 0x29ca8a0)

PAIR_RECORD_TAG = 0x1C


def reserve_pair_records(mem, descriptor, capacity, *, allocator):
    """0x1940990: 24-byte record vector reserve (tag 0x1c, align 0x10); count clamped."""
    if capacity == mem.d(descriptor + 12):
        return
    pointer = mem.q(descriptor)
    if pointer:
        if capacity:
            pointer = allocator.reallocate(pointer, (capacity * 24) & 0xFFFFFFFF, 0x10,
                                           PAIR_RECORD_TAG)
        else:
            allocator.release(pointer)
            pointer = 0
    else:
        pointer = allocator.allocate((capacity * 24) & 0xFFFFFFFF, 0x10, PAIR_RECORD_TAG)
    mem.set_q(descriptor, pointer)
    mem.set_d(descriptor + 12, capacity)
    if mem.d(descriptor + 8) > capacity:
        mem.set_d(descriptor + 8, capacity)


def append_broadphase_pair(mem, broadphase, record, *, grow):
    """Slot +0x98 = 0x199b590 for the dynamic-tree broadphase: copy 24 bytes from
    `record` (link+8: both endpoints and the following qword) into the current
    new-pair vector at broadphase+0xf8 (the vector the pair update reads through
    slots +0x40/+0x48). grow(descriptor, capacity) = 0x1940990 when count == capacity
    (initial 8, else doubled). A null record faults natively (no guard)."""
    vector = mem.q(broadphase + 0xf8)
    capacity = mem.d(vector + 12)
    if mem.d(vector + 8) == capacity:
        grow(vector, (capacity * 2) & 0xFFFFFFFF if capacity else 8)
    count = mem.d(vector + 8)
    data = mem.view(record, 24).tobytes()
    mem.view(mem.q(vector) + 24 * count, 24)[:] = data
    mem.set_d(vector + 8, count + 1)


def mark_broadphase_active(mem, broadphase, argument):
    """Slot +0xa8 = 0x193fa10: byte +0x49 |= 1 + (low byte of argument != 0)."""
    mem.set_b(broadphase + 0x49, mem.b(broadphase + 0x49) | (2 if argument & 0xFF else 1))
