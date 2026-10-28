"""Connect recovered dispatch and all four builders; LINK_SOLVER.md, Unified build."""
from .pose_link_dispatch import dispatch_pose_link_builders
from .pose_link_builder import build_pose_link_rows
from .pose_link_paired_builder import build_paired_pose_link_rows
from .pose_link_multi_builder import build_multi_pose_link_rows
from .pose_link_paired_multi_builder import build_paired_multi_pose_link_rows


def build_dispatched_pose_links(context,link_tokens,*,links,bodies,payloads,resources,profiles,modes):
    """Build into six retained pools with shared result numbering.

    pools contains clear_primary/secondary/shared and paired_primary/secondary/shared.
    Each pool has rows, count, base (byte offset in a common abstract arena).
    This adapter owns no allocation, solver iteration or native object lifetime.
    """
    def invoke(c,a,b,p,kind,multi):
        names=('primary','shared' if multi else 'secondary')
        view={k:c[k] for k in ('flags38','scalar_c','factor14','field1c','field20','result_count','result_rows')}
        for name in names:
            pool=c['pools'][kind+'_'+name]
            view[name+'_rows']=pool['rows'];view[name+'_count']=pool['count'];view[name+'_base']=pool['base']
        fn={('clear',False):build_pose_link_rows,('paired',False):build_paired_pose_link_rows,
            ('clear',True):build_multi_pose_link_rows,('paired',True):build_paired_multi_pose_link_rows}[kind,multi]
        try:
            fn(view,bodies[a],bodies[b],p,resources=resources,profiles=profiles,modes=modes)
        finally:
            # Mutations are not transactional: expose consumed counters on failure too.
            c['result_count']=view['result_count']
            for name in names:c['pools'][kind+'_'+name]['count']=view[name+'_count']
    builders={prefix+'_'+suffix:(lambda c,a,b,p,k=kind,m=multi:invoke(c,a,b,p,k,m))
              for prefix,kind in (('metadata_clear','clear'),('metadata_set','paired'))
              for suffix,multi in (('single',False),('multi',True))}
    dispatch_pose_link_builders(context,link_tokens,links=links,bodies=bodies,payloads=payloads,builders=builders)
