"""Registered skeleton-pose acquisition and pooled wrapper initialization.

Evidence: CENTRAL_IMPULSE.md, Concrete skeleton-pose acquisition.
Object resolution, wrapper storage and bank allocation remain explicit services.
"""


def initialize_acquired_pose(wrapper, component, selection_mask, mode):
    if wrapper is None:
        return None
    wrapper.update(component=component,primary=None,alternate=None,
                   storage='own_inline_scratch',header=0x8004,
                   index=int(selection_mask)&65535,
                   flags=(wrapper['flags'] & 0xfc) | (int(mode)&1) | 4)
    return wrapper


def acquire_skeleton_pose(backend, selection_mask, mode, eager, *, resolve_component,
                          allocate_wrapper, acquire_bank):
    """Resolve a valid resource handle, allocate wrapper, optionally acquire bank.

    backend has resource={flags,payload} and cache. Only resource bit31 enables
    payload resolution. resolve_component(backend, payload) supplies cache lookup.
    allocate_wrapper() -> mutable prior storage or None.
    acquire_bank(pool, uint16 mask, representation_bit) -> bank.
    Null wrapper plus eager is refused as an authored guard before native null use.
    """
    resource=backend['resource']
    payload=resource['payload'] if resource['flags'] & 0x80000000 else None
    component=resolve_component(backend,payload) if payload is not None else None
    wrapper=initialize_acquired_pose(allocate_wrapper(),component,selection_mask,mode)
    if int(eager)&255:
        if wrapper is None:
            raise ValueError('eager acquisition requires allocated wrapper')
        if wrapper['primary'] is None:
            wrapper['primary']=acquire_bank(wrapper['component']['pool'],wrapper['index'],
                                            wrapper['flags']&1)
    return wrapper
