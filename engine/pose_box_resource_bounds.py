"""Box resource bounds; LINK_SOLVER.md, Box resource bounds query."""
from reference.central_impulse import f32


def box_resource_bounds(extents, frame):
    """Return lowXYZ/highXYZ using native absolute-basis float32 arithmetic."""
    e=list(map(f32,extents));f=[list(map(f32,row)) for row in frame]
    radius=[f32(f32(f32(abs(f[0][j])*e[0])+f32(abs(f[1][j])*e[1]))
                 +f32(abs(f[2][j])*e[2])) for j in range(3)]
    return [f32(f[3][j]-radius[j]) for j in range(3)]+[f32(radius[j]+f[3][j]) for j in range(3)]
