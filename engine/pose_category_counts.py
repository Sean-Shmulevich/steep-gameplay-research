"""Recovered pose-type dispatch and planned solver category contributions.

Evidence: LINK_SOLVER.md, Pose category-count prepass.
"""
import struct
from .snow_pose_solver_counts import pose_solver_counts


def count_pose_categories(counts,pose_tokens,*,poses,bodies):
    """Accumulate counts using supplied virtual type results and retained storage.

    Pose type is the resolved uint32 result of virtual slot10. storage70 starts at
    the pose's inline+70 record. No semantic animation/constraint names are assigned
    to the six raw types, and this API does not invoke virtual methods itself.
    """
    if len(counts)!=25 or any(type(v) is not int or not 0<=v<=0xffffffff for v in counts):
        raise ValueError('Exactly25 raw uint32 counts required')
    def add(index,n=1):counts[index]=(counts[index]+n)&0xffffffff
    for i in range(len(pose_tokens)):
        pose=poses[pose_tokens[i]];kind=pose['type']
        if type(kind) is not int or not 0<=kind<=0xffffffff:raise ValueError('Raw uint32 virtual type required')
        if kind==4:add(24);continue
        if kind not in (1,2,3,5,6):continue
        flags=bodies[pose['second_body']]['metadata_flags50'];b=int(bool(flags&0x8000))
        if kind==1:add(10+b)
        elif kind==6:add(2+b)
        elif kind==2:
            result=pose_solver_counts(pose['storage70'],flags)
            for index,name in ((8,'doubled_rows'),(10,'hard_triple_blocks'),(14,'flagged_or_hard_rows'),
                               (16,'first_soft_rows'),(18,'second_hard_rows'),(20,'second_soft_rows')):
                add(index+b,result[name])
        elif kind==3:
            storage=pose['storage70'];add(22+b);add(8+b,2)
            if struct.unpack_from('<I',storage,0x68)[0]!=0:add(14+b)
        else:
            storage=pose['storage70'];add(10+b);add(8+b,1+4*int(storage[0x68]!=0))
            if storage[0x70]!=0:add(12+b)
