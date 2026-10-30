"""Synthetic inspectable cleanup scenario; run python3 -m engine.pose_cleanup_bench.

No game payloads or live addresses. Evidence: LINK_SOLVER.md, Joined container cleanup.
"""
import json
import struct
from .pose_cleanup_runtime import remove_retained_pose_container
from .pose_command_registry import register_pose_constraint
from .pose_constraint_destroy import destroy_pose_constraint
from .pose_endpoint_rings import attach_pose_endpoint_rings


def run_pose_cleanup_scenario():
    """Exercise tree destruction, cross-owner removal and child queueing together."""
    def put(raw,off,fmt,*values):struct.pack_into('<'+fmt,raw,off,*values)
    def get(raw,off,fmt='I'):return struct.unpack_from('<'+fmt,raw,off)[0]
    provider=bytearray(0xf0);containers={10:bytearray(0x68),20:bytearray(0x68)}
    bodies={i:bytearray(0xa0) for i in (1,2,3)};metadata={i:bytearray(0x60) for i in (11,12,13)}
    arrays={100:[10,20],200:[0]*8,300:[0]*8,400:[80]*8,500:[1],600:[80],700:[]}
    for off,ptr,count,cap in ((0x50,100,2,2),(0x60,200,0,8),(0x70,300,0,8),(0x80,400,1,8)):
        put(provider,off,'QII',ptr,count,cap)
    for b,m,owner,flags in ((1,11,1,8),(2,12,2,1),(3,13,1,0)):
        put(bodies[b],0x30,'Q',m);put(metadata[m],0x20,'Q',owner);metadata[m][0x52]=flags
    put(metadata[11],0x54,'I',111)
    records={i:bytearray(0x200) for i in (30,40,80,90)}
    for t,a,b in ((30,1,3),(40,1,2),(80,1,3),(90,1,3)):
        put(records[t],8,'QQ',a,b);put(records[t],0x50,'Q',t+1000);records[t][0x5a]=1
    for t in (30,40):
        register_pose_constraint(provider,t,arrays=arrays,grow=lambda *a:None,get_kind=lambda t:4,
            notify=lambda t,s:attach_pose_endpoint_rings(t,s,records=records,bodies=bodies))
    c=containers[10];put(c,0x20,'Q',123);put(c,0x38,'QI',500,1);put(c,0x58,'QI',600,1)
    nodes=bytearray(32);put(nodes,0,'iii',-1,-1,-1);put(nodes,16,'QI',90,111)
    put(provider,0xd0,'Qii',800,1,0);put(provider,0xe4,'ii',0,-1)
    output=bytearray(16);put(output,0,'QII',700,0,0)
    manager=bytearray(0x30);put(manager,0x28,'Q',999);events=[]
    def destroy(t,f):
        destroy_pose_constraint(t,f,records=records,bodies=bodies,base_tables=(901,902),final_tables=(903,904),
            get_callback_manager=lambda:900,managers={900:manager},
            invoke=lambda fn,t,f,user:events.append(dict(operation='callback',token=t,flag=f,userdata=user)),
            release=lambda t:events.append(dict(operation='release_intent',token=t)))
    def grow(out,capacity):
        old=get(out,0,'Q');count=get(out,8);arrays[701]=arrays[old][:count]+[0]*(capacity-count)
        put(out,0,'QII',701,count,capacity);events.append(dict(operation='grow_output',capacity=capacity))
    remove_retained_pose_container(1000,10,output,providers={1000:provider},containers=containers,
        constraints=records,bodies=bodies,metadata=metadata,arrays=arrays,node_arrays={800:nodes},
        get_kind=lambda t:4,destroy=destroy,grow_output=grow)
    def active(off):return arrays[get(provider,off,'Q')][:get(provider,off+8)]
    return dict(schema='pose-cleanup-inspection-v1',source='authored synthetic fixture',
        events=events,containers=active(0x50),individual_constraints=active(0x60),
        first_commands=active(0x70),second_commands=active(0x80),
        queued_constraints=arrays[get(output,0,'Q')][:get(output,8)],
        body_heads={str(b):get(raw,0x90,'Q') for b,raw in bodies.items()},
        tree_active=get(provider,0xd8),tree_free=get(provider,0xdc),
        moved_container=dict(owner=get(containers[20],0x20,'Q'),index=get(containers[20],0x30),backlink=get(containers[20],0x28,'Q')),
        limits=['Synthetic known kind4 values; not a captured game scene.',
                'Callback and storage release are recorded intents; no allocator reclamation.',
                'Serial retained storage; no live mutation or concurrency claim.'])


if __name__=='__main__':print(json.dumps(run_pose_cleanup_scenario(),indent=2))
