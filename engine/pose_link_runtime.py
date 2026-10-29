"""Contact services for a group arena shared with pose constraints.

Evidence: LINK_SOLVER.md, Mixed contact and constraint group runtime.
"""
import struct
from .pose_link_arena import POOLS
from .pose_link_build import build_dispatched_pose_links
from .pose_link_feedback import write_pose_link_feedback
from .pose_link_secondary_rows import refresh_pose_secondary_link_rows


def make_pose_link_services(arena, *, arrays, links, bodies, payloads,
                            resources, profiles, modes):
    """Bind build/feedback/secondary-refresh callbacks without solving separately.

    Body views must describe the same retained state as the raw group bodies.
    They are caller supplied, not live snapshots. Pose categories are preserved.
    """
    view=memoryview(arena)
    word=lambda off:struct.unpack_from('<I',arena,off)[0]
    scalar=lambda off:struct.unpack_from('<f',arena,off)[0]
    def tokens(start,end):
        if end<start or (end-start)%8:raise ValueError('Whole pointer span required')
        n=(end-start)//8
        if not n:return []
        if len(arrays[start])<n:raise ValueError('Complete pointer array required')
        return arrays[start][:n]
    def records(start,count,stride):
        if start<0x190 or start+count*stride>len(arena):raise ValueError('Complete retained row range required')
        return [view[start+i*stride:start+(i+1)*stride] for i in range(count)]
    def context():
        counts=struct.unpack_from('<25I',arena,0x108)
        result=dict(flags38=word(0x38),scalar_c=scalar(0xc),factor14=scalar(0x14),
                    field18=scalar(0x18),field1c=scalar(0x1c),field20=scalar(0x20),
                    result_count=word(0x180),result_rows=records(word(0x178),sum(counts),16),pools={})
        for name,cat,stride in POOLS:
            start=word(0x16c)+16*word(0x40+4*cat)
            result['pools'][name]=dict(base=start,count=word(0xa4+4*cat),rows=records(start,counts[cat],stride))
        return result
    def build(_,start,end):
        current=context()
        try:
            build_dispatched_pose_links(current,tokens(start,end),links=links,bodies=bodies,
                payloads=payloads,resources=resources,profiles=profiles,modes=modes)
        finally:
            struct.pack_into('<I',arena,0x180,current['result_count'])
            for name,cat,_ in POOLS:struct.pack_into('<I',arena,0xa4+4*cat,current['pools'][name]['count'])
    def feedback(_,start,end):
        write_pose_link_feedback(context(),tokens(start,end),links=links,payloads=payloads)
    def refresh(_,start,end):
        current=context()
        current.update(counts=[0,0],rows=[current['pools']['clear_primary']['rows'],current['pools']['paired_primary']['rows']])
        refresh_pose_secondary_link_rows(current,tokens(start,end),links=links,bodies=bodies,payloads=payloads)
        struct.pack_into('<2I',arena,0xa4,*current['counts'])
    return dict(build_link_rows=build,link_feedback=feedback,refresh_secondary_rows=refresh)
