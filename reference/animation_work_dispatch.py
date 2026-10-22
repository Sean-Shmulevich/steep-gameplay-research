"""Concrete Kino interface work dispatch; numerical evaluator remains supplied.

Evidence: CENTRAL_IMPULSE.md, Concrete pose-work interface dispatch.
Time is transported as float32 bits without assigning units or finite-only policy.
"""

def dispatch_pose_work(interface, packet, extra_work, *, prepare, evaluate):
    if type(extra_work) is not int or not 0<=extra_work<=255:
        raise ValueError('uint8 extra-work argument required')
    owner=interface['owner']
    if owner is None:return 0
    prepare(owner['context'],0)
    # Both packet arguments and owner are reloaded after preparation.
    result=evaluate(interface['owner'],packet['input'],packet['output'],
                    packet['time_bits'],extra_work)
    if type(result) is not int or not 0<=result<=255:
        raise ValueError('uint8 evaluator result required')
    return result


def pose_output_route(extra_work, owner_present, skip_result, result_header):
    """Local output-path gates, not an evaluator or proof of no side effects.

    Evidence: CENTRAL_IMPULSE.md, Pose evaluator output gates.
    skip_result is the supplied low byte of an unresolved graph predicate.
    result_header contains a low-29-bit result count plus encoding flags.
    """
    for value,limit in ((extra_work,255),(skip_result,255),(result_header,0xffffffff)):
        if type(value) is not int or not 0<=value<=limit:raise ValueError('unsigned gate fields required')
    if type(owner_present) is not bool:raise ValueError('boolean owner presence required')
    if not extra_work or not owner_present:return 'skip_extra_path'
    if skip_result:return 'predicate_skips_output'
    if result_header & 0x1fffffff <= 1:return 'insufficient_results'
    return 'publish_output'
