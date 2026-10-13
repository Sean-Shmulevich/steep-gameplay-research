> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Global action callback ownership

Run38 proves the global vector callback's construction and captured receiver. A separate callback owner holds the callable, and the manager that creates that owner becomes the callable's receiver. The actual vector target is selected, but its action-storage read and freshness remain untraced at this pass's eight-root export limit.

All work was static and offline. No game, process, debugger, remote host or input device was accessed. [Private evidence](evidence.md) gives the exact register and stack lifetimes. Verification (`private/verification.json`; source artifact, not distributed) checks 1,452 exported instructions against the frozen image and selected ownership edges.

## New versus run37

- The planned unwind-covered inventory found eight global references across 30,672 function fragments. Its only store clears the global during deletion. A bounded gap scan within the same ranges found the missing constructor, a leaf without unwind coverage. A selected direct caller establishes its instruction alignment and reachability.
- The manager constructor allocates 736 bytes for a separate callback owner, invokes the owner constructor, then invokes the binder with the manager as its argument. The owner constructor installs the destructor-supported table and publishes its own address in the sampler's global. This closes the receiver ownership join that run37 lacked.
- The binder loads that same global once. Two 16-byte stores install the vector callable. Its stored function is the selected manager-vector target; its captured receiver is the constructing manager with the low two tag bits removed at invocation. Its invoker unwraps those fields and passes the caller's action ID to that function.
- Constructor publication occurs before callback binding. Binding writes callable contents in separate stores. This local order supplies no atomic publication protocol, concurrent-use safety claim or source generation.
- The adjacent scalar getter is a different callable. Its exported leaf reads a manager integer field and returns it. It does not establish vector storage, receipt age or a generation. The retained receipt records a rejected candidate caused by initially following the next stack assignment instead of the value already loaded into the vector copy.

The carrier's separate enable/inversion source still does not own the callable. The state-vector override remains a second producer. No new scheduler dependency, action commit order, input acceptance time or video-frame age was proved.

## Boundary

The selected manager-vector function is the next exact trace. This pass used eight exported roots, each below 24 KB. It stops before exporting that function or following its storage lookup. Manager identity is now known for the global callback route, but equality with the ordinary motion-ingestion manager and its stored sample still requires the next function's actual read. Similar action IDs and matching field offsets remain insufficient.

The existing passive experiment remains a transition-observation proposal. There is still no linked source generation or timestamp for an exact latency calculation. [Next step](next-investigation.md) replaces the broad owner search with one selected function and its storage edge.
