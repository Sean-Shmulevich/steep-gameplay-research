"""Run a synthetic spawn publication: python3 -m engine.examples.spawn_publication_probe."""
import json
import math
import struct
from reference.entity_transform_update import TransformEntity
from reference.skeleton_parent_transform import publish_spawn_pose, publish_spawn_entity_transform, reset_animation_bank_parent


def run_probe():
    entity=TransformEntity(bytes(64),['synthetic-component'])
    events=[];banks={name:dict(parent=bytes(32),default_pose=bytes(32),records=[bytes([0x5a])*32]*4,count=3,reset_word=123) for name in ('a','b')}
    parent=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[10,20,30,1]]
    def get_entity(state):events.append('entity');return entity
    def read_parent(state,phase):events.append('parent_'+phase);return parent
    def notify(phase,component,owner):events.append(phase+'_'+component)
    def publish(owner,matrix):
        events.append('publish')
        payload=struct.pack('<16f',*(x for row in matrix for x in row))
        publish_spawn_entity_transform(owner,payload,derived=False,thread_id=1,
            notify=notify,publish_cache=lambda _:events.append('cache'))
    def skeleton(owner):events.append('skeleton');return {'slots':['a','b']}
    def reset(bank,pose):
        events.append('reset_'+bank)
        payload=struct.pack('<8f',*(pose['parent_position']+pose['parent_rotation']))
        reset_animation_bank_parent(banks[bank],payload,True,
            lambda:struct.pack('<8f',0,0,0,0,0,0,0,1))
    result=publish_spawn_pose({'position':[1,2,3,0],'rotation':[0,0,0,2]},
        get_entity=get_entity,read_parent=read_parent,reciprocal_sqrt=lambda n:1/math.sqrt(n),
        publish_entity=publish,find_skeleton=skeleton,reset_parent=reset)
    return dict(evidence='synthetic reconstruction example; exact reciprocal used as authored estimate',
        events=events,matrix=result['matrix'],banks={name:dict(parent=list(struct.unpack('<8f',bank['parent'])),active_records=[list(struct.unpack('<8f',r)) for r in bank['records'][:bank['count']]],tail_unchanged=bank['records'][-1]==bytes([0x5a])*32,reset_word=bank['reset_word']) for name,bank in banks.items()},final_lock_depth=entity.lock_depth,
        native_game_access=False)

if __name__=='__main__':print(json.dumps(run_probe(),indent=2))
