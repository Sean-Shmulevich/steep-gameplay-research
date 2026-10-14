import struct
import unittest
from engine.animation_container import parse_clip_body
from engine.animation_corpus import inspect_clip


def obj(kind):return struct.pack('<BQI',0,0,kind)


def fixture(version=2,event=False,shared=False):
    result=struct.pack('<QIBfI',7,0x0fa3067f,1,1.,11)
    result+=struct.pack('<III',12,0,0) if version==2 else struct.pack('<I',0)
    result+=bytes(4)+struct.pack('<I',int(event))
    if event:
        size=119 if version==2 else 117
        item=struct.pack('<BQI',0,99,0x561e06fc)+bytes(size-15)+b'\x01\x03'
        result+=obj(0x41682213)+struct.pack('<HI',65535,1)+item+struct.pack('<IHH',0,1,60)
    result+=obj(0x0181efe8)+struct.pack('<IIQIIH',11,1,0,0x653caa76,22,0)
    if version==2:
        # A decoy binding-type marker inside opaque metadata must not be searched.
        result+=struct.pack('<II',4,0x653caa76)
    result+=struct.pack('<II',5,1)
    result+=struct.pack('<BI',254,0) if shared else struct.pack('<BIII',54,8,1,123)
    return result


class ContainerTests(unittest.TestCase):
    def test_versions_event_framing_and_direct_corpus(self):
        for version in (1,2):
            body=fixture(version,event=True);parsed=parse_clip_body(body)
            self.assertEqual(parsed['version'],version)
            self.assertEqual(parsed['consumed'],len(body))
            self.assertEqual(parsed['event_tracks'][0]['ticks'],[60])
            self.assertEqual(parsed['tracks'][0]['binding_hash'],22)
            self.assertEqual(inspect_clip(body,parsed['tracks'])['validated_tracks'],1)

    def test_shared_reference_is_preserved_not_resolved(self):
        parsed=parse_clip_body(fixture(shared=True))
        self.assertEqual(parsed['tracks'][0]['shared_track_reference'],0)
        report=inspect_clip(fixture(shared=True),parsed['tracks'])
        self.assertEqual(report['unresolved_shared_records'],1)
        self.assertFalse(report['all_tracks_supported_and_validated'])

    def test_truncations_and_trailing_bytes(self):
        body=fixture(event=True)
        for length in range(len(body)):
            with self.assertRaises(ValueError):parse_clip_body(body[:length])
        with self.assertRaises(ValueError):parse_clip_body(body+b'\x00')

    def test_wrong_types_counts_and_unknown_codec(self):
        body=fixture()
        for offset,fmt,value in ((8,'I',0),(12,'B',0),(25,'I',1),(37,'I',0xffffffff),(len(body)-13,'B',71)):
            damaged=bytearray(body);struct.pack_into('<'+fmt,damaged,offset,value)
            with self.assertRaises(ValueError):parse_clip_body(damaged)
