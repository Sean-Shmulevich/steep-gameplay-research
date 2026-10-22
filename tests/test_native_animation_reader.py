"""Execute the native reader against synthetic byte arrays, no Wine/game."""
import ctypes as C
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import test_player_animation_observation as memory_fixture

READ = C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_uint64,C.c_void_p,C.c_size_t)
class Profile(C.Structure):
    _fields_=[('entity_tables',C.c_uint64*16),('skeleton_table',C.c_uint64),
              ('type_getter',C.c_uint64),('descriptor_global',C.c_uint64),('count',C.c_uint)]
class Result(C.Structure):
    _fields_=[('found',C.c_uint32),('guards',C.c_uint32),('epoch',C.c_uint32),
              ('vector',C.c_float*4),('rotation',C.c_float*4),
              ('parent_vector',C.c_float*4),('parent_rotation',C.c_float*4),
              ('provider_vector',C.c_float*4),('provider_rotation',C.c_float*4),
              ('record_index',C.c_uint32),('bank_flags',C.c_uint32),
              ('owner_matrix',C.c_float*16),('owner_accessor_present',C.c_uint32),('owner_reader_word',C.c_uint32)]

class CachedResult(C.Structure):
    _fields_=[('cached',C.c_float*8),('primary',C.c_float*8),('current',C.c_float*8)]+[(n,C.c_uint32) for n in
        ('guards','primary_present','current_present','banks_alias','storage_nonempty','context_tag',
         'context_nonzero','function_present','holder_present','target_present','status_sign','eligible')]

class NativeAnimationReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc=shutil.which('cc')
        if not cc: raise unittest.SkipTest('C compiler unavailable')
        cls.tmp=tempfile.TemporaryDirectory()
        source=Path(__file__).resolve().parents[1]/'native/snow_host/animation_reader_fixture.c'
        lib=Path(cls.tmp.name)/'reader.so'
        subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',str(source),'-o',str(lib)],check=True,capture_output=True)
        cls.library=C.CDLL(str(lib))
        cls.fn=cls.library.snow_animation_fixture
        cls.fn.argtypes=[READ,C.c_void_p,C.c_uint64,C.POINTER(Profile),C.c_uint32,C.POINTER(Result)]
        cls.fn.restype=C.c_int
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def setUp(self):
        self.fixture=memory_fixture.PlayerAnimationObservationTests();self.fixture.setUp()
        b=self.fixture.base
        self.profile=Profile((C.c_uint64*16)(b+0x200),b+0x300,b+0x500,b+0x600,1)
    def run_reader(self,key=10,mutate=None,fail=None):
        f=self.fixture
        def read(_,address,out,size):
            if fail and fail(address,size): return 0
            offset=address-f.base
            if offset<0 or offset+size>len(f.memory): return 0
            C.memmove(out,bytes(f.memory[offset:offset+size]),size)
            if mutate: mutate(address,size)
            return 1
        callback=READ(read);out=Result()
        rc=self.fn(callback,None,f.entity,C.byref(self.profile),key,C.byref(out))
        if rc: self.assertEqual(bytes(out),bytes(Result()))
        return rc,out
    def test_success_local_record(self):
        rc,out=self.run_reader();self.assertEqual(rc,0)
        self.assertEqual(list(out.vector),[1,2,3,0]);self.assertEqual(list(out.rotation),[0,0,0,1])
        self.assertEqual((out.found,out.guards),(1,1))
    def test_missing_and_unsigned_max_key(self):
        for key in [99,4294967295]:
            rc,out=self.run_reader(key);self.assertEqual((rc,out.found,out.guards),(0,0,1))
    def test_wrong_owner(self):
        f=self.fixture;f.put(f.component+0x10,'<Q',f.entity+8)
        self.assertEqual(self.run_reader()[0],1)
    def test_epoch_changes(self):
        f=self.fixture
        def mutate(a,n):
            if a==f.base+0xf000:f.put(f.component+0xc58,'<I',5)
        self.assertEqual(self.run_reader(mutate=mutate)[0],1)
    def test_slot_changes(self):
        f=self.fixture
        def mutate(a,n):
            if a==f.base+0xf000:f.put(f.base+0x3000,'<Q',f.component+8)
        self.assertEqual(self.run_reader(mutate=mutate)[0],1)
    def test_interrupted_read(self):
        self.assertEqual(self.run_reader(fail=lambda a,n:a==self.fixture.base+0xf000)[0],1)
    def test_metadata_allocation_too_small(self):
        f=self.fixture;f.put(f.base+0xe014,'<HH',16,32)
        self.assertEqual(self.run_reader()[0],1)
        f.put(f.base+0xd08c,'<I',1<<28)
        self.assertEqual(self.run_reader()[0],0)
    def test_channel_outside_record_count(self):
        f=self.fixture;f.put(f.base+0xc000,'<II',10,1)
        self.assertEqual(self.run_reader()[0],1)
    def test_nonfinite_record(self):
        f=self.fixture;f.put(f.base+0xf000,'<f',float('nan'))
        self.assertEqual(self.run_reader()[0],1)
    def test_duplicate_skeleton_refused(self):
        f=self.fixture;f.put(f.entity+0x92,'<H',2);f.put(f.base+0x3008,'<Q',f.component)
        self.assertEqual(self.run_reader()[0],1)
    def test_bad_type_getter(self):
        f=self.fixture;f.write(f.base+0x500,b'\x90')
        self.assertEqual(self.run_reader()[0],1)
    def test_unsigned_lookup_and_first_duplicate(self):
        f=self.fixture
        f.put(f.base+0xb042,'<H',3)
        f.put(f.base+0xc000,'<IIIIII',10,0,10,65535,0xffffffff,0)
        self.assertEqual(self.run_reader(10)[1].found,1)
        self.assertEqual(self.run_reader(0xffffffff)[1].found,1)
    def test_unsorted_lookup_refused(self):
        f=self.fixture;f.put(f.base+0xb042,'<H',2)
        f.put(f.base+0xc000,'<IIII',11,0,10,0)
        self.assertEqual(self.run_reader()[0],1)
    def test_oversized_lookup_refused(self):
        f=self.fixture;f.put(f.base+0xb042,'<H',4097)
        self.assertEqual(self.run_reader()[0],1)
    def test_changed_record_refused(self):
        f=self.fixture
        def mutate(a,n):
            if a==f.base+0xf000:f.put(a,'<f',50)
        self.assertEqual(self.run_reader(mutate=mutate)[0],1)
    def test_bank_swap_refused(self):
        f=self.fixture
        def mutate(a,n):
            if a==f.base+0xf000:f.put(f.component+0x258,'<Q',f.base+0xd008)
        self.assertEqual(self.run_reader(mutate=mutate)[0],1)
    def test_output_matches_python_local_observation(self):
        f=self.fixture
        for x in [-123.5,0,17.25]:
            f.put(f.base+0xf000,'<f',x)
            expected=f.capture()['pose']['channels'][0]['inputs']
            rc,out=self.run_reader()
            self.assertEqual(rc,0)
            self.assertEqual(list(out.vector),expected['position'])
            self.assertEqual(list(out.rotation),expected['rotation'])
    def test_provider_conversion_matches_reference(self):
        import random
        from reference.ground_response_pose import provider_pose_transform
        rng=random.Random(917)
        f=self.fixture
        for direct in [False,True]:
            for _ in range(64):
                local=[rng.uniform(-2,2) for _ in range(8)]
                parent=[rng.uniform(-3,3) for _ in range(8)]
                f.put(f.base+0xf000,'<8f',*local);f.put(f.base+0xd000,'<8f',*parent)
                f.put(f.base+0xd08c,'<I',(1<<26) if direct else 0)
                rc,out=self.run_reader();self.assertEqual(rc,0)
                expected=provider_pose_transform(local[:4],local[4:],parent[:4],parent[4:],direct)
                self.assertEqual(list(out.provider_vector),list(expected['position']))
                self.assertEqual(list(out.provider_rotation),list(expected['rotation']))
                self.assertEqual(out.record_index,0)
    def test_parent_mutation_refused(self):
        f=self.fixture
        def mutate(a,n):
            if a==f.base+0xd000:f.put(a,'<f',999)
        self.assertEqual(self.run_reader(mutate=mutate)[0],1)
    def test_nonfinite_parent_and_overflow_refused(self):
        f=self.fixture
        f.put(f.base+0xd000,'<f',float('inf'))
        self.assertEqual(self.run_reader()[0],1)
        f.put(f.base+0xd000,'<8f',0,0,0,0,1e30,1e30,1e30,1e30)
        self.assertEqual(self.run_reader()[0],1)
    def test_owner_matrix_retained_and_changes_refused(self):
        f=self.fixture;matrix=[1,0,0,0,0,1,0,0,0,0,1,0,10,20,30,1]
        f.put(f.entity+0x20,'<16f',*matrix)
        rc,out=self.run_reader();self.assertEqual(rc,0);self.assertEqual(list(out.owner_matrix),matrix)
        def mutate(a,n):
            if a==f.base+0xf000:f.put(f.entity+0x20,'<f',2)
        self.assertEqual(self.run_reader(mutate=mutate)[0],1)
    def test_owner_accessor_backlink_and_state(self):
        f=self.fixture;accessor=f.base+0x11000
        f.put(f.entity+0x18,'<Q',accessor);f.put(accessor+0x40,'<Q',f.entity)
        f.put(accessor+0x8c,'<IIIB',3,7,0,1)
        rc,out=self.run_reader();self.assertEqual(rc,0)
        self.assertEqual((out.owner_accessor_present,out.owner_reader_word),(1,3))
        f.put(accessor+0x40,'<Q',f.entity+8)
        self.assertEqual(self.run_reader()[0],1)
    def test_owner_accessor_state_mutation_refused(self):
        f=self.fixture;accessor=f.base+0x11000
        f.put(f.entity+0x18,'<Q',accessor);f.put(accessor+0x40,'<Q',f.entity)
        def mutate(a,n):
            if a==f.base+0xf000:f.put(accessor+0x8c,'<I',1)
        self.assertEqual(self.run_reader(mutate=mutate)[0],1)

    def cached_reader(self,mutate=None):
        f=self.fixture
        def read(_,address,out,size):
            offset=address-f.base
            if offset<0 or offset+size>len(f.memory):return 0
            C.memmove(out,bytes(f.memory[offset:offset+size]),size)
            if mutate:mutate(address,size)
            return 1
        fn=self.library.snow_cached_parent_fixture
        fn.argtypes=[READ,C.c_void_p,C.c_uint64,C.POINTER(Profile),C.POINTER(CachedResult)]
        fn.restype=C.c_int
        out=CachedResult();rc=fn(READ(read),None,f.entity,C.byref(self.profile),C.byref(out))
        if rc:self.assertEqual(bytes(out),bytes(CachedResult()))
        return rc,out
    def test_cached_callback_success(self):
        f=self.fixture;f.put(f.component+0x250,'<Q',f.base+0xd000)
        f.put(f.component+0x290,'<5Q',1,0,7,f.base+0x7000,f.base+0x7100)
        f.put(f.base+0x7100,'<QII',0x100,2,0x80000000)
        rc,out=self.cached_reader()
        self.assertEqual((rc,out.guards,out.eligible,out.banks_alias,out.context_tag),(0,1,1,1,3))
    def test_cached_empty_callback(self):
        rc,out=self.cached_reader();self.assertEqual((rc,out.eligible,out.function_present),(0,0,0))
    def test_cached_mutations_rejected(self):
        f=self.fixture
        for offset,size in ((0x130,32),(0x290,40),(0x250,16)):
            self.setUp();f=self.fixture;changed=[]
            def mutate(address,n):
                if address==f.component+offset and n==size and not changed:
                    changed.append(True);f.write(address,bytes([0x77])*n)
            self.assertEqual(self.cached_reader(mutate)[0],1)
    def test_cached_wrong_owner(self):
        f=self.fixture;f.put(f.component+0x10,'<Q',f.entity+8)
        self.assertEqual(self.cached_reader()[0],1)
    def test_cached_active_registration_missing_holder(self):
        f=self.fixture;f.put(f.component+0x250,'<Q',f.base+0xd000);f.put(f.component+0x290,'<Q',1)
        self.assertEqual(self.cached_reader()[0],1)
