"""Bind recovered container, body-ring and metadata-tree cleanup.

Evidence: LINK_SOLVER.md, Joined container cleanup.
"""
from .pose_body_tree import remove_pose_tree_body
from .pose_command_registry import (process_pose_body_constraints,
                                    unregister_pose_constraint_container)


def remove_retained_pose_container(provider_token,container_token,output,*,
        providers,containers,constraints,bodies,metadata,arrays,node_arrays,
        get_kind,destroy,grow_output):
    """Remove a container with actual reconstructed tree/body processing.

    destroy(token,flags) is a virtual dispatch service. Bind known base/kind4
    records to destroy_pose_constraint only when their dynamic type is established.
    grow_output(output,capacity) preserves entries and updates pointer/count/capacity.
    The public token/mapping interface is authored; cleanup ordering is recovered.
    """
    provider=providers[provider_token]
    def tree_remove(tree_token,body):
        # Native container removal supplies provider+d0, so use an aliased view.
        if tree_token!=provider_token+0xd0:
            raise ValueError('Unexpected tree descriptor identity')
        remove_pose_tree_body(memoryview(provider)[0xd0:0xf0],body,bodies=bodies,
            metadata=metadata,node_arrays=node_arrays,destroy=destroy)
    def process(owner,body,queue):
        process_pose_body_constraints(providers[owner],body,queue,constraints=constraints,
            bodies=bodies,metadata=metadata,arrays=arrays,get_kind=get_kind,
            destroy=destroy,grow_output=grow_output)
    unregister_pose_constraint_container(provider,container_token,output,
        provider_token=provider_token,containers=containers,constraints=constraints,
        bodies=bodies,metadata=metadata,arrays=arrays,get_kind=get_kind,
        remove_tree_body=tree_remove,process_body=process,grow_output=grow_output)
