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


def run_pose_contact_pass(arena,link_tokens,*,links,bodies,payloads,resources,profiles,modes,
                          body_data,body_state,body_tokens,raw_bodies):
    """Build, solve, publish contact cache and copy motion into retained raw bodies.

    Contact-only slice: pose constraints, secondary phase and poststep are excluded.
    body_tokens order must correspond to body_state indices and the body's solver
    index. Parsed body inputs and raw_bodies must describe the same supplied state.
    """
    from .pose_link_feedback import write_pose_link_feedback
    from .pose_body_feedback import write_pose_body_feedback
    build_and_solve_pose_links(arena,link_tokens,links=links,bodies=bodies,payloads=payloads,
        resources=resources,profiles=profiles,modes=modes,body_data=body_data,body_state=body_state)
    counts=struct.unpack_from('<25I',arena,0x108)
    start=struct.unpack_from('<I',arena,0x178)[0];view=memoryview(arena)
    results=[view[start+16*i:start+16*(i+1)] for i in range(sum(counts))]
    write_pose_link_feedback(dict(flags38=struct.unpack_from('<I',arena,0x38)[0],result_rows=results),
                             link_tokens,links=links,payloads=payloads)
    write_pose_body_feedback(body_tokens,bodies=raw_bodies,body_state=body_state)


def run_pose_contact_pass_from_bodies(arena,link_tokens,*,links,bodies,payloads,resources,profiles,modes,
                                      body_tokens,raw_bodies,scalar,vector,damping_response=None):
    """Produce arena body buffers, then run the contact build/solve/feedback slice.

    Bodies combine builder fields with tensor170/scalar124/metadata_flags52/flagsaa
    and optional damping1b8. Their frame basis is used for buffer production.
    Supplied body order must match index1c; this check is an authored API guard.
    """
    from .pose_body_buffers import build_pose_body_buffers
    ordered=[]
    for index,token in enumerate(body_tokens):
        body=bodies[token]
        if body['index1c']!=index:raise ValueError('Body order must match solver index')
        ordered.append(dict(body,basis=body['frame']['basis']))
    produced=build_pose_body_buffers(ordered,scalar=scalar,vector=vector,damping_response=damping_response)
    view=memoryview(arena);buffers={}
    for key,offset,stride in (('body_data',0x170,64),('body_state',0x174,32)):
        start=struct.unpack_from('<I',arena,offset)[0]
        if start<0x190 or start+len(ordered)*stride>len(arena):raise ValueError('Body buffers exceed retained arena')
        buffers[key]=[]
        for i,record in enumerate(produced[key]):
            target=view[start+i*stride:start+(i+1)*stride];target[:]=record;buffers[key].append(target)
    run_pose_contact_pass(arena,link_tokens,links=links,bodies=bodies,payloads=payloads,
        resources=resources,profiles=profiles,modes=modes,body_tokens=body_tokens,
        raw_bodies=raw_bodies,**buffers)


def solve_pose_contact_secondary_correction(arena,link_tokens,*,links,bodies,payloads,body_data,body_state):
    """Run gated secondary contact refresh/solve, leaving correction state available.

    Does not apply corrections to transforms or run group poststep. Body state must
    alias the arena state range, as in run_pose_contact_pass_from_bodies.
    """
    from .pose_link_secondary_rows import refresh_pose_secondary_link_rows
    flags=struct.unpack_from('<I',arena,0x38)[0]
    if not flags&0x07ff0000:return False
    struct.pack_into('<I',arena,0x38,(flags&~0x08000000)|0x10000000)
    start,end=struct.unpack_from('<II',arena,0x174)
    if end<start or start<0x190 or end>len(arena) or (end-start)%32:
        raise ValueError('Complete retained secondary state range required')
    arena[start:end]=bytes(end-start)
    counts=struct.unpack_from('<25I',arena,0x108);view=memoryview(arena)
    resultstart=struct.unpack_from('<I',arena,0x178)[0]
    results=[view[resultstart+16*i:resultstart+16*(i+1)] for i in range(sum(counts))]
    rowbase=struct.unpack_from('<I',arena,0x16c)[0];pools={}
    for name,category,stride in POOLS:
        offset=rowbase+16*struct.unpack_from('<I',arena,0x40+category*4)[0]
        pools[name]=[view[offset+i*stride:offset+(i+1)*stride] for i in range(counts[category])]
    context=dict(field18=struct.unpack_from('<f',arena,0x18)[0],field1c=struct.unpack_from('<f',arena,0x1c)[0],
                 counts=[0,0],rows=[pools['clear_primary'],pools['paired_primary']],result_rows=results)
    refresh_pose_secondary_link_rows(context,link_tokens,links=links,bodies=bodies,payloads=payloads)
    struct.pack_into('<2I',arena,0xa4,*context['counts'])
    solve_pose_link_rows(arena,base_token=0,primary_rows=pools['clear_primary'],paired_primary_rows=pools['paired_primary'],
        shared_rows=pools['clear_shared'],paired_shared_rows=pools['paired_shared'],secondary_rows=pools['clear_secondary'],
        paired_tangent_rows=pools['paired_secondary'],arena=arena,body_data=body_data,body_state=body_state,results=results)
    return True


def correct_pose_contact_transforms(arena,link_tokens,*,links,bodies,payloads,body_data,body_state,
                                    body_tokens,raw_bodies,half_angle_trig=None):
    """Solve secondary contacts and apply the recovered constructor-selected update.

    The caller explicitly selects this body implementation. Other virtual update
    implementations are not dispatched. General sine/cosine remain a service.
    Raw transforms change; parsed body snapshots must be refreshed before reuse.
    """
    from .pose_body_secondary_update import apply_pose_secondary_body_state
    from .pose_body_integration import integrate_pose_body
    if not solve_pose_contact_secondary_correction(arena,link_tokens,links=links,bodies=bodies,
                                                   payloads=payloads,body_data=body_data,body_state=body_state):
        return False
    apply_pose_secondary_body_state(body_tokens,bodies=raw_bodies,body_state=body_state,
        update_body=lambda token,body,scalar:integrate_pose_body(body,scalar,half_angle_trig=half_angle_trig))
    return True
