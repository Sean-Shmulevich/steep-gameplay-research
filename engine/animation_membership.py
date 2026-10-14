"""Selected animation registry-copy block; callers supply a stable source view.

Native synchronization, allocation failure and registry ownership are not modeled.
An empty source preserves the destination, including its existing active count.
"""
from dataclasses import dataclass, field


@dataclass
class AnimationMembership:
    storage: list = field(default_factory=list)
    count: int = 0

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
