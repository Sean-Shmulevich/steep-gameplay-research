import struct
import unittest
from engine.pose_link_profiles import resolve_pose_link_profiles


class ProfileTests(unittest.TestCase):
    def resource(self,kind):
        return dict(kind28=kind,default20=99,map60={2:3},table50={3:101},
                    mapb0={(0x20005>>1):4},tablea0={4:102})

    def test_paired_resources_share_payload_selector(self):
        payload=bytearray(288);struct.pack_into('<I',payload,0x3c,0x20005)
        struct.pack_into('<HH',payload,0x48,1,0)
        resources={10:self.resource(0x8006),20:self.resource(7)}
        actual=resolve_pose_link_profiles(dict(entries=[20,10]),dict(entries=[20]),payload,resources=resources)
        self.assertEqual(actual,(101,102))

    def test_absent_map_falls_back_and_zero_selected_profile_is_preserved(self):
        payload=bytearray(288);r=self.resource(6);r['map60']=None
        self.assertEqual(resolve_pose_link_profiles(dict(entries=[10]),dict(entries=[10]),payload,resources={10:r}),(99,99))
        r['map60']={0:0};r['table50']={0:0}
        self.assertEqual(resolve_pose_link_profiles(dict(entries=[10]),dict(entries=[10]),payload,resources={10:r}),(0,0))

    def test_unknown_kind_needs_no_unused_maps(self):
        payload=bytearray(288);r=dict(kind28=8,default20=17)
        self.assertEqual(resolve_pose_link_profiles(dict(entries=[10]),dict(entries=[10]),payload,resources={10:r}),(17,17))

    def test_kind7_ignores_detail_low_bit(self):
        p=bytearray(288);r=self.resource(7)
        for detail in (0x20004,0x20005):
            struct.pack_into('<I',p,0x3c,detail)
            self.assertEqual(resolve_pose_link_profiles(dict(entries=[10]),dict(entries=[10]),p,resources={10:r}),(102,102))

    def test_selected_profiles_feed_response_instead_of_defaults(self):
        from engine.pose_link_coefficients import link_response_coefficients
        payload=bytearray(288)
        struct.pack_into('<I',payload,0x3c,0x20005)
        resources={10:self.resource(6),20:self.resource(7)}
        tokens=resolve_pose_link_profiles(dict(entries=[10]),dict(entries=[20]),payload,resources=resources)
        profiles={101:dict(field30=4,field40=9,field60=4,field64=2),
                  102:dict(field30=6,field40=3,field60=8,field64=4)}
        modes=dict(field30=0,field40=1,field60=0,field64=0)
        result=link_response_coefficients(*(profiles[t] for t in tokens),modes,
                    context_scalar=2,default_factor=9,context_flags=12)
        self.assertEqual(result['combined30'],4)
        self.assertEqual(result['combined40'],9)
        self.assertEqual(result['response'],-0.5)
        self.assertEqual(result['seed_gate'],0.75)
