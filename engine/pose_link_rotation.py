"""Recovered quaternion matrix arithmetic and fixed-angle selector rotation.

Evidence: CENTRAL_IMPULSE.md, Fixed-angle selector rotation.
"""
import math
import struct
from reference.central_impulse import f32

SELECTOR_ANGLE=f32(0.6456422805786133)
# Offline execution of the original half-angle scalar functions at this literal.
SELECTOR_HALF_SIN=struct.unpack('<f',struct.pack('<I',0x3ea26db4))[0]
SELECTOR_HALF_COS=struct.unpack('<f',struct.pack('<I',0x3f72c6b0))[0]


def quaternion_basis(quaternion):
    """Three XYZ rows; preserve native operation order, without normalization."""
    if len(quaternion)!=4:raise ValueError('XYZW quaternion required')
    x,y,z,w=map(f32,quaternion)
    if not all(math.isfinite(v) for v in (x,y,z,w)):raise ValueError('Finite quaternion required')
    dx,dy,dz=f32(x*2.),f32(y*2.),f32(z*2.)
    xx,yy,zz=f32(x*dx),f32(y*dy),f32(z*dz)
    xy,xz,yz=f32(dy*x),f32(dz*x),f32(dz*y)
    wx,wy,wz=f32(dx*w),f32(dy*w),f32(dz*w)
    return [[f32(1.-f32(zz+yy)),f32(xy+wz),f32(xz-wy)],
            [f32(xy-wz),f32(1.-f32(zz+xx)),f32(yz+wx)],
            [f32(xz+wy),f32(yz-wx),f32(1.-f32(yy+xx))]]


def selector_rotation_basis(normal, angle=SELECTOR_ANGLE):
    """Exact inspected selector angle only; general trigonometry is not supplied."""
    if f32(angle)!=SELECTOR_ANGLE:raise ValueError('Only the recovered selector angle is supported')
    if len(normal)!=3:raise ValueError('XYZ normal required')
    xyz=[f32(f32(x)*SELECTOR_HALF_SIN) for x in normal]
    return quaternion_basis(xyz+[SELECTOR_HALF_COS])
