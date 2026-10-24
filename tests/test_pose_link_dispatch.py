import struct
import unittest
from engine.pose_link_dispatch import dispatch_pose_link_builders


class DispatchTests(unittest.TestCase):
    def payload(self, count, enabled=True):
        value=bytearray(288)
        struct.pack_into('<I',value,0x110,count)
        value[0x114]=int(enabled)
        return value

    def run_dispatch(self, context, tokens, links, bodies, payloads, callback):
        names=('metadata_set_multi','metadata_set_single',
               'metadata_clear_multi','metadata_clear_single')
        builders={name:(lambda c,a,b,p,n=name:callback(n,c,a,b,p)) for name in names}
        dispatch_pose_link_builders(context,tokens,links=links,bodies=bodies,
                                    payloads=payloads,builders=builders)

    def test_gates_and_all_four_paths(self):
        for flags in range(4):
            for metadata in (0,0x8000):
                calls=[]
                payloads={i:self.payload(n) for i,n in enumerate((0,1,2,0xffffffff))}
                payloads[4]=self.payload(3,False)
                link=dict(flags84=1,first_body=10,second_body=20,
                          payload_count=5,payload_slots=list(payloads))
                self.run_dispatch(dict(flags38=flags),[1,2],
                    {1:dict(flags84=0),2:link},{20:dict(metadata_flags50=metadata)},
                    payloads,lambda n,c,a,b,p:calls.append((n,a,b)))
                prefix='metadata_set' if metadata else 'metadata_clear'
                self.assertEqual(calls,[(prefix+('_multi' if flags==0 and i>=2 else '_single'),10,20)
                                        for i in range(4)])

    def test_captured_per_link_state_and_reloaded_payload_slots(self):
        context=dict(flags38=0)
        link=dict(flags84=1,first_body=10,second_body=20,payload_count=2,payload_slots=[1,2])
        bodies={20:dict(metadata_flags50=0)}
        payloads={1:self.payload(2),2:self.payload(2,False),3:self.payload(2)}
        calls=[]
        def callback(name,c,a,b,p):
            calls.append(name)
            if len(calls)==1:
                c['flags38']=1
                bodies[20]['metadata_flags50']=0x8000
                link.update(payload_count=0,payload_slots=[1,3],flags84=0)
        self.run_dispatch(context,[1],{1:link},bodies,payloads,callback)
        self.assertEqual(calls,['metadata_clear_multi']*2)

    def test_empty_range_needs_no_objects(self):
        self.run_dispatch({},[],{},{},{},lambda *a:self.fail('Unexpected builder'))
