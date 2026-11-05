"""Island-step action tree walk (stage C3) and its per-entry body wake callback.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Island action tree walk" (this pass),
RVAs 0x18b9710 (caller), 0x11fd350 (tree getter: provider+0xd0), 0x1959a70 (walk),
0x18b8c90 (callback), 0x1959c50 (node retirement, already reconstructed in
pose_body_tree), body table 0x29c99a8 slot 0x28 = 0x18be770 (quiet reset).

The tree is the same indexed red-black tree that body removal searches
(pose_body_tree.remove_pose_tree_body, key = body metadata+0x54). Descriptor: node
pointer +0, active +8, free +12, root +0x14, free head +0x18. Node (32 bytes): left +0,
right +4, parent +8, red +12, free +13, value +0x10, key +0x18.

Entry object (value) layout used by the walk: vtable +0 (slot 0 = deleting destructor
called with 1; slot 1 = update(dt)), body pointer +8, state dword +0x10 (2 = finished).
The update method is a dynamic virtual whose implementing class was not found in
unprotected code; it is always a supplied service. Our names are design names.

Memory is a PoseFlatMemory-like object (q/d/i/b/set_* and view). Services receive
addresses. Nothing here takes a lock: the callback's protected controller
synchronization (enter/leave at controller+0x50) is a supplied service.
"""
import struct

from .pose_body_tree import _Tree
from .pose_body_quiet_state import reset_pose_body_quiet_state

ACTION_TREE_OFFSET = 0xD0   # provider (= controller+0x20) + 0xd0, getter 0x11fd350
STATE_FINISHED = 2


def _successor(mem, nodes, index):
    """In-order successor exactly as 0x1959ae0..0x1959b45 computes it (before any call)."""
    right = mem.i(nodes + index * 32 + 4)
    if right != -1:
        nxt = right
        child = mem.i(nodes + nxt * 32)
        while child != -1:
            nxt = child
            child = mem.i(nodes + nxt * 32)
        return nxt
    current = index
    parent = mem.i(nodes + index * 32 + 8)
    while parent != -1:
        if current == mem.i(nodes + parent * 32):
            break
        current = parent
        parent = mem.i(nodes + parent * 32 + 8)
    return parent


def _leftmost(mem, nodes, index):
    child = mem.i(nodes + index * 32)
    while child != -1:
        index = child
        child = mem.i(nodes + index * 32)
    return index


def retire_action_node(mem, tree, index):
    """0x1959c50(tree, index) on flat memory, via the reconstructed pose_body_tree code."""
    nodes = mem.q(tree)
    count = mem.d(tree + 8) + mem.d(tree + 12)
    descriptor = mem.view(tree, 0x20)
    node_view = mem.view(nodes, max(count, index + 1) * 32)
    _Tree(descriptor, node_view).remove(index, key_size=4)


def walk_pose_action_tree(mem, tree, dt, *, callback, update, destroy, retire=None):
    """0x1959a70(tree, dt, callback): in-order walk with in-loop retirement.

    update(entry, dt)   - entry vtable slot 1 (+8), dynamic, supplied
    callback(body)      - argument is the entry's +8 qword, reloaded after update
    destroy(entry, 1)   - entry vtable slot 0, after retirement, only for state 2
    retire(tree, index) - defaults to retire_action_node (0x1959c50)

    Order per node (native): capture right/value and the successor index from the
    current node array; update; callback; reload state; if 2: retire then destroy.
    The node-array pointer is reloaded from the descriptor at every iteration.
    Returns the list of visited node indices (diagnostic only).
    """
    if retire is None:
        def retire(tree_address, node_index):
            retire_action_node(mem, tree_address, node_index)
    index = mem.i(tree + 0x14)
    if index == -1:
        return []
    index = _leftmost(mem, mem.q(tree), index)
    visited = []
    while index != -1:
        nodes = mem.q(tree)
        entry = mem.q(nodes + index * 32 + 0x10)
        nxt = _successor(mem, nodes, index)
        visited.append(index)
        update(entry, dt)
        callback(mem.q(entry + 8))
        if mem.d(entry + 0x10) == STATE_FINISHED:
            retire(tree, index)
            destroy(entry, 1)
        index = nxt
    return visited


def wake_action_body(mem, body, *, enter, leave, transition, reset=None):
    """0x18b8c90(body): the controller wrapper of 0x18b8380 with a body-derived controller.

    controller = body.metadata(+0x30).holder(+0x20).controller(+0x20); these three loads
    happen before the gates. Gates: metadata+0x52 bit0 set, or body+0x10 (group) null,
    return without effects. Otherwise enter(controller+0x50); transition(context, body)
    with context = controller+0x30 loaded after enter (0x18e14f0, see
    pose_group_update); reset(body) = body vtable slot 0x28 (0x18be770 for table
    0x29c99a8 by default); leave(controller+0x50).
    """
    metadata = mem.q(body + 0x30)
    controller = mem.q(mem.q(metadata + 0x20) + 0x20)
    if mem.b(metadata + 0x52) & 1:
        return False
    if mem.q(body + 0x10) == 0:
        return False
    enter(controller + 0x50)
    transition(mem.q(controller + 0x30), body)
    if reset is None:
        reset_body_quiet_state(mem, body)
    else:
        reset(body)
    leave(controller + 0x50)
    return True


def reset_body_quiet_state(mem, body):
    """Body table 0x29c99a8 slot 0x28 (0x18be770) on flat memory: metadata reloaded."""
    metadata = mem.q(body + 0x30)
    reset_pose_body_quiet_state(mem.view(body, 0x2c), mem.view(metadata, 0x54))


def run_island_action_stage(mem, provider, dt, *, update, destroy, enter, leave,
                            transition, reset=None, retire=None):
    """C3 as called by 0x18b9710: walk provider+0xd0 with 0x18b8c90 as callback."""
    return walk_pose_action_tree(
        mem, provider + ACTION_TREE_OFFSET, dt,
        callback=lambda body: wake_action_body(mem, body, enter=enter, leave=leave,
                                               transition=transition, reset=reset),
        update=update, destroy=destroy, retire=retire)
