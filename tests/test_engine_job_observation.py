import json
import struct
import unittest
from engine.engine_job_observation import (observe_engine_jobs, IMAGE_SHA256,
    OWNER_GLOBAL_RVA, TABLE_RVA, METHODS, JOBS)

B=0x140000000; O=0x600000000


class EngineJobObservationTests(unittest.TestCase):
    def fixture(self):
        table=bytearray(128)
        for slot,rva in METHODS.items():struct.pack_into('<Q',table,slot,B+rva)
        jobs={}
        for name,offset in JOBS.items():
            block=bytearray(0x1b8)
            struct.pack_into('<Q',block,0,B+TABLE_RVA)
            struct.pack_into('<6I',block,0x4c,1,1,2,3,3,0)
            block[0x194]=1
            struct.pack_into('<4Q',block,0x198,B+0x656c20,0,O|2,B+0x8ab390)
            # Tags alone do not make an optional callback eligible.
            struct.pack_into('<Q',block,0x100,3)
            jobs[O+offset]=block
        def readv(plan):
            result=[]
            for a,n in plan:
                if a==B+OWNER_GLOBAL_RVA:result.append(struct.pack('<Q',O))
                elif a==B+TABLE_RVA:result.append(bytes(table[:n]))
                elif a==O+0x58:result.append(b'\1\1\0')
                else:result.append(bytes(jobs[a][:n]))
            return result
        return readv,jobs,table

    def observe(self,readv):
        return observe_engine_jobs(readv,image_base=B,image_size=0x4000000,verified_image_sha256=IMAGE_SHA256)

    def test_bounded_sanitized_lifecycle_and_tag_decoding(self):
        readv,jobs,table=self.fixture();r=self.observe(readv)
        self.assertEqual((r['reads'],r['bytes']),(16,2086))
        self.assertTrue(r['observations_equal'])
        job=r['samples'][0]['jobs']['graphics']
        self.assertTrue(job['local_teardown_would_wait'])
        self.assertEqual(job['delegates']['main']['receiver_relation'],'owner')
        self.assertEqual(job['delegates']['main']['context_tags'],2)
        self.assertFalse(job['delegates']['before']['optional_eligible'])
        self.assertNotIn(str(O),json.dumps(r))
        self.assertFalse(r['lifetime_pinned'])

    def test_changed_fields_are_reported_not_flattened(self):
        readv,jobs,table=self.fixture();calls=0
        def changing(plan):
            nonlocal calls
            calls+=1
            if calls==5:struct.pack_into('<I',jobs[O+0x218],0x50,0)
            return readv(plan)
        r=self.observe(changing)
        self.assertFalse(r['observations_equal'])
        self.assertEqual([s['jobs']['graphics']['outstanding_dispatches'] for s in r['samples']],[1,0])

    def test_rejects_guard_changes_and_short_reads(self):
        readv,jobs,table=self.fixture();calls=0
        def changed(plan):
            nonlocal calls
            calls+=1
            blocks=readv(plan)
            if calls==3:blocks[0]=struct.pack('<Q',O+0x1000)
            return blocks
        with self.assertRaisesRegex(ValueError,'identity changed'):self.observe(changed)
        with self.assertRaisesRegex(ValueError,'incomplete'):self.observe(lambda p:[b'']*len(p))

    def test_wrong_methods_or_build_refused(self):
        readv,jobs,table=self.fixture();table[0x40]=0
        with self.assertRaisesRegex(ValueError,'methods mismatch'):self.observe(readv)
        with self.assertRaisesRegex(ValueError,'unsupported'):
            observe_engine_jobs(readv,image_base=B,image_size=0x4000000,verified_image_sha256='wrong')

    def test_external_function_is_not_exported_or_assumed_valid(self):
        readv,jobs,table=self.fixture()
        struct.pack_into('<Q',jobs[O+0x218],0xf0,O+0x8000)
        job=self.observe(readv)['samples'][0]['jobs']['graphics']
        self.assertEqual(job['delegates']['before']['function'],{'kind':'outside_image'})
        self.assertTrue(job['delegates']['before']['optional_eligible'])

    def test_redacted_context_change_still_marks_observations_unequal(self):
        readv,jobs,table=self.fixture();calls=0
        struct.pack_into('<Q',jobs[O+0x218],0x1a8,O+0x1000)
        def changing(plan):
            nonlocal calls
            calls+=1
            if calls==5:struct.pack_into('<Q',jobs[O+0x218],0x1a8,O+0x2000)
            return readv(plan)
        r=self.observe(changing)
        self.assertEqual(r['samples'][0],r['samples'][1])
        self.assertFalse(r['observations_equal'])
