"""Recovered ordered action-processor composition, with explicit child kernels.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Ordered processor-chain kernel.
Does not infer children, configuration lifetime, clocks or device input units.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ProcessorStageResult:
    index: int
    invoked: bool
    raw: bytes
    working: bytes
    published: bytes

@dataclass(frozen=True)
class ProcessorChainResult:
    output: bytes
    stages: tuple[ProcessorStageResult, ...]


def process_chain(value, configuration_flags, evaluate):
    """Compose supplied child kernels; None means no resolved configuration.

    A resolved false flag bypasses the child. True or None invokes it. Each
    visited child's raw and working fields start with the preceding output;
    published output is copied back to the parent's accumulator. Bypassed
    children still publish that unchanged input. evaluate(index, raw16) must
    return the child's raw 16-byte output. No child method is substituted.
    """
    if not isinstance(value,bytes) or len(value)!=16:
        raise ValueError('input must contain 16 raw bytes')
    flags=tuple(configuration_flags)
    if len(flags)>65535 or any(x is not None and type(x) is not bool for x in flags):
        raise ValueError('uint16 stage count and bool-or-None flags required')
    stages=[]
    current=value
    for index,flag in enumerate(flags):
        raw=current;invoked=flag is not False
        if invoked:
            current=evaluate(index,raw)
            if not isinstance(current,bytes) or len(current)!=16:
                raise ValueError('child output must contain 16 raw bytes')
        stages.append(ProcessorStageResult(index,invoked,raw,current,current))
    return ProcessorChainResult(current,tuple(stages))
