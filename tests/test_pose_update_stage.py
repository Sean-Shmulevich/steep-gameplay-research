import struct
import unittest
from engine.pose_update_stage import run_pose_update_stage


def fixture():
    owner=bytearray(0x50)
    for off,value in ((0x20,20),(0x28,28),(0x30,30),(0x38,38),(0x40,40)):
        struct.pack_into('<Q',owner,off,value)
    context=bytearray(0x500);struct.pack_into('<QI',context,0x490,100,3)
    changed=bytearray(0x38);struct.pack_into('<QI',changed,0x28,200,2)
    events=[]
    def record(name,ret=None):
        def call(*args):
            events.append((name,args,struct.unpack_from('<I',owner,0x48)[0]));return ret
        return call
    args=dict(scalar=.25,owners={1:owner},contexts={30:context},collections={38:changed},
        arrays={100:[7,0,9]},prepare=record('prepare'),get_body_source=record('source',50),
        update_bodies=record('bodies'),body_update_callback=60,begin_contacts=record('begin'),
        update_contacts=record('contacts'),finish_contacts=record('finish'),
        attach_links=record('attach'),publish_link=record('publish'),
        get_settings=record('settings',70),run_batches=record('batches'),notify_active=record('active'))
    return owner,context,args,events


class UpdateStageTests(unittest.TestCase):
    def test_service_order_and_null_link_conversion(self):
        owner,context,args,events=fixture()
        struct.pack_into('<I',context,0x420,1)
        run_pose_update_stage(1,**args)
        self.assertEqual([e[0] for e in events],['prepare','source','bodies','begin',
            'contacts','finish','attach','publish','publish','publish','settings','batches','active'])
        self.assertEqual([e[1] for e in events if e[0]=='publish'],[(28,15),(28,0),(28,17)])
        self.assertTrue(all(e[2]==3 for e in events))
        self.assertEqual(struct.unpack_from('<I',owner,0x48)[0],0)

    def test_reload_owner_and_pending_slot_but_capture_span(self):
        owner,context,args,events=fixture();seen=[]
        def begin(token):struct.pack_into('<Q',owner,0x40,41)
        def publish(interface,token):
            seen.append((interface,token))
            struct.pack_into('<Q',owner,0x28,29)
            struct.pack_into('<QI',context,0x490,999,0)
            args['arrays'][100][2]=10
        args.update(begin_contacts=begin,publish_link=publish)
        def batches(*x):
            replacement=bytearray(0x500);struct.pack_into('<I',replacement,0x420,1)
            args['contexts'][31]=replacement;struct.pack_into('<Q',owner,0x30,31)
        args['run_batches']=batches
        run_pose_update_stage(1,**args)
        self.assertIn(('contacts',(41,.25),3),events)
        self.assertEqual(seen,[(28,15),(29,0),(29,18)])
        self.assertEqual(events[-1],('active',(29,0),3))

    def test_preparation_reciprocal_and_provider_reload(self):
        from engine.pose_update_stage import prepare_pose_constraint_collections
        owner,_,_,_=fixture();events=[]
        def first_at(provider,index):
            events.append(('get',provider,index));return 100+index
        def prepare(token,reciprocal):
            events.append(('prepare',token,reciprocal))
            struct.pack_into('<Q',owner,0x20,21)
        prepare_pose_constraint_collections(1,scalar=.25,owners={1:owner},
            first_count=lambda p:2,first_at=first_at,
            second_count=lambda p:events.append(('second_count',p)) or 1,
            second_at=lambda p,i:200,prepare_constraint=prepare)
        self.assertEqual(events,[('get',20,0),('prepare',100,4.),('get',21,1),
                                 ('prepare',101,4.),('second_count',21),('prepare',200,4.)])
        values=[]
        prepare_pose_constraint_collections(1,scalar=-0.,owners={1:owner},
            first_count=lambda p:1,first_at=lambda p,i:0,second_count=lambda p:0,
            second_at=lambda *a:self.fail('empty'),prepare_constraint=lambda p,r:values.append(r))
        self.assertEqual(values,[float('-inf')])

    def test_retirement_suppresses_notification_and_exception_keeps_phase(self):
        owner,context,args,events=fixture()
        struct.pack_into('<I',context,0x420,1)
        args['run_batches']=lambda *x:struct.pack_into('<I',context,0x420,0)
        run_pose_update_stage(1,**args)
        self.assertNotIn('active',[e[0] for e in events])
        def fail(*x):raise RuntimeError('supplied service')
        args['prepare']=fail
        with self.assertRaises(RuntimeError):run_pose_update_stage(1,**args)
        self.assertEqual(struct.unpack_from('<I',owner,0x48)[0],3)


if __name__=='__main__':unittest.main()
