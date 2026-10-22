"""Recovered four-row transform helpers with float32 operation order.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Transform multiplication convention.
Rows are four consecutive groups in memory; this does not name gameplay axes.
The transpose helper is an inverse only for an orthonormal linear part.
"""
import math
import struct


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _rows(matrix):
    if len(matrix) != 4 or any(len(row) != 4 for row in matrix):
        raise ValueError('four rows of four values required')
    result = [[_f32(x) for x in row] for row in matrix]
    if any(not math.isfinite(x) for row in result for x in row):
        raise ValueError('finite float32 inputs required')
    return result


def _dot(a, b):
    products = [_f32(x*y) for x, y in zip(a, b)]
    value = products[0]
    for product in products[1:]:
        value = _f32(value+product)
    return value


def compose_transform(destination, source):
    """Return source * destination in the stated row-storage interpretation.

    Native overwrites destination after loading all inputs. This pure adapter
    snapshots both inputs and supports using the same matrix for both arguments.
    Each multiply/add rounds separately; no fused multiply-add is used.
    Finite inputs with nonoverflowing intermediates are the validated domain.
    """
    a, b = _rows(destination), _rows(source)
    return [[_dot(b[i], [a[k][j] for k in range(4)]) for j in range(4)]
            for i in range(4)]


def transpose_affine_transform(matrix):
    """Transpose the linear 3x3 and replace translation with negative row dots.

    This reproduces the helper even for nonorthonormal input; it does not divide
    by scale or determinant. Input homogeneous lanes are replaced by 0,0,0,1.
    """
    a = _rows(matrix)
    return [[a[j][i] for j in range(3)]+[0.0] for i in range(3)]+[
        [-_dot(a[i][:3], a[3][:3]) for i in range(3)]+[1.0]]


def recompute_accessor_local(parent, incoming, previous):
    """Recovered local matrix update including the inclusive translation deadband.

    Called only for valid descriptors with packet bit 1 set. Gates, locks and
    child traversal are external. Preserve all three old translation coordinates
    together when every float32 difference is <= float32(0.001); force w=1 only
    on that preservation branch. Candidate rotation always replaces old rotation.
    The threshold's world units are not inferred here.
    """
    old = _rows(previous)
    candidate = compose_transform(transpose_affine_transform(parent), incoming)
    threshold = _f32(0.001)
    preserve = all(abs(_f32(candidate[3][i]-old[3][i])) <= threshold
                   for i in range(3))
    if preserve:
        candidate[3] = old[3][:3]+[1.0]
    return dict(transform=candidate, translation_preserved=preserve)


def child_transform_candidate(mode, local, incoming, cached=None, *, reciprocal_sqrt=None):
    """Recovered child modes 0, 1, 2, 3, 5; no inferred mode names.

    Modes 0/2 require explicit reciprocal-square-root seed service.
    Other uint32 modes produce no candidate before the optional modifier path.
    Cached transform is supplied getter output, not a claimed atomic snapshot.
    """
    if type(mode) is not int or not 0 <= mode <= 0xffffffff:
        raise ValueError('uint32 mode required')
    if mode in (0, 2) and not callable(reciprocal_sqrt):
        raise NotImplementedError('reciprocal-square-root seed service required')
    if mode not in (0, 1, 2, 3, 5):
        return None
    a, b = _rows(local), _rows(incoming)
    if mode in (0, 2):
        result = normalize_transform_basis(compose_transform(b, a), reciprocal_sqrt)
        if mode == 2:
            result[3] = _rows(cached)[3][:3]+[1.0]
        return result
    if mode == 5:
        return compose_transform(b, a)
    c = _rows(cached)
    if mode == 1:
        return c[:3]+[compose_transform(b, a)[3]]
    offset = [_f32(_f32(_f32(a[3][2]*c[2][j])+_f32(a[3][1]*c[1][j]))+
                   _f32(a[3][0]*c[0][j])) for j in range(3)]
    return c[:3]+[[_f32(b[3][j]+offset[j]) for j in range(3)]+[1.0]]


def prepare_child_transform_packet(mode, local, incoming, cached, flags, modifier=None,
                                   *, reciprocal_sqrt=None):
    """Prepare the recovered child packet; native writer/dispatch remain external.

    modifier(candidate) mutates the candidate in place. If a mode produces none,
    a supplied modifier receives a copy of cached instead. Both output slots
    refer to the same Python matrix. Callback signature and validation authored.
    """
    if type(flags) is not int or not 0 <= flags <= 0xffffffff:
        raise ValueError('uint32 flags required')
    if modifier is not None and not callable(modifier):
        raise TypeError('callable modifier required')
    candidate = child_transform_candidate(mode, local, incoming, cached,
                                        reciprocal_sqrt=reciprocal_sqrt)
    if modifier is not None:
        if candidate is None:
            candidate = _rows(cached)
        modifier(candidate)
        candidate = _rows(candidate)
    if candidate is None:
        return None
    return dict(first_transform=candidate, second_transform=candidate,
                flags=flags & 0xfffffffd)


def normalize_transform_basis(matrix, reciprocal_sqrt):
    """Recovered basis rebuild with explicit hardware reciprocal-sqrt seeds.

    Normalize row1, normalize cross(row1,row2), then normalize cross(new0,new1).
    Input row0 is discarded. Positive nondegenerate lengths are required by this
    authored adapter; native degenerate/nonfinite behavior remains unmodeled.
    """
    a = _rows(matrix)
    def normalize(v):
        squares = [_f32(x*x) for x in v]
        n = _f32(squares[0]+_f32(squares[1]+squares[2]))
        if not math.isfinite(n) or n <= 0:
            raise ValueError('positive finite basis length required')
        seed = _f32(reciprocal_sqrt(n))
        factor = _f32(_f32(3.0-_f32(_f32(seed*n)*seed))*_f32(0.5*seed))
        return [_f32(x*factor) for x in v]
    def cross(x, y):
        return [_f32(_f32(x[j]*y[k])-_f32(y[j]*x[k]))
                for j,k in ((1,2),(2,0),(0,1))]
    row1 = normalize(a[1][:3])
    row0 = normalize(cross(row1, a[2][:3]))
    row2 = normalize(cross(row0, row1))
    return [row0+[0.0], row1+[0.0], row2+[0.0], a[3][:3]+[1.0]]


def select_skeleton_link_transform(mode, normalized, provider, local, cached):
    """Recovered SkeletonComponent linked-object mode switch, after normalization.

    Unlike hierarchy propagation, mode 5 does not enable publication here. The
    precomputed matrix survives for an optional modifier even for unknown modes.
    Provider acquisition/normalization and final callback effects are external.
    """
    if type(mode) is not int or not 0 <= mode <= 0xffffffff:
        raise ValueError('uint32 mode required')
    result = _rows(normalized)
    if mode == 1:
        result = _rows(cached)[:3]+[result[3][:3]+[1.0]]
    elif mode == 2:
        result[3] = _rows(cached)[3][:3]+[1.0]
    elif mode == 3:
        result = child_transform_candidate(3, local, provider, cached)
    return dict(transform=result, publish=mode in (0,1,2,3))
