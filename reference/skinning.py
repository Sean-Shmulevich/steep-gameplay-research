"""Portable reference for documented four/eight-influence position shaders.
Only scalar math is bundled here; all tests use synthetic data.
"""
import math

def matrix_multiply(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def transform_rows(rows,position):
    v=tuple(position)+(1,)
    return tuple(sum(rows[i][k]*v[k] for k in range(4)) for i in range(3))
def shader_skin_position(position,weights,joint_indices,palette,influences):
    """The shader consumes exactly influences entries, including zero weights.
    Palette entries are three four-float rows. No implicit weight normalization.
    """
    if influences not in (4,8):raise ValueError('Documented programs have four or eight influences')
    output=[0.,0.,0.]
    for k in range(influences):
        transformed=transform_rows(palette[joint_indices[k]],position)
        for i in range(3):output[i]+=weights[k]*transformed[i]
    return tuple(output)
def float_weights_from_authored_bytes(values):
    """Normalized-byte interpretation; GPU resource conversion not yet specified."""
    return tuple(x/255 for x in values)
def model_matrix(transform):
    x,y,z,w=transform['quaternion_xyzw'];t=transform['translation']
    return [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),t[0]],
            [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),t[1]],
            [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),t[2]],
            [0,0,0,1]]
def palette_from_model_and_inverse_bind(model,inverse_bind):
    """Compatible palette construction, not a fully specified runtime upload path."""
    return matrix_multiply(model,inverse_bind)[:3]
def remap_mesh_joints(resolved_indices):
    """Runtime remap fallback: missing entries alias first resolved joint.
    If no entries resolve, the mapping is cleared. None denotes missing.
    """
    first=next((x for x in resolved_indices if x is not None),None)
    if first is None:return []
    return [first if x is None else x for x in resolved_indices]
def native_skinning_palette(inverse_binds,joint_map,model_pose,global_pose_root,origin_shift,scale):
    """Documented renderer producer. Output has three four-float rows per slot.
    For a null model pose, no origin shift or inverse binds are applied.
    """
    S=[[scale,0,0,0],[0,scale,0,0],[0,0,scale,0],[0,0,0,1]]
    if model_pose is None:return [S[:3] for _ in inverse_binds]
    scaled=abs(scale-1)>9.999999747378752e-6
    out=[]
    for inverse_bind,index in zip(inverse_binds,joint_map):
        if index is None:
            if not scaled:raise ValueError('Unit-scale runtime branch has no missing-joint guard')
            M=[row[:] for row in S]
        else:
            world=matrix_multiply(model_matrix(global_pose_root),model_matrix(model_pose[index]))
            bind=matrix_multiply(S,inverse_bind) if scaled else inverse_bind
            M=matrix_multiply(world,bind)
        for i in range(3):M[i][3]+=origin_shift[i]
        out.append(M[:3])
    return out
def anchored_render_matrix(selected_bone,authored_anchor,global_root=None,requires_root=False,anchor_specified=True,previous_output=None):
    """Documented gate behavior: missing anchor/bone leaves previous output intact."""
    if not anchor_specified or selected_bone is None:return previous_output
    bone=model_matrix(selected_bone)
    if requires_root:
        if global_root is None:raise ValueError('Root transform required by the pose')
        bone=matrix_multiply(model_matrix(global_root),bone)
    return matrix_multiply(bone,authored_anchor)
