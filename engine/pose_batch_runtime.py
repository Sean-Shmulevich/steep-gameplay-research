"""Joined retained batch execution with explicit queue and platform services.

Evidence: LINK_SOLVER.md, Joined retained batch execution.
"""
import struct
from collections.abc import Mapping, Sequence
from .pose_dispatch import dispatch_pose_workers
from .pose_group_batches import run_pose_group_batches
from .pose_group_transfer import transfer_completed_pose_groups
from .pose_worker_runtime import run_retained_pose_worker


class _PointerTail(Sequence):
    def __init__(self, slots, start):
        self.slots, self.start = slots, start

    def __len__(self):
        return len(self.slots) - self.start

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        return self.slots[self.start + index]


class RetainedPointerArrays(Mapping):
    """Resolve base or aligned interior tokens without copying retained arrays.

    Exact base entries take precedence. Ambiguous overlapping interior spans are
    rejected. This is an authored address adapter, not a recovered game class.
    """
    def __init__(self, arrays):
        self.arrays = arrays

    def __iter__(self):
        return iter(self.arrays)

    def __len__(self):
        return len(self.arrays)

    def __getitem__(self, token):
        if token in self.arrays:
            return self.arrays[token]
        candidates = [(slots, (token-base)//8) for base, slots in self.arrays.items()
                      if base < token < base+len(slots)*8 and (token-base)%8 == 0]
        if len(candidates) != 1:
            raise KeyError('Missing or ambiguous pointer-array span: %s' % token)
        return _PointerTail(*candidates[0])


def run_retained_pose_batch_pass(context_token, *, dispatcher, scalar,
                                 settings_token, worker_callback_token, jobs,
                                 worker_services, dispatch_services, sort_prefix,
                                 grow_batches, grow_lists, invoke_other=None):
    """Run one batch pass using the existing retained worker service dictionary.

    worker_services has the keyword arguments of run_retained_pose_worker.
    dispatch_services supplies atomic_compare_exchange, atomic_add, enqueue, take,
    notify and wait for dispatcher. jobs maps argument tokens to aliased records.
    Callback tokens and job owners are caller-supplied identities, not allocated
    here. invoke_other handles unrelated callbacks encountered while helping.
    """
    services = dict(worker_services)
    arrays = RetainedPointerArrays(services['arrays'])
    services['arrays'] = arrays
    context = services['contexts'][context_token]
    def invoke(function, argument, caller_thread):
        if function != worker_callback_token:
            if invoke_other is None:
                raise ValueError('Unrelated dispatcher callback requires a service')
            return invoke_other(function, argument, caller_thread)
        job = jobs[argument]
        owner = struct.unpack_from('<Q', job, 0)[0]
        # The native pose thunk ignores the caller-thread flag.
        run_retained_pose_worker(owner, job, **services)
    def dispatch(count, table_token):
        dispatch_pose_workers(dispatcher, count, worker_callback_token,
            arrays[table_token], invoke=invoke, **dispatch_services)
    def finish(raw):
        transfer_completed_pose_groups(raw, arrays=arrays,
            groups=services['groups'], grow=grow_lists)
    run_pose_group_batches(context, context_token=context_token, scalar=scalar,
        settings_token=settings_token,
        worker_capacity=struct.unpack_from('<I', dispatcher, 0x10)[0],
        arrays=arrays, groups=services['groups'], batches=services['batches'],
        sort_prefix=sort_prefix, grow=grow_batches, dispatch=dispatch, finish=finish)
