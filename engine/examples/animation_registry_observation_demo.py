"""Synthetic transport demo. No game process, native pointers or assets used."""
import json
import struct
from engine.animation_registry_observation import capture_construction_pairs


def run():
    base=0x100000;registry=base+0x100;storage=base+0x200
    memory=bytearray(1024)
    memory[0x100:0x104]=b'DEMO'
    # Earlier null payload suppresses the later matching identity.
    pairs=[(11,22),(33,0),(44,55)]
    memory[0x118:0x124]=struct.pack('<QI',storage,8|(len(pairs)<<16))
    memory[0x200:0x230]=b''.join(struct.pack('<QQ',*pair) for pair in pairs)
    def readv(plan):
        return [bytes(memory[a-base:a-base+n]) for a,n in plan]
    result=capture_construction_pairs(readv,registry,[(registry,b'DEMO')],query_identity=44)
    return dict(evidence='synthetic_transport_demo',game_process=False,observation=result)


if __name__=='__main__':print(json.dumps(run(),indent=2))
