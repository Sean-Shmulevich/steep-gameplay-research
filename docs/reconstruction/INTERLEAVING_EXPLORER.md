# Bounded worker-interleaving exploration

`engine.interleavings.explore(definitions, queue_policy, roots, max_nodes=2000,
max_depth=64)` explores symbolic ordinary-worker API orderings. It uses the
[worker topology model](QUEUE_POLICY_MODEL.md) and repeats every branch from a
fresh scheduler. No live process, native address or game payload is required.

Run the included fixture:

```sh
python3 -m engine.examples.interleaving_probe
```

The two-receiver, two-worker fixture explores 315 nodes and 96 completed schedules
with no blocked leaves or invariant violations. These counts describe that exact
fixture, not general scheduler coverage.

## Boundaries explored

At each API boundary, the explorer enumerates each present worker's enabled action:
reserve the selected eligible job, claim a range, execute the retained range,
execute a callback or finish a returned dispatch. Each worker owns at most one
ordinary dispatch. Range claims and range execution are separate actions, so one
worker may hold receivers while another claims and completes different receivers.

Job bodies are symbolic. External handlers and predicate handlers are rejected
because replaying them could repeat side effects outside the model. Explicit
Boolean conditional jobs are allowed under the existing activation contract.
There is no branching inside a receiver body, atomic operation or dependency
release. Early-exit flags, submission during callbacks, world replacement and
nested helping are outside this exploration alphabet.

## Checked invariants

At each visited boundary, execution/outstanding counts must equal retained
dispatch counts, workers must not hold multiple dispatches, and remaining receiver
counts must be nonnegative. Trace-based checks reject overlapping or out-of-bounds
claims, duplicate or unclaimed receiver returns, and loss of receiver-count
conservation. The driver has no mid-callback checkpoint requirement: replay
constructs new tokens and executes the recorded worker/action prefix.

This is model checking of selected recovered rules and explicit adapter policies.
It does not establish native memory ordering, real thread races, platform event
semantics, callback workload correctness or native pause safety.

## Reading reports

`complete` means all enabled paths in this model finished exploration within the
bounds, with no detected invariant violation. It does not mean every path drained.
`quiescent_leaves` and `blocked_leaves` remain separate. A job rejected by affinity
can yield a complete exploration whose only leaf is blocked.

`status: bounded` means pending paths or depth cutoffs remain. `status: violation`
contains the worker/action path and failed invariant. Counts are traversal counts,
not deduplicated state counts. Up to four leaf examples are retained; they are not
an exhaustive trace archive. Independent repeated fixture runs produce the same
report because random dispatch-capability identities are excluded from reports.

Adapter limits are 10,000 nodes and depth 128. The default bounds intentionally
make larger experiments report incompleteness rather than silently skipping work.
The graph, worker layout and root submissions are fixed for each exploration.
