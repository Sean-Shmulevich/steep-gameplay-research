"""Offline JSON inspector for body integration and secondary-state application.

Evidence: LINK_SOLVER.md, Runnable body integration inspection.
"""
import argparse
import json
import math
from pathlib import Path
import struct
from reference.central_impulse import f32
from .pose_body_integration import integrate_pose_body
from .pose_body_secondary_update import apply_pose_secondary_body_state


def inspect(document):
    if document.get('schema') != 'pose-body-integration-v1':
        raise ValueError('Unsupported schema')
    if document.get('provenance') not in ('authored_synthetic', 'caller_supplied_observation'):
        raise ValueError('Explicit provenance required')
    data = document['inputs']
    body = bytearray.fromhex(data['body_hex'])
    if not 0x1b8 <= len(body) <= 4096:
        raise ValueError('Bounded complete retained body required')
    replies = data['trig_responses']
    if len(replies) > 4096:
        raise ValueError('Bounded explicit response list required')
    calls = []
    def finite(value):
        if type(value) not in (int,float) or not math.isfinite(f32(value)):
            raise ValueError('Finite float32 value required')
        return f32(value)
    def trig(half):
        if len(calls) >= len(replies):
            raise ValueError('Missing explicit sine/cosine response')
        reply = replies[len(calls)]
        if struct.pack('<f',finite(reply['half_angle'])) != struct.pack('<f',half):
            raise ValueError('Half-angle response does not match this call')
        sine,cosine = finite(reply['sine']),finite(reply['cosine'])
        calls.append(dict(half_angle=half,sine=sine,cosine=cosine))
        return sine,cosine
    def view(raw):
        return dict(basis=[list(struct.unpack_from('<3f',raw,o)) for o in (0x40,0x50,0x60)],
                    translation=list(struct.unpack_from('<3f',raw,0x70)),
                    motion1a0=list(struct.unpack_from('<3f',raw,0x1a0)),
                    motion1ac=list(struct.unpack_from('<3f',raw,0x1ac)))
    before = view(body)
    mode = document['sequence']
    if mode == 'body_integration':
        integrate_pose_body(body,finite(data['scalar']),half_angle_trig=trig)
    elif mode == 'secondary_application':
        if 'scalar' in data:
            raise ValueError('Secondary application uses the recovered fixed scalar1.0')
        state = bytes.fromhex(data['state_hex'])
        if len(state) != 32:
            raise ValueError('Complete32-byte secondary state required')
        apply_pose_secondary_body_state([1],bodies={1:body},body_state=[state],
            update_body=lambda token,raw,s:integrate_pose_body(raw,s,half_angle_trig=trig))
    else:
        raise ValueError('Explicit supported sequence required')
    if len(calls) != len(replies):
        raise ValueError('Unused scalar-library responses')
    output = dict(schema=document['schema'],provenance=document['provenance'],sequence=mode,
                  before=before,after=view(body),body_hex=body.hex(),trig_calls=calls,
                  limits=['Constructor-selected body method only; no live class identification',
                          'Sine/cosine responses supplied explicitly, not computed by a recovered library',
                          'Secondary state supplied; row generation and solve are not run',
                          'JSON schema and validation are authored inspection policy'])
    json.dumps(output,allow_nan=False)
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    output=json.dumps(inspect(json.loads(args.input.read_text())),indent=2,allow_nan=False)+'\n'
    if args.output:args.output.write_text(output)
    else:print(output,end='')


if __name__ == '__main__':main()
