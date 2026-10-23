"""Recovered release-context argument policy for one statically linked family.

Evidence: RESOURCE_RETIREMENT.md, Concrete context release policy.
The decoded target remains supplied; no operating-system release is implemented.
"""


def release_context_region(address, size, flags, *, invoke):
    """Invoke the selected target with (address, size,0x4000) iff byte flags==1.

    All other flag bytes use (address,0,0x8000). Inputs are uint64 address,
    uint32 size, and byte flags. Return the supplied target result. This exact
    equality differs from the upstream fallback's bit0 test. It is one context
    implementation, not a universal policy for all retained context objects.
    """
    return invoke(address, size if flags == 1 else 0,
                  0x4000 if flags == 1 else 0x8000)
