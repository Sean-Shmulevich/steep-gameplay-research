"""Executable entity transform ordering with caller-supplied component services.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Entity transform notification lists
are captured separately. Python storage and failure cleanup are authored.
No native lock, pointer or lifetime guarantee is supplied. Accessor internals
remain caller-supplied services; only their dispatch gate is recovered here.
"""
from dataclasses import dataclass, field


@dataclass
class TransformEntity:
    transform: bytes
    components: list = field(default_factory=list)
    lock_owner: int | None = None
    lock_depth: int = 0
    pre_flag: int = 0
    post_flag: int = 0
    accessor_present: bool = False


def _check_accessor_services(present, flags, descriptor_valid, propagate):
    if present and flags & 1:
        if not callable(propagate) or (not flags & 4 and not callable(descriptor_valid)):
            raise NotImplementedError('accessor validity/propagation services required')


def dispatch_transform_accessor(entity, flags, *, descriptor_valid=None, propagate=None):
    """Recovered gate, called after entity transform copy.

    descriptor_valid(entity) is queried only when bit 2 is clear. Both services
    receive the current entity; propagate(entity, flags) owns opaque accessor
    behavior. It may inspect the copied transform. This supplies no native calls.
    """
    if type(flags) is not int or not 0 <= flags <= 0xffffffff:
        raise ValueError('uint32 packet flags required')
    _check_accessor_services(entity.accessor_present, flags, descriptor_valid, propagate)
    if entity.accessor_present and flags & 1:
        if flags & 4 or not descriptor_valid(entity):
            propagate(entity, flags)


def update_entity_transform(entity, transform, *, thread_id, notify, publish_cache,
                            flags=31, descriptor_valid=None, propagate=None):
    """Copy exactly 64 bytes between two independently captured callback passes.

    notify(phase, component, entity) and publish_cache(entity) are supplied
    services. notify may replace entity.components. Each pass retains its Python
    backing list and initial extent, but reads each element at dispatch time.
    This models observed traversal, not native reference retention. Callbacks
    must preserve captured backing extent. Optional accessor internals must be
    supplied explicitly. Packet flags are a uint32; default 31 matches the wrapper.
    A contended model lock raises instead of reproducing the native spin loop.
    Callback exceptions restore the model lock via authored finally cleanup;
    transform and callback side effects are not rolled back.
    """
    if not isinstance(entity, TransformEntity):
        raise TypeError('TransformEntity required')
    if type(transform) is not bytes or len(transform) != 64:
        raise ValueError('exactly 64 transform bytes required')
    if type(entity.transform) is not bytes or len(entity.transform) != 64:
        raise ValueError('exactly 64 existing transform bytes required')
    if type(flags) is not int or not 0 <= flags <= 0xffffffff:
        raise ValueError('uint32 packet flags required')
    _check_accessor_services(entity.accessor_present, flags, descriptor_valid, propagate)
    if type(thread_id) is not int or thread_id < 0:
        raise ValueError('nonnegative inspection thread token required')
    if type(entity.lock_depth) is not int or not 0 <= entity.lock_depth < 0xffffffff:
        raise ValueError('valid nonoverflowing lock depth required')
    if (entity.lock_depth == 0) != (entity.lock_owner is None):
        raise ValueError('inconsistent model lock state')
    if entity.lock_owner not in (None, thread_id):
        raise RuntimeError('model lock belongs to another thread')
    if not callable(notify) or not callable(publish_cache):
        raise TypeError('callback services required')

    def capture():
        if type(entity.components) is not list or len(entity.components) > 65535:
            raise ValueError('component storage must be a list with uint16 extent')
        return entity.components, len(entity.components)

    backing, count = capture()
    entity.lock_owner = thread_id
    entity.lock_depth += 1
    try:
        entity.pre_flag = 0
        for index in range(count):
            notify('pre', backing[index], entity)
        entity.transform = transform
        dispatch_transform_accessor(entity, flags, descriptor_valid=descriptor_valid,
                                    propagate=propagate)
        publish_cache(entity)
        entity.post_flag = 1
        backing, count = capture()
        for index in range(count):
            notify('post', backing[index], entity)
    finally:
        entity.lock_depth -= 1
        if entity.lock_depth == 0:
            entity.lock_owner = None
