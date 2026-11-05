import struct
import unittest

from engine.pose_island_ccd_stage import (begin_swept_stage, reserve_stage_list,
                                          store_stage_dt, finish_swept_stage, run_swept_stage)
from engine.pose_pair_link_worker import PoseFlatMemory

STAGE, CTRL, PROV, GEN, OBJS, CON, BODY, META = (0x1000, 0x3000, 0x3100, 0x4000, 0x5000,
                                                0x10000, 0x20000, 0x30000)


def world(kinds, holders, containers=()):
    mem = PoseFlatMemory()
    mem.add(STAGE, bytearray(0x1040))
    mem.set_q(STAGE + 8, CTRL)
    mem.add(CTRL, bytearray(0x80))
    mem.set_q(CTRL + 0x20, PROV)
    mem.set_q(CTRL + 0x40, STAGE)
    mem.add(PROV, bytearray(0x100))
    for i, h in enumerate((0x700, 0x800)):
        mem.add(BODY + i * 0x200, bytearray(0x200))
        mem.add(META + i * 0x60, bytearray(0x60))
        mem.set_q(BODY + i * 0x200 + 0x30, META + i * 0x60)
        mem.set_q(META + i * 0x60 + 0x20, h)

    def con(k, kind, pair):
        p = CON + k * 0x80
        mem.add(p, bytearray(0x80))
        mem.set_q(p + 8, BODY)
        mem.set_q(p + 0x10, BODY + (0x200 if pair else 0))
        mem.set_d(p + 0x70, kind)
        return p
    gen = [con(k, kind, holders[k]) for k, kind in enumerate(kinds)]
    mem.add(GEN, bytearray(max(8, 8 * len(gen))))
    for k, p in enumerate(gen):
        mem.set_q(GEN + 8 * k, p)
    mem.set_q(PROV + 0x60, GEN)
    mem.set_d(PROV + 0x68, len(gen))
    mem.add(OBJS, bytearray(64))
    for c, child_kinds in enumerate(containers):
        cp = 0x6000 + c * 0x100
        arr = 0x7000 + c * 0x100
        mem.add(cp, bytearray(0x80))
        mem.add(arr, bytearray(0x80))
        for j, kind in enumerate(child_kinds):
            mem.set_q(arr + 8 * j, con(len(gen) + 10 * (c + 1) + j, kind, False))
        mem.set_q(cp + 0x58, arr)
        mem.set_d(cp + 0x60, len(child_kinds))
        mem.set_q(OBJS + 8 * c, cp)
    mem.set_q(PROV + 0x50, OBJS)
    mem.set_d(PROV + 0x58, len(containers))
    return mem


class Allocator:
    def __init__(self, mem, log):
        self.mem, self.log, self.next = mem, log, 0x90000

    def allocate(self, size, align, tag):
        self.log.append(('alloc', size, align, tag))
        p = self.next
        self.next += 0x1000
        self.mem.add(p, bytearray(size))
        return p

    def reallocate(self, pointer, size, align, tag):
        self.log.append(('realloc', size, tag))
        p = self.next
        self.next += 0x1000
        self.mem.add(p, bytearray(size))
        old = self.mem.view(pointer, min(size, 64)).tobytes()
        self.mem.view(p, len(old))[:] = old
        return p

    def release(self, pointer):
        self.log.append(('free', pointer))


class SweptStageBeginTests(unittest.TestCase):
    def run_begin(self, mem):
        log = []
        alloc = Allocator(mem, log)
        begin_swept_stage(
            mem, STAGE, kind=lambda c: mem.d(c + 0x70),
            grow=lambda d, cap: reserve_stage_list(mem, d, cap, allocator=alloc),
            remove_cross=lambda ctrl, c: log.append(('cross', ctrl, c)),
            remove_local=lambda h, c: log.append(('local', h, c)),
            destroy=lambda c, f: log.append(('destroy', c, f)))
        return log

    def test_only_kind6_removed_by_holder_relation_then_destroyed(self):
        mem = world([6, 4, 6], [True, True, False])
        log = self.run_begin(mem)
        self.assertEqual(log, [('alloc', 64, 0x10, 0x11),
                               ('cross', CTRL, CON), ('destroy', CON, 1),
                               ('local', 0x700, CON + 0x100), ('destroy', CON + 0x100, 1)])
        self.assertEqual(mem.d(STAGE + 0x1038), 0)
        self.assertEqual(mem.d(STAGE + 0x103c), 8)

    def test_container_children_follow_general_list_and_list_doubles(self):
        mem = world([6] * 9, [False] * 9, containers=[(6, 1), (6,)])
        log = self.run_begin(mem)
        self.assertEqual([e[0] for e in log if e[0] in ('alloc', 'realloc')], ['alloc', 'realloc'])
        self.assertEqual(mem.d(STAGE + 0x103c), 16)
        destroyed = [e[1] for e in log if e[0] == 'destroy']
        self.assertEqual(len(destroyed), 11)
        self.assertEqual(destroyed[9:], [CON + (9 + 10) * 0x80, CON + (9 + 20) * 0x80])

    def test_nulled_slot_skips_destroy_but_not_removal(self):
        mem = world([6], [False])
        log = []
        begin_swept_stage(mem, STAGE, kind=lambda c: 6,
                          grow=lambda d, cap: reserve_stage_list(mem, d, cap,
                                                                 allocator=Allocator(mem, [])),
                          remove_cross=None,
                          remove_local=lambda h, c: mem.set_q(mem.q(STAGE + 0x1030), 0),
                          destroy=lambda c, f: log.append(c))
        self.assertEqual(log, [])

    def test_empty_inputs_clear_count(self):
        mem = world([], [])
        mem.set_d(STAGE + 0x1038, 0)
        self.assertEqual(self.run_begin(mem), [])


class SweptStageOrderTests(unittest.TestCase):
    def test_dt_store_and_finish_gate(self):
        mem = world([], [])
        store_stage_dt(mem, STAGE, -0.0)
        self.assertEqual(mem.d(STAGE + 0x10), 0x80000000)
        log = []
        args = dict(scan=lambda s: log.append('scan'), acquire_job_context=lambda: log.append('job') or 7,
                    run_job=lambda t: log.append(('run', t)), process_hits=lambda s: log.append('hits'))
        finish_swept_stage(mem, STAGE, **args)
        self.assertEqual(log, ['scan'])
        mem.set_d(STAGE + 0x28, 1)
        log.clear()
        finish_swept_stage(mem, STAGE, **args)
        self.assertEqual(log, ['scan', 'job', ('run', 7), 'hits'])

    def test_stage_sequence_uses_controller_plus_40(self):
        mem = world([], [])
        log = []
        run_swept_stage(mem, CTRL, 0.5, begin=lambda s: log.append(('begin', s)),
                        finish=lambda s: log.append(('finish', s, mem.get('<f', s + 0x10))))
        self.assertEqual(log, [('begin', STAGE), ('finish', STAGE, 0.5)])


if __name__ == '__main__':
    unittest.main()
