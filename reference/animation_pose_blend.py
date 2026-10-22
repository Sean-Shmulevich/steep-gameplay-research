"""Recovered mode-zero, inactive-mask pose wrapper orchestration.

Evidence: CENTRAL_IMPULSE.md, Regular pose wrapper orchestration.
Selection, reciprocal scale removal and bank arithmetic are explicit services.
This keeps their incompatible storage adapters visible instead of guessing a
byte-buffer to transform-record mapping. Mode-zero active-mask preparation and blending use explicit services.
No additive route is implied.
"""
from reference.central_impulse import f32


def blend_regular_pose(destination, source, weight, *, acquire, select_bank,
                       remove_scale, blend_bank, blend_mask=None, prepare_mask=None,
                       masked_blend=None):
    """Mutate destination and service-owned banks in recovered call order.

    Wrappers use primary, component.pool/flags16, index, request_byte.
    acquire(pool, index, mode_bit) must return a valid bank.
    select_bank(wrapper) and remove_scale(wrapper, bank) return selected banks.
    blend_bank(output, first, second, weight, selector, mask, exclusion_mask=0)
    receives the primary output even when selection returns an alternate bank.
    Services may mutate wrappers; cached mask/selector precede selection calls.
    Exceptions propagate with partial mutations, without invented rollback.
    """
    if destination['primary'] is None:
        destination['primary'] = acquire(destination['component']['pool'],
                                         destination['index'] & 65535,
                                         destination['request_byte'] & 1)
        if destination['primary'] is None:
            raise ValueError('acquisition must supply a valid primary bank')
    mask = (source['index'] & destination['index']) & 65535
    selector = (destination['component']['flags16'] >> 3) & 7
    active = blend_mask is not None and blend_mask['active_count'] != 0
    if active:
        prepare_mask(blend_mask, remove_scale(source, select_bank(source)), 0)
        uniform_groups = blend_mask['uniform_groups']
    second = remove_scale(source, select_bank(source))
    first = remove_scale(destination, select_bank(destination))
    if active:
        result = masked_blend(destination['primary'], first, second, f32(weight),
                              selector, mask, weight_mode=1,
                              uniform_groups=uniform_groups, exclusion_mask=0)
    else:
        result = blend_bank(destination['primary'], first, second, f32(weight),
                            selector, mask, exclusion_mask=0)
    destination['primary']['flags'] |= 1 << 27
    return result


def blend_regular_byte_pose(destination, source, weight, *, acquire, convert=None,
                            get_owner_scalar, reciprocal_sqrt=None, blend_mask=None):
    """Compose recovered selection, byte scaling and regular bank arithmetic.

    Evidence: CENTRAL_IMPULSE.md, Joined regular byte pose path.
    Allocation remains supplied; conversion defaults to the recovered byte adapter.
    get_owner_scalar(wrapper) reads the current owner's scalar when needed.
    Banks use animation_bank_blend plus animation_bank_scale schemas; wrappers
    use select_converted_owner_bank's schema. Mutations retain bank identity.
    """
    from reference.skeleton_parent_transform import select_converted_owner_bank
    from reference.animation_bank_conversion import convert_relative_byte_bank
    if convert is None:
        convert = lambda a, b, selector: convert_relative_byte_bank(
            a, b, selector, reciprocal_sqrt)
    from reference.animation_bank_scale import remove_owner_byte_bank_scale
    from reference.animation_bank_blend import blend_regular_pose_bank, blend_masked_pose_bank
    from reference.animation_mask_preparation import prepare_blend_mask
    return blend_regular_pose(destination, source, weight, acquire=acquire,
        blend_mask=blend_mask, prepare_mask=prepare_blend_mask,
        masked_blend=lambda *args, **kwargs: blend_masked_pose_bank(
            *args, **kwargs, reciprocal_sqrt=reciprocal_sqrt),
        select_bank=lambda wrapper: select_converted_owner_bank(
            wrapper, acquire=acquire, convert=convert),
        remove_scale=lambda wrapper, bank: remove_owner_byte_bank_scale(
            wrapper, bank, lambda: get_owner_scalar(wrapper)),
        blend_bank=lambda *args, **kwargs: blend_regular_pose_bank(
            *args, **kwargs, reciprocal_sqrt=reciprocal_sqrt))
