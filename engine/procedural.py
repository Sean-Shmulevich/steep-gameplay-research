"""Explicit procedural operations. Caller owns effector mapping and layer order."""
import copy
from reference import ik, landing_pose
from .math3d import vector
from .assets import canonical

def limb_target(request):
    for field in ('root','middle','end','requested_middle','requested_end'):vector(request[field])
    canonical(request)
    # Adapter policy: reject collapsed limbs before entering unguarded native math.
    for a,b in (('root','middle'),('middle','end')):
        if sum((x-y)**2 for x,y in zip(request[a],request[b]))<1e-20:raise ValueError('Collapsed limb')
    return ik.solve_middle_target(request['root'],request['middle'],request['end'],request['requested_middle'],request['requested_end'],request['middle_weight'],request['alignment_control'],request['end_weight'],request['mix_bias'],request.get('end_axis_mask',(True,True,True)))

def orient_bones(local_pose,requests):
    result=copy.deepcopy(local_pose);diagnostics=[]
    for request in requests:
        index=request['index']
        if type(index) is not int or not 0<=index<len(result):raise ValueError('Invalid effector mapping')
        vector(request['target'],4);canonical(request)
        update=ik.apply_weighted_bone_orientation(result[index]['quaternion_xyzw'],request['target'],request['weight'])
        result[index]['quaternion_xyzw']=list(update['rotation']);diagnostics.append(dict(index=index,delta=list(update['delta_rotation'])))
    return dict(local_pose=result,diagnostics=diagnostics,evidence='recovered weighted orientation; caller-chosen order/mapping')

def landing_alignment(basis,source,target,elapsed,horizon,minimum_horizon,start_marker=0.):
    weight=landing_pose.alignment_weight(elapsed,horizon,minimum_horizon,start_marker)
    return dict(basis=landing_pose.align_basis(basis,source,target,weight),weight=weight,evidence='recovered local pose alignment; caller-supplied inputs')
