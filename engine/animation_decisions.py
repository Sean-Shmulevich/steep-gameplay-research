"""Recovered scalar comparison and bounded authored-record decoding.

Evidence: docs/systems/animations/decisions/CLIENT_GUIDE.txt.
Graph expression schema and validation limits are independent API choices.
"""
import math
import struct
import zlib

OPERATORS={0:'Equals',1:'GreaterThan',2:'GreaterThanOrEquals',3:'LessThan',4:'LessThanOrEquals',5:'NotEquals'}


def _f32(value):
    try:return struct.unpack('<f',struct.pack('<f',value))[0]
    except OverflowError:return math.copysign(math.inf,value)


EPSILON=_f32(1e-5)


def scalar_compare(operator,left,right):
    a,b=_f32(left),_f32(right)
    if isinstance(operator,str):operator=next((k for k,v in OPERATORS.items() if v==operator),-1)
    if operator==0:return abs(_f32(a-b))<=EPSILON
    if operator==1:return a>b
    if operator==2:return a>=b
    if operator==3:return a<b
    if operator==4:return a<=b
    if operator==5:return not(abs(_f32(a-b))<=EPSILON)
    return False


def decode_comparison(payload,typed_inputs):
    """Only the verified constant-op / scalar parameter / float constant form."""
    if len(payload)!=184 or struct.unpack_from('<I',payload)[0]!=zlib.crc32(b'AtomCompareValuesNode'):
        raise ValueError('unsupported comparison record')
    for offset in (16,72,128):
        if struct.unpack_from('<I',payload,offset)[0]!=zlib.crc32(b'AtomInputPort'):
            raise ValueError('input port signature mismatch')
    if tuple(struct.unpack_from('<I',payload,o+4)[0] for o in (16,72,128))!=(4,0,3):
        raise ValueError('unresolved comparison binding variant')
    operator=struct.unpack_from('<I',payload,24)[0];index=struct.unpack_from('<I',payload,80)[0]
    if operator not in OPERATORS or index>=len(typed_inputs) or typed_inputs[index].get('type')!='scalar':
        raise ValueError('unresolved comparator or parameter')
    name=typed_inputs[index].get('name')
    if not isinstance(name,str) or not name:raise ValueError('missing scalar parameter name')
    return {'parameter':name,'operator':OPERATORS[operator],'threshold':struct.unpack_from('<f',payload,144)[0]}


def predicate_expression(predicate):
    expression={'compare':predicate['operator'],'left':{'input':predicate['parameter']},'right':predicate['threshold']}
    validate_expression(expression)
    return expression


def validate_expression(value,depth=0):
    if depth>64:raise ValueError('scalar expression depth limit')
    if isinstance(value,dict):
        if set(value)=={'input'}:
            if not isinstance(value['input'],str) or not value['input']:raise ValueError('invalid scalar input name')
        elif set(value)=={'compare','left','right'}:
            if type(value['compare']) not in (int,str):raise ValueError('invalid comparison operator type')
            validate_expression(value['left'],depth+1);validate_expression(value['right'],depth+1)
        else:raise ValueError('invalid scalar expression')
    elif not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('invalid graph scalar')


def evaluate_expression(value,inputs):
    validate_expression(value)
    def evaluate(v):
        if isinstance(v,dict):
            if 'input' in v:
                if v['input'] not in inputs:raise ValueError('unresolved graph scalar input')
                result=inputs[v['input']]
                if not isinstance(result,(int,float)) or not math.isfinite(result):raise ValueError('invalid graph scalar input')
                return result
            return float(scalar_compare(v['compare'],evaluate(v['left']),evaluate(v['right'])))
        return float(v) if isinstance(v,bool) else v
    return evaluate(value)
