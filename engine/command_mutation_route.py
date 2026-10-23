"""Recovered local deferral branch, not a general engine mutation permission.

See ANIMATION_CONTEXT_RETIREMENT.md: Participant execution bypasses re-deferral.
Applies after the target routine's own eligibility and target-selection checks.
"""

def select_command_mutation_route(executing_byte, bypass_defer_byte):
    for value in (executing_byte, bypass_defer_byte):
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('uint8 flags required')
    return 'defer' if executing_byte != 0 and bypass_defer_byte == 0 else 'immediate'
