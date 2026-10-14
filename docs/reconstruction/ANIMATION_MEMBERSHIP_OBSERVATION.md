# Joining a player entity to the animation registry

The [passive reader](../../engine/animation_membership_observation.py) follows the already-established world-to-action-graph link, then reads animation event slot 16 and the gathered storage header. It identifies source receivers whose table matches `KinoComponent` and whose owner pointer matches the supplied player entity.

This answers a narrower question than execution. A registered receiver may not have been copied into the current job, and a pointer retained in allocated job storage may belong to an earlier request.

## Live result

A fresh acquisition in a bounded Highball/D3DMetal gameplay session found four source receivers and four allocated destination slots. Exactly one source receiver matched the selected player's entity and the Kino table. It appeared at zero-based source index 3 and destination storage index 3. Remaining-to-claim was zero, so it was not in the sampled unclaimed prefix. All rechecked headers, arrays and identity fields matched.

The [sanitized receipt](live_animation_membership_validation.json) records this observation and hashes of the private acquisition/results. It establishes selected-player registration in this observed animation source list and a matching stored pointer. It does not establish when that pointer was copied, which request claimed it, whether its callback ran, or whether its internal readiness gates allowed an animation update. The current source was nonempty; an empty current registry cannot explain this particular sample. Historical empty gathers remain possible.

Startup navigation reached gameplay; the capture sent no riding input and used no debugger or game-memory writes. The research bottle was stopped after the successful capture, and its watchdog restored settings. Raw addresses, memory receipts and screenshots remain private.

## API and observations

```python
from engine.animation_membership_observation import capture_membership

# readv must check current process identity and enforce timeouts.
# entity/world must come from fresh player acquisition, not a saved address.
report = capture_membership(readv, entity, world, image_base, identity_guards)
```

The returned matches contain three separate index lists:

| Observation | Supported interpretation |
| --- | --- |
| Source index | A source receiver has the Kino table and belongs to the supplied entity |
| Storage indices | Its pointer value appears in allocated gathered storage, possibly in an inactive tail |
| Unclaimed-prefix indices | Its pointer value appears before the sampled remaining-to-claim count |

The latter two compare pointer values without dereferencing destination entries. They do not establish a request generation, a claimed span's owner, or callback execution. If no matching source receiver exists, the reader does not infer the identity of an unregistered component from leftover destination storage.

The source count is bounded to 256 and storage capacity to 1024; over-limit captures fail rather than report a truncated absence. These are observation budgets, not recovered game limits. All followed headers, source entries, source receiver table/owner fields and destination storage are rechecked before returning. Mutable middle fields of component headers are excluded from identity guards. Reads remain sequential and matching rechecks do not prevent allocation reuse or changes that occur and reverse between reads.

The caller must provide external player/process identity guards. Matching a component owner only connects it to the supplied entity; the reader cannot independently know whether that entity is the selected player. Image identity checks and read timeouts remain the transport's responsibility.

## Evidence behind the layout

- [World/graph join](SCHEDULER_OBSERVATION.md): entity world at `+0x60`, world action graph at `+0x1038`, graph world backlink at zero.
- [Registry](ANIMATION_EVENT_REGISTRY.md): source pointer/count/capacity header at world+`0x530`; low 29 bits of capacity hold the capacity value.
- [Gather copy](ANIMATION_MEMBERSHIP_COPY.md): destination pointer/count/capacity at graph+`0x3c88`; count is consumed as ranges are claimed.
- [Component identity](ANIMATION_COMPONENT_DISPATCH.md): Kino table `141f289d0`, entity owner at component+`0x10`.

No lock is acquired inside the target process. A failed consistency check is an inconclusive capture, not proof that the entity lacks animation. A positive source match is a passive membership observation; `callback_execution_established` and `safe_to_step_established` remain false.

## Validation

Six synthetic reader tests cover a matching source with stale destination storage, a nonempty unclaimed prefix, an empty source with retained storage, source replacement during capture, malformed/oversized storage headers, wrong-world links and incomplete reads. Fixtures include a same-class component belonging to another entity and an invalid stale storage pointer that must never be dereferenced. These checks validate collection semantics, not native synchronization.

The next discriminating experiment should observe the matched component's update entry/exit and packet interval, retaining request and thread identity. A source match plus zero claim count is not a reason to write scheduler state or assume a safe pause.
