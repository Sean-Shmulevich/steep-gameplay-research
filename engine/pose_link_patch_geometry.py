"""Multi-contact centroid/spread; LINK_SOLVER.md, Multi-row contact patch geometry."""
import math
from reference.central_impulse import f32


def contact_patch_geometry(basis, center_world, local_arms):
    """Transform one to four supplied offset-relative arms and average their spread.

    Center is the already transformed body offset, not body translation alone.
    Preserve world-point averaging before subtracting the center again.
    """
    def vector(v):
        if len(v)!=3:raise ValueError('Three components required')
        result=[f32(x) for x in v]
        if not all(math.isfinite(x) for x in result):raise ValueError('Finite components required')
        return result
    if len(basis)!=3 or not 1<=len(local_arms)<=4:
        raise ValueError('Three basis rows and one to four local arms required')
    rows=[vector(v) for v in basis];center=vector(center_world)
    points=[];total=[0.0]*3;count=0.0
    for local in local_arms:
        arm=vector(local)
        point=[f32(f32(f32(rows[2][j]*arm[2])+f32(f32(rows[1][j]*arm[1])+f32(rows[0][j]*arm[0])))+center[j]) for j in range(3)]
        points.append(point);total=[f32(total[j]+point[j]) for j in range(3)];count=f32(count+1.0)
    inverse=f32(1.0/count);centroid=[f32(x*inverse) for x in total]
    distance_sum=0.0
    for point in points:
        delta=[f32(point[j]-centroid[j]) for j in range(3)]
        squared=[f32(x*x) for x in delta]
        distance=f32(math.sqrt(f32(f32(squared[0]+squared[1])+f32(squared[2]+0.0))))
        distance_sum=f32(distance_sum+distance)
    spread=f32(max(distance_sum,f32(.001))*inverse)
    return dict(world_points=points,centroid_world=centroid,
                centroid_arm=[f32(centroid[j]-center[j]) for j in range(3)],
                distance_sum=distance_sum,spread=spread)


def contact_patch_basis(normal, centroid_arm, motion1a0, motion1ac, spread):
    """Shared constraint directions with componentwise fallback-axis tests."""
    def vector(v):
        if len(v)!=3:raise ValueError('Three components required')
        result=[f32(x) for x in v]
        if not all(math.isfinite(x) for x in result):raise ValueError('Finite components required')
        return result
    n,arm,linear,angular=map(vector,(normal,centroid_arm,motion1a0,motion1ac))
    spread=f32(spread)
    if not math.isfinite(spread) or spread<=0:raise ValueError('Positive finite spread required')
    def cross(a,b):return [f32(f32(a[(i+1)%3]*b[(i+2)%3])-f32(b[(i+1)%3]*a[(i+2)%3])) for i in range(3)]
    spin=cross(angular,arm);motion=[f32(linear[i]+spin[i]) for i in range(3)]
    direction=[-x for x in n];candidate=cross(direction,motion);source='motion'
    if all(abs(x)<f32(.001) for x in candidate):
        candidate=cross(direction,[1.0,0.0,0.0]);source='axis_x'
        if all(abs(x)<f32(.001) for x in candidate):
            candidate=cross(direction,[0.0,1.0,0.0]);source='axis_y'
    squared=[f32(x*x) for x in candidate]
    length=f32(math.sqrt(f32(f32(squared[0]+squared[1])+f32(squared[2]+0.0))))
    if not length or not math.isfinite(length):raise ValueError('Nondegenerate shared tangent required')
    inverse=f32(1.0/length);first=[f32(x*inverse) for x in candidate]
    second=cross(direction,first)
    return dict(first=first,second=second,first_angular=cross(arm,first),
                second_angular=cross(arm,second),spread_direction=[f32(x*spread) for x in direction],
                point_motion=motion,source=source)


def pack_contact_patch_directions(row, basis):
    """Write reached shared-row fields10..7f, preserving all other bytes."""
    import struct
    if len(row)!=208:raise ValueError('Complete208-byte shared row required')
    row[0x10:0x20]=bytes(16)
    for axis in range(3):
        struct.pack_into('<4f',row,0x20+16*axis,basis['first'][axis],basis['second'][axis],0.0,0.0)
        struct.pack_into('<4f',row,0x50+16*axis,basis['first_angular'][axis],basis['second_angular'][axis],basis['spread_direction'][axis],0.0)
