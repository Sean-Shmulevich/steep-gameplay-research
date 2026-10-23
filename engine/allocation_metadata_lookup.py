"""Recovered address-region selector for allocation-release metadata.

Evidence: RESOURCE_RETIREMENT.md, Allocation metadata selection.
Tables and returned tokens are externally retained, build-specific state.
"""


def lookup_allocation_metadata(address, *, read_region, read_entry, default_index):
    """Resolve a uint64 address without dereferencing the payload itself.

    read_region(high32) returns None for a null region pointer or an indexable
    65536-byte tag table. The tag index is address bits 16..31. A tag of 255 or
    null region uses the unmasked default byte; other tags select low seven bits.
    read_entry(index) supplies the corresponding raw pointer-sized table value.
    No bounds, allocation ownership, object-lifetime or pointer validity proof
    is supplied by this routine. Services must reflect memory aliases; default
    storage overlaps the raw 127th entry in the inspected build.
    """
    if type(address) is not int or not 0 <= address < 2**64:
        raise ValueError('address must be uint64')
    region = read_region(address >> 32)
    tag = 255 if region is None else region[(address >> 16) & 0xffff]
    index = default_index() if tag == 255 else tag & 0x7f
    return read_entry(index)
