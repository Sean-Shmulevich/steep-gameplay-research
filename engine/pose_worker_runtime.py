"""Retained numerical services bound to the recovered group batch worker.

Evidence: LINK_SOLVER.md, Joined numerical batch worker.
"""
import struct
from .pose_group_worker import run_pose_group_worker
from .pose_group_retained import read_retained_pose_group
from .pose_group_prepare import prepare_pose_group
from .pose_group_runtime import run_pose_group_runtime
from .pose_link_runtime import make_pose_link_services
from .pose_category_counts import count_pose_categories
from .pose_link_counts import count_pose_link_rows
from .pose_solver_layout import plan_pose_solver_layout
from .pose_free_motion import advance_pose_free_motion


def run_retained_pose_worker(owner_token,job,*,contexts,batches,arrays,groups,bodies,
                             metadata,settings,links,entry_arrays,constraints,get_kind,
                             payloads,resources,profiles,modes,buffers,allocate,release,
                             claim,poststep,atan2=None,notify=None,damping_records=None,
                             damping_response=None,update_body=None):
    """Compose serial numerical work with explicit claim/allocator/class services.

    allocate(size) returns a nonzero token registered in buffers. release(token)
    supplies allocator effects. Raw records and resource views must remain stable
    except for modeled mutations. This is not a live injector or thread-safe host.
    """
    def solve(token,request):
        group=groups[token];configuration=settings[request['settings_token']]
        parsed=read_retained_pose_group(group,arrays=arrays,bodies=bodies,metadata=metadata,
            links=links,entry_arrays=entry_arrays,constraints=constraints,get_kind=get_kind)
        counts=[0]*25
        count_pose_link_rows(counts,parsed['link_tokens'],links=parsed['links'],bodies=parsed['bodies'],
            payloads=payloads,mode=struct.unpack_from('<I',configuration,0x24)[0])
        count_pose_categories(counts,parsed['pose_tokens'],poses=parsed['poses'],bodies=parsed['bodies'])
        body_count=struct.unpack_from('<I',group,0x18)[0]
        size=plan_pose_solver_layout(counts,body_count)['size']
        if size>request['capacity']:
            if request['buffer']:release(request['buffer'])
            request['buffer']=allocate(size);request['capacity']=size
        if not request['buffer']:raise ValueError('Nonzero retained solver allocation required')
        arena=buffers[request['buffer']]
        prepare_pose_group(arena,configuration,scalar=request['scalar'],group_token=token,
            body_count=body_count,link_tokens=parsed['link_tokens'],pose_tokens=parsed['pose_tokens'],
            links=parsed['links'],payloads=payloads,poses=parsed['poses'],bodies=parsed['bodies'])
        services=make_pose_link_services(arena,arrays=arrays,links=parsed['links'],bodies=parsed['bodies'],
            payloads=payloads,resources=resources,profiles=profiles,modes=modes)
        run_pose_group_runtime(arena,base_token=request['buffer'],groups=groups,arrays=arrays,bodies=bodies,
            metadata=metadata,constraints=constraints,get_kind=get_kind,link_services=services,
            poststep=poststep,atan2=atan2,notify=notify,damping_records=damping_records,
            damping_response=damping_response,update_body=update_body)
    def advance(start,end,request,vector_token):
        count=(end-start)//8
        selected=arrays[start][:count] if count else []
        if len(selected)!=count:raise ValueError('Complete retained body span required')
        configuration=settings[vector_token-8]
        advance_pose_free_motion(selected,bodies=bodies,metadata=metadata,scalar=request['scalar'],
            vector=struct.unpack_from('<3f',configuration,8),damping_records=damping_records,
            damping_response=damping_response)
    run_pose_group_worker(owner_token,job,contexts=contexts,batches=batches,arrays=arrays,groups=groups,
        bodies=bodies,metadata=metadata,settings=settings,claim=claim,solve=solve,
        advance_motion=advance,poststep=poststep,release=release)
