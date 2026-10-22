"""Recovered Hierarchy/accessor initializer with explicit transform globals.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Accessor construction bypasses pairs.
Unknown bytes are preserved; supplied matrix bytes are not assumed identity.
"""
import struct


def initialize_transform_accessor(backing, initial_transform, fallback_holder):
    backing=bytes(backing);initial_transform=bytes(initial_transform)
    if len(backing)!=224 or len(initial_transform)!=64:
        raise ValueError('224-byte backing and 64-byte supplied transform required')
    if type(fallback_holder) is not int or not 0<=fallback_holder<2**64:
        raise ValueError('uint64 supplied fallback holder required')
    result=bytearray(backing)
    result[:64]=initial_transform
    for offset in (0x40,0x48,0x50,0x80):struct.pack_into('<Q',result,offset,0)
    struct.pack_into('<I',result,0x58,0)
    struct.pack_into('<H',result,0x5c,0x101)
    for offset in (0x60,0x68):struct.pack_into('<Q',result,offset,fallback_holder)
    for offset,value in ((0x70,0),(0x74,0xffffffff),(0x78,0xffff),
                         (0x8c,0),(0x90,0xffffffff),(0x94,0)):
        struct.pack_into('<I',result,offset,value)
    result[0x88]=0;result[0x98]=1
    return bytes(result)


def bootstrapped_transform_default():
    """Transform globals after the recovered shared initializer executes.

    This does not assert that a particular live process has run that initializer
    or that no later indirect writer can replace the globals.
    """
    return struct.pack('<16f',1.,0.,0.,0.,0.,1.,0.,0.,
                       0.,0.,1.,0.,0.,0.,0.,1.)
