"""Runnable synthetic known-body loading example; contains no game payloads."""
import json
import struct
from .pose_body_loading_runtime import deserialize_known_pose_body
from .pose_body_load import finalize_pose_body_resources


def run():
    def block(tag,data):return struct.pack('<II',0xecd70000|tag,len(data)+8)+data
    body=bytearray(0x200);metadata={2:bytearray(0x60)};entries={3:bytearray(72)}
    struct.pack_into('<Q',body,0x30,2);struct.pack_into('<QHH',body,0xb8,3,0,1)
    table=bytearray(128);struct.pack_into('<QI',table,0,7,0x9fb7)
    reader=bytearray(0x50);struct.pack_into('<QII',reader,0x28,4,1,8)
    struct.pack_into('<QII',reader,0x38,5,0,8)
    frame=struct.pack('<12f',1,0,0,0,1,0,0,0,1,2,3,4)
    resource=struct.pack('<II',0x73cb9fb7,0)+frame+bytes(36)+bytes(6)
    data=block(0xc02,b'\0\0')+block(0xc05,bytes(58))+block(0xc06,b'\0')
    data+=block(0xe02,struct.pack('<I',1))+block(0xe03,resource)
    data+=block(0x1001,bytes(92))+block(0x1002,struct.pack('<6f',1,2,3,4,5,6))
    data+=block(0x1003,struct.pack('<4f',2,3,4,5))+block(0x1004,struct.pack('<3f',-1,6,-1))
    struct.pack_into('<QI',reader,0,1000,len(data));struct.pack_into('<QQ',reader,0x10,1000,1000)
    transforms={};parameters={};events=[]
    def transform_allocate():
        transforms[8]=bytearray(64);events.append('transform allocation');return 8
    def parameter_allocate(kind):
        token=20+len(parameters);parameters[token]=bytearray(16)
        events.append(kind+' allocation');return token
    def unavailable(*args):raise AssertionError('Synthetic fixture unexpectedly reached lifecycle service')
    deserialize_known_pose_body(body,reader,body_token=10,buffers={1000:data},metadata=metadata,
        object_tables={4:table},fixup_arrays={5:bytearray(192)},grow_objects=unavailable,
        grow_fixups=unavailable,entry_arrays=entries,identity_token=1,transforms=transforms,
        allocate_transform=transform_allocate,release_transform=unavailable,
        parameter_records=parameters,allocate_parameter=parameter_allocate,
        release_parameter=unavailable,reset_resource=unavailable,grow_entries=unavailable)
    resources={7:bytearray(0x60)}
    finalize_pose_body_resources(body,entry_arrays=entries,resources=resources)
    return dict(fixture='authored synthetic body; no game assets',reader_error=reader[0x20],
        registered_objects=struct.unpack_from('<I',reader,0x30)[0],
        decoded_entry_attempts=struct.unpack_from('<I',body,0x110)[0],
        motion=list(struct.unpack_from('<6f',body,0x1a0)),
        resource_owner_index=list(struct.unpack_from('<QI',resources[7],0x30)),
        local_translation=list(struct.unpack_from('<3f',transforms[8],48)),
        scalar_vector=list(struct.unpack_from('<4f',parameters[20])),
        parameters=list(struct.unpack_from('<3f',parameters[21])),events=events,
        limits=['Supplied pools; no physics-provider registration or live gameplay.'])


if __name__=='__main__':print(json.dumps(run(),indent=2))
