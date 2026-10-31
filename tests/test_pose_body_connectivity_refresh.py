import struct
import unittest
from engine.pose_body_connectivity_refresh import refresh_pose_body_connectivity


class ConnectivityRefreshTests(unittest.TestCase):
    def fixture(self):
        b=bytearray(0x200);m=bytearray(0x60);o=bytearray(0x40);c=bytearray(0x80)
        struct.pack_into('<Q',b,0x30,3);struct.pack_into('<Q',m,0x20,4)
        struct.pack_into('<Q',o,0x20,5);struct.pack_into('<QQ',c,0x30,6,7)
        return b,c,dict(body_token=2,metadata={3:m},owners={4:o},controllers={5:c})

    def test_empty_ring_no_services(self):
        b,c,args=self.fixture()
        refresh_pose_body_connectivity(b,**args,links={},collect=None,rebuild=None,retire=None)

    def test_mixed_endpoints_snapshot_rows_and_reload_services(self):
        b,c,args=self.fixture();struct.pack_into('<Q',b,0x80,10)
        links={10:bytearray(0x40),11:bytearray(0x40)}
        struct.pack_into('<QQQ',links[10],8,2,99,101)
        struct.pack_into('<Q',links[10],0x20,11)
        struct.pack_into('<QQQ',links[11],8,99,2,102)
        struct.pack_into('<Q',links[11],0x30,10)
        expected=[bytes(links[n][8:0x20]) for n in (10,11)];events=[];output=[77]
        def collect(provider,rows):
            self.assertEqual((provider,rows),(7,expected))
            links[10][8:0x20]=bytes(24);self.assertEqual(rows,expected)
            struct.pack_into('<Q',c,0x30,66);return output
        def rebuild(context,rows):
            self.assertEqual(context,66);self.assertIs(rows,output);rows.append(88)
            struct.pack_into('<Q',c,0x38,777);events.append('rebuild')
        def retire(provider,rows,flag):
            self.assertIs(rows,output);self.assertEqual((provider,rows,flag),(777,[77,88],1));events.append('retire')
        refresh_pose_body_connectivity(b,**args,links=links,collect=collect,rebuild=rebuild,retire=retire)
        self.assertEqual(events,['rebuild','retire'])

    def test_nonclosing_ring_is_an_authored_guard(self):
        b,c,args=self.fixture();struct.pack_into('<Q',b,0x80,10)
        link=bytearray(0x40)
        with self.assertRaisesRegex(ValueError,'does not close'):
            refresh_pose_body_connectivity(b,**args,links={10:link},collect=None,rebuild=None,retire=None)
