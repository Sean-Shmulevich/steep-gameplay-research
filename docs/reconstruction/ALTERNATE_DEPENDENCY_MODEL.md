# Executable alternate dependency propagation

[The alternate-dependency module](../../engine/alternate_dependencies.py) implements the two callback shapes established by the [alternate release audit](ALTERNATE_DEPENDENCY_RELEASE.md): an ordinary callback with one outgoing list, and a conditional callback with primary and secondary lists. It makes their different effects from normal release testable on synthetic graphs.

This is a serial behavioral reference with caller-declared callback bindings. It does not interpret arbitrary native subclasses, reproduce recursive locks or atomic interleavings, cancel executing work, or establish a safe native pause/unload boundary. There is no native-game interaction.

## Graph and API

The JSON graph contains:

- `jobs`: recipient ID to the state schema from [request-state rules](REQUEST_STATE_MODEL.md).
- `lists`: list ID to the request-state dependency-list schema, including active flag and ordered successors.
- `bindings`: each job ID to either `{kind: "ordinary", outgoing: list_id}` or `{kind: "conditional", primary: list_id, secondary: list_id}`.

An ordinary leaf uses an empty outgoing list. IDs and callback kinds are explicit fixture inputs. A name such as “terminal” does not choose a callback automatically. Credit-recipient arrays remain part of the shared list schema but alternate release does not visit them.

`new_graph(jobs, lists, bindings)` validates and copies the fixture. `release_alternate(graph, list_id)` mutates only hold counts and list activation flags, returning an ordered trace. `on_alternate_last_hold(graph, job_id)` invokes the selected callback directly with its independent current-count check. `decrement_alternate_hold(job)` performs only the decrement and returns whether the previous count was one.

The last two APIs allow a specific synthetic interleaving: decrement the last hold, introduce a fresh hold using an independently modeled operation, then enter the callback. The callback observes the fresh nonzero count and does not propagate. This demonstrates why the old atomic-value test and the callback's current-value check cannot be collapsed into one condition. It is not a concurrent test or evidence that this interleaving occurred in the game.

## Preserved behavior

Alternate list release visits successors in stored order. It calls a successor only when decrementing that successor changes holds from one to zero. A two-to-one change has no recursive callback. The list stays active through descendant traversal and clears only after all its successors return.

An ordinary callback with current holds zero releases its active outgoing list alternately. A conditional callback with current holds zero does the same for primary, then secondary. It does not evaluate a predicate, choose one route, or begin either route normally.

No alternate operation changes requested, started, credits, credit gate, deferred flag or lifecycle state. In particular, a pending request with requested seven and started six retains that mismatch after bypass. The trace reports `alternate_callback` and `alternate_list_cleared`, never “completed job” or “normal begin.”

The implementation traverses a detached working copy to make validation failures transactional. Within that working copy, the trace preserves after-traversal clearing. On success, only holds and active flags are committed to existing caller objects. Their Python identities are preserved. This transaction boundary is adapter behavior, not a native atomic snapshot or lock protocol.

## Reconvergence depends on release order

Suppose a shared join has two holds, one from the selected route and one from an unselected route. Its requested count exceeds its started count.

| First release | Last release | Local result |
| --- | --- | --- |
| Alternate removes one hold | Normal removes the last hold | Normal eligibility and credit checks may emit a begin invocation |
| Normal removes one hold | Alternate removes the last hold | Alternate callback propagates bypass; it does not inspect the earlier normal release or emit begin |

The tests implement both orders against the same synthetic topology. The first case leaves the join's outgoing dependencies active until the selected work actually completes through its separately modeled path. The second case bypasses those dependencies while preserving the pending request. An order-independent “execute if any predecessor ran” rule would incorrectly merge these outcomes.

For a conditional begin whose receiver has been identified, the audited order is alternate release of the unselected list followed by normal release of the selected list. Use the two modules explicitly:

```python
from engine import alternate_dependencies as alternate
from engine import request_state as requests

# graph is a validated, pre-held synthetic fixture.
trace = alternate.release_alternate(graph, "unselected")
effects = requests.release_normal(graph["lists"]["selected"], graph["jobs"])
# effects are still virtual-call boundaries. Resolve them separately;
# they do not mean any ordinary body or finalizer has executed.
```

The existing normal-release batch reducer has an explicit limitation when its opaque callbacks would mutate later recipients. This module does not remove that limitation or supply a general mixed normal/alternate interpreter.

## Validation and scope

The adapter accepts at most 128 jobs and 256 dependency-list objects, with a configurable bounded event count per operation. An exceeded limit or invalid hold decrement leaves the graph unchanged. Counter validation follows the request-state operational domain; native wraparound and corrupt objects are excluded.

Cycles are rejected even when their lists are currently inactive. This prevents an adapter from pretending to solve reentrant cyclic ownership or native locking semantics. Duplicate successor entries under one canonical ID are retained and remove distinct holds. Different IDs aliasing the same Python job or list object are rejected. Neither restriction is claimed as an original engine policy.

Full JSON roundtrips preserve this model's future behavior. No callback code, host clock, thread state, native address, hidden generation or physics state is included. The bindings must still be justified by the caller for any compatibility claim.

The module follows the static relationships documented in [the source audit](ALTERNATE_DEPENDENCY_RELEASE.md); this implementation pass adds synthetic execution tests, not new native runtime observations. [Ten tests](../../tests/test_engine_alternate_dependencies.py) cover both reconvergence orders, nested conditionals, after-traversal clearing, pending requests, current-count recheck, ignored credit recipients, inactive lists, cycle/alias rejection, underflow and event-limit rollback, duplicate entries, checkpoint equivalence and preserved object identity.

Run `python3 -m unittest discover -s tests -p 'test_engine_alternate_dependencies.py'` from the repository root.
