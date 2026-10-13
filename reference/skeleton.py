"""Hierarchy math with synthetic fixtures only; no decoded bind poses bundled."""
import math

def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def qmul(a,b):
    av=a[:3];bv=b[:3];c=cross(av,bv)
    return tuple(a[3]*bv[i]+b[3]*av[i]+c[i] for i in range(3))+(a[3]*b[3]-sum(av[i]*bv[i] for i in range(3)),)
def rotate(q,v):
    t=tuple(2*x for x in cross(q[:3],v));c=cross(q[:3],t)
    return tuple(v[i]+q[3]*t[i]+c[i] for i in range(3))
def compose(parent,local):
    p=rotate(parent['quaternion_xyzw'],local['translation'])
    return {'translation':[parent['translation'][i]+p[i] for i in range(3)],'quaternion_xyzw':list(qmul(parent['quaternion_xyzw'],local['quaternion_xyzw']))}
def native_compose(parent,local):
    """Documented normalized hierarchy kernel; scalar form of its SIMD rotation."""
    a=parent['quaternion_xyzw'];v=local['translation'];dot=sum(a[i]*v[i] for i in range(3));c=cross(a[:3],v)
    t=[parent['translation'][i]+2*(dot*a[i]+c[i]*a[3]+(a[3]*a[3]-.5)*v[i]) for i in range(3)]
    q=qmul(a,local['quaternion_xyzw']);length=math.sqrt(sum(x*x for x in q))
    return {'translation':t,'quaternion_xyzw':[x/length for x in q]}
def native_propagate(bones,locals=None,lod=7,minimum_lod=None,descendant_counts=None,previous_output=None):
    """Parent-first ordered kernel. LOD skips a bone and its contiguous subtree.
    Skipped outputs retain their prior contents. Zero quaternions are invalid.
    """
    locals=locals if locals is not None else [b['local_bind'] for b in bones]
    minimum_lod=minimum_lod if minimum_lod is not None else [0]*len(bones)
    descendant_counts=descendant_counts if descendant_counts is not None else [0]*len(bones)
    out=list(previous_output) if previous_output is not None else [None]*len(bones)
    identity={'translation':[0,0,0],'quaternion_xyzw':[0,0,0,1]}
    if not bones:return out
    out[0]=native_compose(identity,locals[0]);i=1
    while i<len(bones):
        if lod<minimum_lod[i]:i+=descendant_counts[i]+1;continue
        parent=bones[i]['parent_index']
        if parent<0 or parent>=i:raise ValueError('Runtime non-root requires an earlier parent')
        out[i]=native_compose(out[parent],locals[i]);i+=1
    return out
def native_model_to_local(bones,model):
    """Documented inverse conversion, all LOD gates accepted, separate output."""
    out=[]
    for i,b in enumerate(bones):
        if i==0:
            identity={'translation':[0,0,0],'quaternion_xyzw':[0,0,0,1]}
            out.append(native_compose(identity,model[i]));continue
        parent=model[b['parent_index']];q=parent['quaternion_xyzw'];delta=[model[i]['translation'][k]-parent['translation'][k] for k in range(3)]
        inv={'translation':[0,0,0],'quaternion_xyzw':[-q[0],-q[1],-q[2],q[3]]}
        out.append(native_compose(inv,{'translation':delta,'quaternion_xyzw':model[i]['quaternion_xyzw']}))
    return out
def inverse(transform):
    q=transform['quaternion_xyzw'];q=(-q[0],-q[1],-q[2],q[3]);t=rotate(q,[-x for x in transform['translation']])
    return {'translation':list(t),'quaternion_xyzw':list(q)}
def propagate(bones,locals=None):
    """Parent index -1 means root. Detect cyclic hierarchy; allow arbitrary order."""
    out={};active=set();locals=locals if locals is not None else [b['local_bind'] for b in bones]
    def visit(i):
        if i in out:return out[i]
        if i in active:raise ValueError('Cyclic hierarchy')
        active.add(i);parent=bones[i]['parent_index'];out[i]=locals[i] if parent<0 else compose(visit(parent),locals[i]);active.remove(i);return out[i]
    return [visit(i) for i in range(len(bones))]
def skinning_palette(bones,animated_local_pose):
    """Mathematical rigid palette. Runtime rendering palette path remains unresolved."""
    model=propagate(bones,animated_local_pose)
    return [compose(model[i],inverse(b['model_bind'])) for i,b in enumerate(bones)]
def apply(transform,point):
    p=rotate(transform['quaternion_xyzw'],point)
    return tuple(p[i]+transform['translation'][i] for i in range(3))
