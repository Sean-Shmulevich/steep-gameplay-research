"""Z-up, XYZW numerical helpers for our integration, not original source."""
import math

def finite(values):
    if not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in values):
        raise ValueError("Expected finite numerical components")
    return list(values)

def vector(value,n=3):
    if not isinstance(value,(list,tuple)) or len(value)!=n:raise ValueError(f"Expected {n} components")
    return finite(value)

def normalize(v):
    v=vector(v,len(v));length=math.sqrt(sum(x*x for x in v))
    if length<1e-12:raise ValueError("Zero direction")
    return [x/length for x in v]

def rotate(q,v):
    from reference.skeleton import rotate as impl
    return list(impl(normalize(vector(q,4)),vector(v)))
