"""Face polygon construction; LINK_SOLVER.md, Face polygon vertices and tags."""
import struct
from reference.central_impulse import f32


def append_face_polygon(storage,frame,vertices,indices,reference_face,incident_face,flipped=False):
    """Append XYZ/tag records to retained 128-slot storage with count at0x800.

    Capacity enforcement is an authored guard; native helper has no bounds check.
    Only the low32 bits of the native tag expression survive the final store.
    """
    if len(storage)<0x804:raise ValueError('Retained polygon storage required')
    count=struct.unpack_from('<I',storage,0x800)[0]
    if count+len(indices)>128:raise ValueError('Polygon capacity exceeded')
    f=[list(map(f32,row)) for row in frame]
    for ordinal,index in enumerate(indices):
        x,y,z=map(f32,vertices[index])
        point=[f32(f32(f32(f32(f[0][j]*x)+f[3][j])+f32(f[1][j]*y))+f32(f[2][j]*z)) for j in range(3)]
        tag=(((((ordinal&0x3f)|(0x180 if flipped else 0x80))<<12)|(incident_face&0xfff))<<12)|(reference_face&0xfff)
        struct.pack_into('<3fI',storage,count*16,*point,tag&0xffffffff)
        count+=1
        struct.pack_into('<I',storage,0x800,count)
