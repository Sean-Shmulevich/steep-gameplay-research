"""Arena-backed contact build/solve composition; LINK_SOLVER.md, Arena composition."""
import struct
from .pose_link_build import build_dispatched_pose_links
from .pose_link_solve import solve_pose_link_rows


POOLS=(('clear_primary',0,112),('paired_primary',1,128),('clear_shared',4,208),
       ('paired_shared',5,256),('clear_secondary',6,112),('paired_secondary',7,128))


def build_and_solve_pose_links(arena,link_tokens,*,links,bodies,payloads,resources,profiles,modes,
                               body_data,body_state):
    """Use initialized layout/counts and retained storage; no allocation or prepass.

    Arena origin is the solver context. Body data/state are explicit caller-owned
    records. Their production, body-index assignment and integration remain external.
    """
    if len(arena)<0x190:raise ValueError('Complete retained arena header required')
    counts=struct.unpack_from('<25I',arena,0x108)
    supported={category for _,category,_ in POOLS}
    if any(n for i,n in enumerate(counts) if i not in supported):raise ValueError('Unsupported populated row category')
    view=memoryview(arena)
    def records(start,count,stride):
        if start<0x190 or start+count*stride>len(arena):raise ValueError('Retained arena range out of bounds')
        return [view[start+i*stride:start+(i+1)*stride] for i in range(count)]
    results_offset=struct.unpack_from('<I',arena,0x178)[0]
    context={name:struct.unpack_from('<f',arena,offset)[0] for name,offset in
             (('scalar_c',0xc),('factor14',0x14),('field1c',0x1c),('field20',0x20))}
    context.update(flags38=struct.unpack_from('<I',arena,0x38)[0],result_count=struct.unpack_from('<I',arena,0x180)[0],
                   result_rows=records(results_offset,sum(counts),16),pools={})
    rowbase=struct.unpack_from('<I',arena,0x16c)[0]
    for name,category,stride in POOLS:
        start=rowbase+16*struct.unpack_from('<I',arena,0x40+category*4)[0]
        context['pools'][name]=dict(base=start,count=struct.unpack_from('<I',arena,0xa4+category*4)[0],
                                   rows=records(start,counts[category],stride))
    try:
        build_dispatched_pose_links(context,link_tokens,links=links,bodies=bodies,payloads=payloads,
                                    resources=resources,profiles=profiles,modes=modes)
    finally:
        struct.pack_into('<I',arena,0x180,context['result_count'])
        for name,category,_ in POOLS:struct.pack_into('<I',arena,0xa4+4*category,context['pools'][name]['count'])
    pools=context['pools']
    solve_pose_link_rows(arena,base_token=0,primary_rows=pools['clear_primary']['rows'],
        paired_primary_rows=pools['paired_primary']['rows'],secondary_rows=pools['clear_secondary']['rows'],
        paired_tangent_rows=pools['paired_secondary']['rows'],shared_rows=pools['clear_shared']['rows'],
        paired_shared_rows=pools['paired_shared']['rows'],arena=arena,body_data=body_data,
        body_state=body_state,results=context['result_rows'])
