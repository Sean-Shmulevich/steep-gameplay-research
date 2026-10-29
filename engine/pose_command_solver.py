"""Command-row numerical solver; LINK_SOLVER.md, Command constraint solving."""
import math
import struct
from reference.central_impulse import f32


def _read(data, off):
    values=struct.unpack_from('<4f',data,off)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Finite command solver inputs required')
    return values


def _put(data,off,values):struct.pack_into('<4f',data,off,*values)
def _mul(a,b):return [f32(x*y) for x,y in zip(a,b)]
def _add(a,b):return [f32(x+y) for x,y in zip(a,b)]
def _dot(a,b):
    v=_mul(a,b)
    return f32(f32(v[0]+v[1])+f32(v[2]+0.0))
def _tensor(data,v):
    x,y,z=[_read(data,i*16) for i in range(3)]
    return [f32(f32(z[j]*v[2])+f32(f32(y[j]*v[1])+f32(x[j]*v[0]))) for j in range(4)]


def _commands(row):
    if len(row)<912:raise ValueError('Complete command row required')
    count=struct.unpack_from('<i',row,0x24)[0]
    if count>6:raise ValueError('Command count exceeds retained row capacity')
    return range(max(0,count))


def _endpoints(row):
    first,second=struct.unpack_from('<2H',row)
    return [(first,0x30,0x40)] if row[0x20] else [(first,0x30,0x40),(second,0x50,0x60)]


def _apply(row,i,amount,body_data,body_state):
    # Read/write each endpoint in sequence, including coincident body indices.
    for index,lin,ang in _endpoints(row):
        data,state=body_data[index],body_state[index]
        linear=_mul(_read(row,i*128+lin),_mul(_read(data,48),amount))
        _put(state,0,_add(_read(state,0),linear))
        angular=_tensor(data,_mul(_read(row,i*128+ang),amount))
        _put(state,16,_add(_read(state,16),angular))


def prepare_pose_command_row(row,*,body_data,body_state):
    """Compute negative effective-mass reciprocals and apply cached impulses."""
    for i in _commands(row):
        terms=[]
        for index,lin,ang in _endpoints(row):
            d=body_data[index];l=_read(row,i*128+lin);a=_read(row,i*128+ang)
            terms.append((_dot(l,_mul(l,_read(d,48))),_dot(_tensor(d,a),a)))
        denominator=f32(terms[0][1]+terms[0][0])
        if len(terms)>1:
            denominator=f32(denominator+terms[1][0])
            denominator=f32(denominator+terms[1][1])
        if not denominator or not math.isfinite(denominator):
            raise ValueError('Finite nonsingular command denominator required')
        inverse=f32(1.0/-denominator)
        _put(row,0x330+i*16,[inverse,inverse,inverse,0.0])
        _apply(row,i,_read(row,0xa0+i*128),body_data,body_state)


def iterate_pose_command_row(row,*,body_data,body_state):
    """Project each command impulse to its bounds, then apply its increment."""
    for i in _commands(row):
        terms=[]
        for index,lin,ang in _endpoints(row):
            state=body_state[index]
            terms.append((_dot(_read(state,0),_read(row,i*128+lin)),
                          _dot(_read(state,16),_read(row,i*128+ang))))
        speed=f32(terms[0][1]+terms[0][0])
        if len(terms)>1:
            speed=f32(speed+terms[1][0]);speed=f32(speed+terms[1][1])
        off=i*128;old=_read(row,off+0xa0)
        target=_read(row,off+0x70);lower=_read(row,off+0x80);upper=_read(row,off+0x90)
        inverse=_read(row,0x330+i*16)
        candidate=[f32(f32(inv*f32(speed-t))+o) for inv,t,o in zip(inverse,target,old)]
        # SSE min/max return their second operand on equal values.
        capped=[u if u<c else c for u,c in zip(upper,candidate)]
        projected=[c if c>lo else lo for c,lo in zip(capped,lower)]
        delta=[f32(v-o) for v,o in zip(projected,old)]
        _apply(row,i,delta,body_data,body_state)
        _put(row,off+0xa0,_add(_read(row,off+0xa0),delta))
