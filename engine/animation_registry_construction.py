"""Bounded supplied-storage construction experiment, without native allocation.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Supplied-storage construction chain.
The callback models target-word production only, not arbitrary native callbacks.
"""
from copy import deepcopy
from reference.animation_registry_pairs import finalize_and_register


def construct_supplied_target(*, pairs, identity, target, constructor,
                              enabled, secondary_holder_present, secondary_target,
                              target_to_identity, identity_to_target):
    """Expose the temporary registration to a supplied inspection callback.

    Callback receives a copied snapshot and must return a uint32 target word.
    It cannot change the model's registry through that snapshot. Native callbacks
    may do more; those effects are deliberately not guessed here.
    """
    if identity is None or target is None or not callable(constructor):
        raise ValueError('nonnull identities and constructor callback required')
    if len(pairs)>=16383 or any(len(row)!=2 for row in pairs):
        raise ValueError('pair append must fit packed capacity')
    if type(enabled) is not bool or type(secondary_holder_present) is not bool:
        raise ValueError('explicit registry predicates required')
    rows=deepcopy(pairs);rows.append([identity,target])
    observation=dict(pairs=deepcopy(rows),target_word=0,registry_lock_held=False)
    word=constructor(deepcopy(observation))
    if type(word) is not int or not 0<=word<=0xffffffff:
        raise ValueError('constructor must supply uint32 target word')
    result=finalize_and_register(rows,identity=identity,target=target,target_word=word,
        enabled=enabled,secondary_holder_present=secondary_holder_present,
        secondary_target=secondary_target,target_to_identity=target_to_identity,
        identity_to_target=identity_to_target)
    return dict(callback_observation=observation,result=result,
                evidence=dict(callback='caller_supplied',allocation='external',
                              live_validated=False))
