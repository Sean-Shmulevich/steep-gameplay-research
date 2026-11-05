

### Live invocation capture

The two snapshot checks evaluated captured state offline. This check records
real in-game calls of `18b8860` instead. The receipt is
`native/snow_host/pose_connectivity_live_invocation_validation.json`.

**Capture point.** `18b8860` has exactly two static call sites, `18b8757` and
`18b8776`. Both are inside controller listener `18b8670`, in event 0. Nothing
calls `18b8670` directly, and no image pointer to it is stored. It is reached
only through a row of the global body-listener registry (descriptor pointer at
image `0x33367c0`), which broadcaster `18a7f60` calls as
`row.callback(body, event)`.

A private plugin swapped that one row's callback to a detour, using an aligned
8-byte compare-exchange on heap data. No code bytes or page protections were
changed. The detour always forwards to `18b8670`. Before installing, the plugin
checked:

- the image base;
- fingerprints of `18b8670`, `18b8860` and `18a7f60`;
- that both call sites decode as `call rel32` to `18b8860`;
- that exactly one enabled registry row holds `18b8670`.

On restore, the plugin scanned the current registry for rows holding the detour,
compared and swapped them back, waited for in-flight calls to drain, and kept
the module pinned.

The detour classifies each event-0 call by the listener's own gate:

- **Path A:** priority bit 15 clear and metadata+0x1c != controller+0x4c. The
  listener stamps the metadata and calls `18b8860`.
- **Path B:** priority bit 15 set and quiet nibble 2. The listener calls
  `18b8380`, then `18b8860`.
- **Neither:** any other event-0 call.

For path A calls, the plugin copies the walked refresh regions just before
the listener runs and again just after it returns, using self
`ReadProcessMemory`. The regions are: body, metadata, owner, controller,
context, provider with its node array, slot owners and their +0x28 vectors,
+0x80 ring links, endpoint bodies with their metadata and rings, tree values,
contact spans, and groups with their slot arrays and members. Session 1
captured the first 32 path A calls. Sessions 2 and 3 captured only calls whose
+0x80 head was nonempty, at most 4 per body.

Offline, the expected post-state is the pre-state plus the listener stamp,
with `analyze.run_python` (same stubs) applied. That is compared with the
post-state the game produced at every captured address. Differences are
attributed to the services that really ran in game (`18e2de0`, allocator,
pool return, listener enter/leave). Any other difference is unattributed and
fails the pair. Native `18b8860` also runs in Unicorn on the stamped pre-state
as a coverage cross-check.

**Results.** Three sessions used director startup and forward holds (scan 17,
1500 ms). The plugin armed when a player body first had a controller and a
+0x80 head. Install windows were 150, 150 and 300 s. In every session the row
was restored (no conflicts, the detour absent afterwards, one `18b8670` row) and
in-flight calls drained. Cleanup was fully verified.

While installed, the listener received 149,689 calls, 90,549 of them event 0.
Of those:

- **Path A:** 10,552 calls.
- **Path B:** 0 calls.
- **Neither:** 55,535 calls.
- **No controller:** 24,462 event-0 calls had a null or unreadable controller
  chain.

Every path A call whose ring state was recorded had an empty +0x80 ring: the 32
captured, plus 6,775 and 3,694 counted in sessions 2 and 3. The other 51
session-1 calls were not split. Session 3 counted 3,694 path A calls on 1,276
distinct bodies, all with class table `0x29c98c8` and none of them player
bodies.

Session 3 also counted event-0 calls on bodies with a nonempty ring: 19,078,
all with priority bit 15 set and quiet nibble 0, so the listener calls neither
`18b8380` nor `18b8860`. Of these, 18,516 were on the player's main and rider
bodies, which carry priority `0x8002`.

The 32 captured invocations, all on world bodies, each matched the Python
chain:

- **Path taken:** empty-ring early return, with no rows, selection or service
  calls.
- **Bytes:** 405,296 bytes compared. Of these, 64 changed in game: exactly the
  four stamp bytes per call, all predicted.
- **Differences:** 0 unattributed differing bytes. Nothing else in the captured
  regions changed, including the controller enter/leave bytes and any effects
  of `controller28` virtual+a8.
- **Cross-check:** Unicorn agreed with Python in 32 of 32 runs, with 0
  coverage gaps.

Pre and post reads ran on the same thread around each call. Sampled walks took
0.05–0.9 ms.

**Interpretation.** The empty-ring early return is now confirmed on real
invocations. The selection, rebuild and retire paths were not reached by any
observed in-game call. The bodies that carry selector-1 links (player and
ragdoll/world bodies) receive event 0 only with priority set and quiet 0. Session 2's
window included two crash detaches and one respawn. Those paths
therefore remain validated only on synthetic data and live snapshots.

Limits:

- **Atomicity:** pre and post reads are sequential self-reads, not atomic.
- **Bracket:** the capture brackets the whole listener call, not `18b8860`
  alone.
- **Untested branch:** path B never occurred, so it was never tested.
- **Removal hazard:** native removal `18bb610` does not guard a failed search.
  Short install windows bound this hazard but do not exclude it.

**Leads.** Nonempty-ring refreshes probably come from somewhere other than this
listener branch. Candidates are a quiet-2 wake (path B), or link creation
paths that call the selection, rebuild and retire services directly. Next
steps:

- Find other callers of `18dedf0`, `18e28d0` and `18de440`.
- Capture around priority-set bodies whose quiet nibble becomes 2.
