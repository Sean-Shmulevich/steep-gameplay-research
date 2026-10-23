import struct
import unittest
from engine.motion_input_batch import prepare_motion_input_batch
from engine.motion_input_ingestion import ingest_motion_prefix
from engine.scheduler import schedule

ZERO = bytes(16)
LEFT = struct.pack('<4f', -1, 0, 0, 0)
RIGHT = struct.pack('<4f', 1, 0, 0, 0)

class MotionBatchTests(unittest.TestCase):
    def initial(self):
        return ingest_motion_prefix((ZERO,)*4, flip_x=False, counts=(0,0),
                                    smoothed=(ZERO,ZERO), alpha=.5)

    def prepare(self, previous, steps, reader, **overrides):
        options=dict(ingestion_enabled=True, read_action=reader,
                     alternate_enabled=False, actor_predicate=False,
                     flip_x=False, alpha=.5)
        options.update(overrides)
        return prepare_motion_input_batch(previous, steps, **options)

    def test_source_changes_during_substeps_only_affect_next_batch(self):
        steps=schedule({}, .05, {'mode':'fixed','fixed_dt':.01})
        source=[LEFT]; reads=[]; observed=[]
        def reader(action):
            reads.append(action)
            return source[0] if action==0x76 else ZERO
        batch=self.prepare(self.initial(),steps,reader)
        # Mutating the original plan must not alter the prepared batch.
        steps[0]['elapsed_dt']=999
        def update(i, elapsed, derivative, motion):
            observed.append((i,elapsed,motion.primary,motion.primary_count))
            source[0]=RIGHT
        batch.execute(update)
        self.assertEqual(len(observed),5)
        self.assertEqual(reads,[0x76,0x77,0x76,0x77])
        self.assertTrue(all(x[1:]==(.01,LEFT,1) for x in observed))
        following=self.prepare(batch.motion,[{'elapsed_dt':.01,'derivative_dt':.01}],reader)
        self.assertEqual(following.motion.primary,RIGHT)
        self.assertEqual(following.motion.primary_count,2)

    def test_release_resets_on_next_batch_and_suppression_preserves(self):
        held=self.prepare(self.initial(),[],lambda _:LEFT)
        def forbidden(_): raise AssertionError('suppressed read')
        suppressed=self.prepare(held.motion,[],forbidden,ingestion_enabled=False)
        self.assertIs(suppressed.motion,held.motion)
        self.assertFalse(suppressed.refreshed)
        released=self.prepare(suppressed.motion,[],lambda _:ZERO)
        self.assertEqual(released.motion.primary_count,0)
        self.assertEqual(released.motion.primary,ZERO)

    def test_repeated_action_ids_are_independent_reads(self):
        values=iter((LEFT,ZERO,RIGHT,ZERO)); ids=[]
        def read(action): ids.append(action);return next(values)
        batch=self.prepare(self.initial(),[],read,alternate_enabled=True,actor_predicate=True)
        self.assertEqual(ids,[0xd9,0x77,0x76,0x77])
        self.assertEqual(batch.motion.primary,LEFT)
        self.assertEqual(batch.motion.current_primary,RIGHT)

    def test_invalid_plan_fails_before_reads_and_failed_callback_stops(self):
        def forbidden(_):raise AssertionError('unexpected read')
        for interval in (-1,0,float('nan'),float('inf'),True):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                self.prepare(self.initial(),[dict(elapsed_dt=interval,derivative_dt=.01)],forbidden)
        batch=self.prepare(self.initial(),[dict(elapsed_dt=.01,derivative_dt=.02)]*3,lambda _:ZERO)
        called=[]
        def fail(i,*args):
            called.append(i)
            raise RuntimeError('solver failed')
        with self.assertRaises(RuntimeError):batch.execute(fail)
        self.assertEqual(called,[0])
