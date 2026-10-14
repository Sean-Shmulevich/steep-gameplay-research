"""Selected animation registry-copy block; callers supply a stable source view.

Native synchronization, allocation failure and registry ownership are not modeled.
An empty source preserves the destination, including its existing active count.
"""
from dataclasses import dataclass, field
from collections.abc import Sequence
from .membership import claim_range


@dataclass(frozen=True)
class AnimationSpan(Sequence):
    """Captured storage reference with late entry reads; not a completion token."""
    storage: list
    start: int
    count: int = field()

    def __len__(self):
        return self.count

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(self.count))]
        if index < 0:
            index += self.count
        if not 0 <= index < self.count:
            raise IndexError(index)
        return self.storage[self.start + index]


@dataclass
class AnimationMembership:
    storage: list = field(default_factory=list)
    count: int = 0

    def claim(self, chunk_size=1, tail_threshold=0):
        """Consume a range before visitation; exclusive serial ownership required.

        Count is remaining-to-claim, not unfinished callbacks. This models a
        successful native CAS; it does not implement competing worker threads.
        Do not rebuild storage until all claimed spans have finished using it.
        """
        if type(self.count) is not int or not 0 <= self.count <= len(self.storage):
            raise ValueError('active count must fit destination storage')
        proposal = claim_range(self.count, chunk_size, tail_threshold)
        if proposal is None:
            return None
        span = AnimationSpan(self.storage, proposal['start'], proposal['count'])
        self.count = proposal['remaining']
        return span

    def copy_registry(self, source):
        """Copy a stable sequence in order, retaining capacity when possible.

        Return whether storage grew as a portable diagnostic. This is not the
        original routine's return value. Referenced objects are not cloned.
        """
        if type(self.count) is not int or not 0 <= self.count <= len(self.storage):
            raise ValueError('active count must fit destination storage')
        count = len(source)
        if count > 0x7fffffff:
            raise ValueError('source count must fit nonnegative signed int32')
        if not count:
            return False
        grew = count > len(self.storage)
        if grew:
            self.storage = [None] * count
        self.count = 0
        self.storage[:count] = source[:count]
        self.count = count
        return grew
