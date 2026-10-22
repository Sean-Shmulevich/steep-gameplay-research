#!/usr/bin/env python3
"""Compare a bank parent with preparation from the passively sampled owner matrix.

Equality is not freshness, atomicity, world-space identity or writer attribution.
"""
import argparse,json,math,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reference.skeleton_parent_transform import prepare_skeleton_parent_transform


def compare_parent(capture):
    compared=0;equal=0;indirect=0;errors=[];deltas=[];rotation_deltas=[];position_matches=0;rotation_matches=0;xyz_matches=0;w_patterns={};reset_matches=0
    for index,row in enumerate(capture['rows']):
        response=row['animation'];p=response.get('result',{})
        if response.get('status')!='completed' or not p.get('found'):continue
        try:
            m=p['owner_matrix']
            if len(m)!=16:raise ValueError('owner matrix requires sixteen lanes')
            expected=prepare_skeleton_parent_transform([m[:4],m[4:8],m[8:12]],m[12:])
            actual_position=p['parent_vector'];actual_rotation=p['parent_rotation']
            if len(actual_position)!=4 or len(actual_rotation)!=4 or not all(math.isfinite(x) for x in actual_position+actual_rotation):
                raise ValueError('invalid parent record')
            actual_position=list(struct.unpack('<4f',struct.pack('<4f',*actual_position)))
            actual_rotation=list(struct.unpack('<4f',struct.pack('<4f',*actual_rotation)))
            reset_position=expected['parent_position'][:3]+(1.,)
            reset_matches+=int(struct.pack('<4f',*actual_position)==struct.pack('<4f',*reset_position) and
                               struct.pack('<4f',*actual_rotation)==struct.pack('<4f',*expected['parent_rotation']))
            position_match=struct.pack('<4f',*actual_position)==struct.pack('<4f',*expected['parent_position'])
            rotation_match=struct.pack('<4f',*actual_rotation)==struct.pack('<4f',*expected['parent_rotation'])
            compared+=1;equal+=int(position_match and rotation_match);indirect+=int(bool(p['owner_accessor_present']))
            position_matches+=int(position_match);rotation_matches+=int(rotation_match)
            xyz_matches+=int(struct.pack('<3f',*actual_position[:3])==struct.pack('<3f',*expected['parent_position'][:3]))
            w_bits=struct.pack('<f',actual_position[3]).hex()
            w_patterns[w_bits]=w_patterns.get(w_bits,0)+1
            rotation_deltas.append(max(abs(a-b) for a,b in zip(actual_rotation,expected['parent_rotation'])))
            deltas.append(math.dist(actual_position[:3],expected['parent_position'][:3]))
        except (KeyError,TypeError,ValueError,OverflowError,struct.error) as exc:
            errors.append({'row':index,'error':str(exc)})
    return dict(schema='animation-owner-parent-comparison-v1',compared=compared,
                bit_exact_parent_matches=equal,reset_parent_formula_matches=reset_matches,
                bit_exact_translation_matches=position_matches,
                bit_exact_rotation_matches=rotation_matches,bit_exact_xyz_matches=xyz_matches,
                parent_w_little_endian_bit_patterns=w_patterns,indirect_accessor_samples=indirect,
                max_rotation_component_difference=max(rotation_deltas,default=None),
                min_translation_difference=min(deltas,default=None),max_translation_difference=max(deltas,default=None),
                errors=errors,comparison_completed=compared>0 and not errors,
                freshness_established=False,writer_attribution_established=False,world_space_established=False)


def compare_owner_body(capture):
    """Compare stored owner lanes with bracketing physics-body observations.

    No time alignment or coordinate equivalence follows from numerical proximity.
    """
    compared=0;skipped=0;distances=[];basis_differences=[]
    for row in capture['rows']:
        responses=[row.get(k,{}) for k in ('player','animation','player_after')]
        if any(r.get('status')!='completed' for r in responses):skipped+=1;continue
        before,pose,after=[r['result'] for r in responses]
        if not pose.get('found') or not before.get('identity')==pose.get('identity')==after.get('identity'):
            skipped+=1;continue
        m=pose['owner_matrix']
        if len(m)!=16 or not all(math.isfinite(x) for x in m):raise ValueError('invalid stored owner matrix')
        for body in (before,after):
            position=body['position'];axes=body['axes']
            if len(position)!=3 or len(axes)!=3 or any(len(v)!=3 for v in axes):raise ValueError('invalid body transform')
            if not all(math.isfinite(x) for x in position+sum(axes,[])):raise ValueError('nonfinite body transform')
            distances.append(math.dist(m[12:15],position))
            basis_differences.append(max(abs(m[4*i+j]-axes[i][j]) for i in range(3) for j in range(3)))
        compared+=1
    return dict(compared_identity_brackets=compared,skipped=skipped,
                min_translation_distance=min(distances,default=None),max_translation_distance=max(distances,default=None),
                max_stored_basis_lane_difference=max(basis_differences,default=None),
                atomic_snapshot=False,coordinate_equivalence_established=False,
                units='stored engine units; before and after body reads are sequential')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('capture',type=Path);args=parser.parse_args()
    data=json.loads(args.capture.read_text())
    if 'probe' in data:data=data['probe']
    if 'animation' in data:data=data['animation']
    result=compare_parent(data);print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['comparison_completed'] else 1)
