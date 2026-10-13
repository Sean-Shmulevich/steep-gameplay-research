import copy
import json
import unittest
from engine.rig_assembly import assemble, AssemblyError


def bone(name, parent=-1, xyz=(0,0,0), h=None):
    b = dict(name=name, parent_index=parent,
             local_bind=dict(translation=list(xyz), quaternion_xyzw=[0,0,0,1]))
    if h is not None:
        b['binding_hash'] = h
    return b


def policy(duplicates='reuse_identical', match='binding_hash', roots='keep', **kw):
    return dict(duplicates=duplicates, match_by=match, roots=roots, **kw)


class RigAssemblyTests(unittest.TestCase):
    def test_shared_root_parent_remapping_and_local_transforms(self):
        base = {'bones':[bone('root', h=1), bone('hand', 0, (0,2,0),2)]}
        gear = {'bones':[bone('hand',1,(0,2,0),2), bone('root',h=1),bone('pole',0,(1,0,0),3)]}
        result = assemble(base,[{'id':'gear','rig':gear}],policy=policy())
        self.assertEqual(result['source_to_assembled'], {'base':[0,1], 'gear':[1,0,2]})
        self.assertEqual(result['rig']['bones'][2]['parent_index'],1)
        self.assertEqual(result['rig']['bones'][2]['local_bind']['translation'],[1,0,0])
        self.assertEqual(len(result['diagnostics']),2)

    def test_policy_required_and_duplicate_rejection_has_diagnostics(self):
        b={'bones':[bone('root',h=1)]}
        with self.assertRaises(AssemblyError):
            assemble(b,[],policy={})
        with self.assertRaises(AssemblyError) as ctx:
            assemble(b,[{'id':'x','rig':b}],policy=policy('error'))
        self.assertEqual(ctx.exception.diagnostics[0]['type'],'duplicate_identity')

    def test_conflicting_bind_requires_explicit_existing_policy(self):
        base={'bones':[bone('root',h=1)]}
        addon={'bones':[bone('root',xyz=(1,0,0),h=1)]}
        with self.assertRaises(AssemblyError):
            assemble(base,[{'id':'x','rig':addon}],policy=policy())
        r=assemble(base,[{'id':'x','rig':addon}],policy=policy('reuse_existing'))
        self.assertEqual(r['rig'],base)
        self.assertFalse(r['diagnostics'][0]['parent_and_bind_equivalent'])

    def test_name_matching_does_not_hide_conflicting_hash(self):
        base={'bones':[bone('root',h=1)]}
        addon={'bones':[bone('root',h=2)]}
        with self.assertRaises(AssemblyError) as ctx:
            assemble(base,[{'id':'x','rig':addon}],policy=policy(match='name'))
        self.assertTrue(ctx.exception.diagnostics[0]['hash_disagrees'])

    def test_distinct_names_shared_hash_preserved_as_ambiguous(self):
        base={'bones':[bone('root',h=1),bone('child',0,h=1)]}
        r=assemble(base,[],policy=policy(match='name'))
        self.assertEqual(r['hash_to_indices'],{'1':[0,1]})
        self.assertEqual(r['diagnostics'][0]['type'],'hash_collision')

    def test_distinct_hash_same_output_name_is_rejected(self):
        base={'bones':[bone('root',h=1)]}
        addon={'bones':[bone('root',h=2)]}
        with self.assertRaises(AssemblyError) as ctx:
            assemble(base,[{'id':'x','rig':addon}],policy=policy('reuse_existing'))
        self.assertEqual(ctx.exception.diagnostics[0]['type'],'name_collision')

    def test_explicit_attachment_keeps_local_offset(self):
        base={'bones':[bone('hand',xyz=(0,2,0),h=1)]}
        gear={'bones':[bone('tool',xyz=(1,0,0),h=2)]}
        r=assemble(base,[{'id':'gear','rig':gear}],policy=policy(roots='attach',attachments={'gear':{'name':'hand'}}))
        self.assertEqual(r['rig']['bones'][1]['parent_index'],0)
        self.assertEqual(r['rig']['bones'][1]['local_bind']['translation'],[1,0,0])
        self.assertEqual(r['diagnostics'][0]['type'],'root_attached')

    def test_ambiguous_attachment_hash_fails(self):
        base={'bones':[bone('root',h=1),bone('hand',0,h=1)]}
        gear={'bones':[bone('tool',h=2)]}
        with self.assertRaises(AssemblyError):
            assemble(base,[{'id':'gear','rig':gear}],policy=policy(match='name',roots='attach',attachments={'gear':{'binding_hash':1}}))

    def test_sign_equivalent_quaternion_can_reuse(self):
        base={'bones':[bone('root',h=1)]}
        gear=copy.deepcopy(base)
        gear['bones'][0]['local_bind']['quaternion_xyzw']=[0,0,0,-1]
        self.assertEqual(assemble(base,[{'id':'gear','rig':gear}],policy=policy())['source_to_assembled']['gear'],[0])

    def test_invalid_cycles_duplicate_source_and_nonfinite_rejected(self):
        for bones in [[bone('root',0,h=1)], [bone('root',h=1),bone('alias',h=1)],
                      [bone('root',xyz=(float('nan'),0,0),h=1)]]:
            with self.assertRaises(AssemblyError):
                assemble({'bones':bones},[],policy=policy('reuse_existing'))

    def test_deterministic_json_roundtrip_and_input_immutability(self):
        base={'bones':[bone('root',h=1)]}
        gear={'bones':[bone('child',h=2)]}
        before=copy.deepcopy((base,gear))
        a=assemble(base,[{'id':'gear','rig':gear}],policy=policy())
        b=assemble(base,[{'id':'gear','rig':gear}],policy=policy())
        self.assertEqual(a,b)
        self.assertEqual(json.loads(json.dumps(a)),a)
        self.assertEqual((base,gear),before)


if __name__ == '__main__':
    unittest.main()
