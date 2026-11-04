"""Pair link filter: the accept/reject gate run on every pair link by the pair worker.

Evidence: native routine RVA 0x18deb70 (leaf apart from indirect calls), called from
the dynamic pair handler 0x18df770 as `filter(owner.provider, link)`. See
docs/reconstruction/LINK_SOLVER.md, "Pair link worker" and "Pair link filter".

Recovered behavior: up to five optional predicate function pointers are called
with the link as the only argument (only the low byte of each result counts). The
first false result rejects. Pointer sources, in call order:

1. provider+0x188 (provider-wide predicate)
2. link.first -> +0x30 (kind record) -> +0x20 -> +0x70   (per-kind predicate A)
3. link.second -> same path (per-kind predicate B), skipped when B == A
4. link.first -> +0xA0 (per-body predicate C)
5. link.second -> +0xA0 (per-body predicate D), skipped when D == C

The link's body pointers are reread before each step (a predicate may edit the link).
A null pointer (or a null intermediate record in path 2/3) is skipped. The dedup
compares the pointer values only: B is compared with A even when A is null, which
never matters because a null B is skipped first.

Authored: the `invoke` service (the predicates are game code reached through
function pointers; a caller supplies an address -> callable mapping). Offsets are
evidence anchors, not portable API fields.
"""

PROVIDER_PREDICATE = 0x188
KIND_RECORD = 0x30
KIND_EXTENSION = 0x20
EXTENSION_PREDICATE = 0x70
BODY_PREDICATE = 0xA0


def _kind_predicate(mem, body):
    extension = mem.q(mem.q(body + KIND_RECORD) + KIND_EXTENSION)
    return mem.q(extension + EXTENSION_PREDICATE) if extension else 0


def filter_pose_pair_link(mem, provider, link, *, invoke):
    """0x18deb70. invoke(address, link) returns the callee's rax; only al is tested."""
    def passes(address):
        return bool(invoke(address, link) & 0xFF)

    predicate = mem.q(provider + PROVIDER_PREDICATE)
    if predicate and not passes(predicate):
        return False
    kind_a = _kind_predicate(mem, mem.q(link + 8))
    if kind_a and not passes(kind_a):
        return False
    kind_b = _kind_predicate(mem, mem.q(link + 0x10))
    if kind_b and kind_b != kind_a and not passes(kind_b):
        return False
    body_c = mem.q(mem.q(link + 8) + BODY_PREDICATE)
    if body_c and not passes(body_c):
        return False
    body_d = mem.q(mem.q(link + 0x10) + BODY_PREDICATE)
    if body_d and body_d != body_c and not passes(body_d):
        return False
    return True
