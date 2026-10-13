"""Cooperative consumer probe for the recovered idle-task dequeue.

Prelinked nodes are synthetic setup, not recovered enqueue behavior. Each step
separates a load, CAS, or post-CAS store. No producer, node reuse, native memory,
OS threads, event semantics, task execution, or reclamation proof is included.
Evidence: docs/reconstruction/IDLE_TASK_WORKERS.md, Tagged dummy-node pop.
"""
from copy import deepcopy
from .tagged_task_queue import POINTER_MASK, _advance


class TaskQueueProbe:
    def __init__(self, tasks, *, workers=2, tail_index=None):
        if not isinstance(tasks, list) or any(type(t) is not str for t in tasks):
            raise ValueError('synthetic tasks must be a list of string identities')
        if len(set(tasks)) != len(tasks):
            raise ValueError('synthetic task identities must be unique')
        if type(workers) is not int or not 1 <= workers <= 16:
            raise ValueError('worker count must be 1..16')
        if tail_index is None:
            tail_index = len(tasks)
        if type(tail_index) is not int or not 0 <= tail_index <= len(tasks):
            raise ValueError('tail index must name a node in the synthetic chain')
        self.nodes = {i + 1: dict(next=i + 2 if i < len(tasks) else 0,
                                 payload=None if i == 0 else tasks[i - 1])
                      for i in range(len(tasks) + 1)}
        self.head, self.tail = 1, tail_index + 1
        self.workers = [dict(phase='head') for _ in range(workers)]
        self.returned, self.trace = [], []

    def step(self, worker):
        if type(worker) is not int or not 0 <= worker < len(self.workers):
            raise ValueError('unknown worker')
        w = self.workers[worker]
        phase = w['phase']
        event = dict(worker=worker, action=phase)
        if phase == 'done':
            raise ValueError('worker already observed empty queue')
        if phase == 'head':
            w.update(head=self.head, phase='tail')
        elif phase == 'tail':
            w.update(tail=self.tail, phase='next')
        elif phase == 'next':
            w.update(next=self.nodes[w['head'] & POINTER_MASK]['next'], phase='recheck')
        elif phase == 'recheck':
            if w['head'] != self.head:
                w['phase'] = 'head'
                event['retry'] = 'head_changed'
            elif w['next'] == 0:
                w['phase'] = 'done'
            elif (w['head'] & POINTER_MASK) == (w['tail'] & POINTER_MASK):
                w['phase'] = 'tail_next'
            else:
                w['phase'] = 'payload'
        elif phase == 'tail_next':
            w['tail_next'] = self.nodes[w['tail'] & POINTER_MASK]['next']
            w['phase'] = 'head' if w['tail_next'] & POINTER_MASK == 0 else 'cas_tail'
        elif phase == 'cas_tail':
            event['success'] = self.tail == w['tail']
            if event['success']:
                self.tail = _advance(w['tail'], w['tail_next'])
            w['phase'] = 'head'
        elif phase == 'payload':
            w.update(payload=self.nodes[w['next']]['payload'], phase='cas_head')
        elif phase == 'cas_head':
            event['success'] = self.head == w['head']
            if event['success']:
                self.head = _advance(w['head'], w['next'])
            w['phase'] = 'copy' if event['success'] else 'head'
        elif phase == 'copy':
            self.nodes[w['head'] & POINTER_MASK]['payload'] = w['payload']
            w['phase'] = 'return'
        elif phase == 'return':
            node = w['head'] & POINTER_MASK
            self.returned.append(dict(worker=worker, node=node,
                                      payload=self.nodes[node]['payload']))
            w.clear()
            w['phase'] = 'head'
        else:
            raise AssertionError('unknown probe phase')
        self.trace.append(event)
        return deepcopy(event)

    def snapshot(self):
        return deepcopy(dict(head=self.head, tail=self.tail, nodes=self.nodes,
                             workers=self.workers, returned=self.returned,
                             trace=self.trace,
                             complete=all(w['phase'] == 'done' for w in self.workers)))
