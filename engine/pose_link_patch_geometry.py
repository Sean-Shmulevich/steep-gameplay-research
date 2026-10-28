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
