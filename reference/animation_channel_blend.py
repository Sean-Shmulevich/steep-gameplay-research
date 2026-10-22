"""Recovered regular per-descriptor blend; quaternion kernel reused with explicit normalization seeds.

Evidence: CENTRAL_IMPULSE.md, Typed animation channel blending.
Descriptor kind names are numerical; no semantic channel interpretation inferred.
"""
import struct
from reference.animation_flat_conversion import _f32


def blend_channel(destination, source_a, source_b, descriptor, weight, vector_weight,
                  integer_weight, *, quaternion_blend=None, reciprocal_sqrt=None):
    if len(descriptor)!=8 or len(vector_weight)!=4:
        raise ValueError('8-byte descriptor and four vector weights required')
    offset,packed=struct.unpack_from('<HH',descriptor,4);kind=packed&15
    size={0:1,1:4,2:4,4:12,5:16,6:16}.get(kind,0)
    if not size:return
    if any(offset+size>len(b) for b in (destination,source_a,source_b)):
        raise ValueError('channel outside supplied buffers')
    a=bytes(source_a[offset:offset+size]);b=bytes(source_b[offset:offset+size])
    weight=_f32(weight)
    if kind in (0,2):
        av=int.from_bytes(a,'little');bv=int.from_bytes(b,'little')
        product=(((bv-av)&0xffffffff)*(int(integer_weight)&0xffffffff))&0xffffffff
        quotient=(product*0x80808081)>>39
        result=(av+quotient)&((1<<(8*size))-1)
        destination[offset:offset+size]=result.to_bytes(size,'little')
    elif kind==6:
        if quaternion_blend is None:
            if not callable(reciprocal_sqrt):
                raise ValueError('quaternion channels require an explicit reciprocal-square-root seed service')
            from reference.animation_channels import combine_rotation_channel
            def quaternion_blend(first, second, weights):
                return combine_rotation_channel(first, second, weights[0], 0, reciprocal_sqrt)
        result=quaternion_blend(struct.unpack('<4f',a),struct.unpack('<4f',b),
                                tuple(_f32(v) for v in vector_weight))
        destination[offset:offset+16]=struct.pack('<4f',*result)
    else:
        n=size//4;av=struct.unpack('<'+'f'*n,a);bv=struct.unpack('<'+'f'*n,b)
        if kind==4:bv=av  # observed first-source duplication, not ordinary vector interpolation
        factors=vector_weight if kind==5 else [weight]*n
        result=[_f32(x+_f32(_f32(y-x)*_f32(t))) for x,y,t in zip(av,bv,factors)]
        destination[offset:offset+size]=struct.pack('<'+'f'*n,*result)


def blend_additive_channel(destination, source_a, source_b, descriptor, weight,
                           vector_weight, integer_weight, *, reciprocal_sqrt=None):
    """Mode-four typed byte leaf; see CENTRAL_IMPULSE.md, Additive byte channels.

    Kind zero/one retain interpolation. Kind five adds weighted second lanes;
    kind six composes a weighted rotation. Remaining kinds leave bytes intact.
    """
    if len(descriptor)!=8 or len(vector_weight)!=4:
        raise ValueError('8-byte descriptor and four vector weights required')
    offset,packed=struct.unpack_from('<HH',descriptor,4);kind=packed&15
    if kind in (0,1):
        return blend_channel(destination,source_a,source_b,descriptor,weight,
                             vector_weight,integer_weight)
    if kind not in (5,6):return
    if any(offset+16>len(b) for b in (destination,source_a,source_b)):
        raise ValueError('channel outside supplied buffers')
    a=struct.unpack_from('<4f',source_a,offset)
    b=struct.unpack_from('<4f',source_b,offset)
    if kind==5:
        result=[_f32(_f32(_f32(w)*y)+x) for x,y,w in zip(a,b,vector_weight)]
    else:
        if not callable(reciprocal_sqrt):
            raise ValueError('quaternion channels require an explicit reciprocal-square-root seed service')
        from reference.animation_channels import combine_rotation_channel
        result=combine_rotation_channel(a,b,weight,4,reciprocal_sqrt)
    struct.pack_into('<4f',destination,offset,*result)


def combine_unweighted_byte_channel(destination, source_a, source_b, descriptor):
    """Near-one additive leaf, distinct from weighted interpolation.

    Evidence: CENTRAL_IMPULSE.md, Unweighted additive byte leaf.
    Byte sums wrap, scalar/vector sums round to float32, quaternion products
    retain recovered multiply/add ordering without normalization.
    """
    if len(descriptor)!=8:raise ValueError('8-byte descriptor required')
    offset,packed=struct.unpack_from('<HH',descriptor,4);kind=packed&15
    width={0:1,1:4,5:16,6:16}.get(kind,0)
    if not width:return
    if any(offset+width>len(b) for b in (destination,source_a,source_b)):
        raise ValueError('channel outside supplied buffers')
    if kind==0:
        destination[offset]=(source_a[offset]+source_b[offset])&255
        return
    from reference.animation_channels import combine_unweighted_channel
    count=width//4
    a=struct.unpack_from('<'+'f'*count,source_a,offset)
    b=struct.unpack_from('<'+'f'*count,source_b,offset)
    result=combine_unweighted_channel(a,b,[],kind)
    struct.pack_into('<'+'f'*count,destination,offset,*result)
