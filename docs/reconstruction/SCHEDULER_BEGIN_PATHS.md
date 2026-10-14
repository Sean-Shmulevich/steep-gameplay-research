# Empty ranges and callback jobs take different begin paths

The [live scheduler capture](NATIVE_SCHEDULER_OBSERVATION.md) observed advancing request counts while every sampled execution count was zero. Matching the concrete tables to their begin and empty-predicate methods narrows the possible explanations.

| Jobs in the observed graph | Empty predicate | Ordinary begin behavior |
| --- | --- | --- |
| Pre-action gather, Kino pre-graph, action gather | Always false | Queue the callback job |
| Character action, skeleton begin, animation time, interaction state | Signed remaining count at `+0x1a0` is less than or equal to zero | Finalize immediately when empty; otherwise queue |

The callback table is `141e89618`, with predicate `1402aa0c0`. The range table is `141ec7f38`, with predicate `1408eb040`. Both bind common begin `1411d1540` and ordinary finalizer `1411d1670`. These are the same table identities matched during the live captures.

## Recovered decision sequence

```text
begin(job):
    lock(job)
    if job.state == SCHEDULED:
        unlock(job)
        return

    job.started = job.requested
    activate_outgoing_dependencies(job, recurse=false, context=job)

    if not job.empty_predicate():
        enqueue(job)
        job.byte_195 = 1
    else:
        lock(job)
        if job.state == SCHEDULED:
            remove_from_queue(job)
        else:
            job.state = DONE
        unlock(job)
        job.finalize()
    unlock(job)
```

The second state check occurs after dependency activation, which can have side effects. It should not be removed merely because entry already checked for SCHEDULED. The local begin routine does not increment either execution counter. Queue reservation and the explicit helper establish those counts on their inspected worker paths.

The range predicate uses a signed comparison. A negative count therefore satisfies it in the inspected instructions, but this does not establish that negative counts are valid runtime workloads. The independent scheduler continues to validate supplied receiver populations rather than accepting corrupt native headers as valid work.

## Consequence for the live observations

An empty animation range can advance its started count, release dependencies and return to unscheduled without a worker dispatch. Therefore zero execution samples plus changing request counts do not demonstrate that animation receivers ran.

That explanation does not apply to the three matched callback jobs' ordinary begin method: their predicate always returns false. An empty receiver list cannot make their begin method take the immediate-finalization branch. Short queued execution between samples remains a concrete explanation for their zero samples. Alternative invocation paths remain possible, but this pass found no new path that removes the established accounting.

Neither the shared table nor its empty predicate proves the selected player's animation component belongs to a particular range. The population must still be read and joined through ownership. The next capture should pair population evidence with a targeted observation of one callback execution interval; another broad series of zero counters would not resolve either issue.

## Runnable reconstruction example

```sh
python3 -m engine.examples.scheduler_begin_probe
```

The [example](../../engine/examples/scheduler_begin_probe.py) uses the recovered seven-job partial topology with deliberately empty synthetic range populations. All four range jobs acknowledge and finish their requests without dispatching receiver bodies. Three callbacks still execute. Every sampled between-job boundary has zero execution counts, while observations inside each callback report one execution and one outstanding dispatch.

This demonstrates how boundary sampling can miss real work in the independent model. It does not assert that the live game's populations were empty, or that its polling happened at these exact boundaries. Two tests verify the empty-range effects and retained callback execution evidence.

## Native instruction validation

The [receipt](scheduler_begin_validation.json) records 90 isolated cases using the original begin routine and concrete predicates. Coverage combines two job types, lifecycle states 0/1/2, signed remaining counts at negative/zero/positive boundaries and three requested values including `0xffffffff`.

Synthetic objects and recording stubs replace locking, dependency activation, queue insertion/removal and finalization. Queue/finalizer state effects are stubbed. Tests assert selected branch, acknowledgement behavior, callback ordering, unchanged execution counters in the local routine and the enqueue-side byte write. Stubs clobber volatile registers. This proves the tested local decisions, not complete dependency effects, native threads or the path taken by the live session.
