# Scheduler input and publication audit

The input-to-physics boundary is partly reconstructed. Motion ingestion and snow sampling can resolve the same action vector, but they read it at different call sites. Later studies decoded local action writers and measured the selected actor callback returning before PhysicsWorldStep in 701 matching requests. The remaining link is the selected writer's publication timing and the gated ingestion call itself, rather than the outer actor callback's placement. See the [consolidated route and capture contract](INPUT_TO_ACTION_ROUTE.md#joining-the-player-route-already-observed). A full scheduler reconstruction must keep these questions separate from reproducing the timestep arithmetic.

This audit consolidates existing static and runtime research. It includes no new game execution, debugger attachment or input injection. The follow-up below verifies selected existing exports against the analyzed image. Semantic names below are explanatory. The proposed release gates are requirements for our implementation or future experiments, not recovered engine guarantees.

## Evidence reconciliation

Read the [shared action storage result](research/input-probes.md) after the older [callback ownership findings](../systems/input/action-ownership/findings.md). The earlier report deliberately stopped before the concrete vector getter. The later pass closes its action-storage lookup; it does **not** close sample freshness. Both conclusions remain useful when their scope is preserved.

The [scheduler research](research/scheduler.md) supplies the world/substep and downstream publication relationships. [Animation scheduling](../systems/animations/scheduling/CLIENT_GUIDE.txt) and [field binding](../systems/animations/field-binding/CLIENT_GUIDE.txt) describe a separate lazy producer cache. The latter's historical open reset question is answered by the former: full evaluation clears readiness afterward, while deferred evaluation retains it.

Original research-document and published-document hashes are recorded in [SOURCE_MANIFEST.json](../../SOURCE_MANIFEST.json). This audit also reviewed the retained input-timing source findings that underlie the scheduler synthesis, particularly the separate motion-state override and periodic release-work paths. No unavailable source artifact is required to understand the contracts below.

## Boundaries we can state

| Boundary | Supported behavior | What it does not establish |
| --- | --- | --- |
| Callback construction | A separate callback owner captures its constructing manager; the vector invoker forwards the action ID to that receiver | A lifetime guarantee, exclusive binding writer or immutable callback publication |
| Context/action lookup | Current selector chooses a context; three groups are traversed in stored order, bindings in reverse; a blocker can terminate fallback search | Stable context selection throughout a concurrent update or semantics for all tagged map variants |
| Action-vector read | Both identified routes read the same payload vector when manager, selector, action, binding and lookup result match | Same contents, device-event identity, units, coordinate frame or sample age |
| Missing action | The analyzed image's shared fallback vector is zero | Runtime immutability of fallback or equivalence between an absent action and a sampled zero |
| Motion ingestion | Selected action values update motion inputs and consecutive-nonzero counts before carrier preparation and state dispatch | A count of new device events, frames or completed physics steps |
| State override | A selected motion state can produce an optional physical-control vector; the snow route reads it under the motion owner lock | Its production immediately precedes the consuming snow invocation |
| Snow sampling | Eligible snow work samples raw physical controls before cache refresh, cooking and forces | Every snow branch uses the action store; disabled, restricted and configured-source branches differ |
| Body capture | The pending cache captures body velocity before that invocation's snow impulses | Its velocity equals post-integration body velocity |
| World completion | The recovered dependency permits the post-physics component route after the world-step body completes | All predecessor worker accounting has returned, or all animation work follows it |
| Cache publication | A gated player pose route exchanges cache roles, reads body pose and copies published cache velocity toward actor/motion state | Exactly one exchange per displayed frame, a generation check or a general read-only pose accessor |
| Animation scalar read | An unready mapped producer runs before its result is read; full graph evaluation later invalidates readiness | A universal latest-physics value, once-per-render-frame production or original sport/clip selection |

The state override is materially different from raw player action input: the inspected producer uses published actor velocity and an entity-context transform, computes an alignment, normalizes four lanes, suppresses positive Y and conditionally limits X. No camera-owner join was established for this slice. Its getter copies before pending motion-state transitions are processed.

## Supported partial order

There is no unconditional selected-player arrow between the first two roots below. The follow-up establishes one candidate motion batch as an upstream dependency, conditional on player membership, actor gates and the matching active job request. Each root must retain its own invocation identity in a trace.

```text
motion_route(actor):
    if actor_and_motion_gates_pass:
        actions = sample_motion_actions()
        update_consecutive_nonzero_counts(actions)
        prepare_control_carrier()
        dispatch_state_under_motion_owner_lock():
            if selected_state_and_its_gates_pass:
                produce_optional_override_from_actor_and_context()

world_request(world, selected_schedule):
    for substep in selected_schedule:
        run_snow_actor_batch_and_wait():
            if selected_actor_gates_pass:
                apply_optional_body_corrections()
                override = copy_guarded_motion_override()
                raw = sample_carrier_branch(override)
                pending_cache = capture_body_before_current_snow_impulses()
                refresh_histories()
                periodic = test_old_periodic_accumulator()
                if periodic: subtract_threshold_once()
                cooked = cook_remapped_controls(raw, elapsed_dt)
                if periodic_flag == 1:
                    update_coil_rate_and_release(cooked, derivative_dt)
                build_rider_targets(cooked, new_or_retained_rate)
                apply_snow_impulses_and_velocity_postprocessing()
                periodic_accumulator += elapsed_dt
        integrate_backend_world(elapsed_dt)
        run_following_world_work()
        run_second_actor_batch_and_wait()
    complete_world_step_body()
    # Recovered successor dependencies permit the post-physics route.

post_physics_component_route():
    if same_world_player_and_component_gates_pass:
        dispatch_player_pose_state()
        if physical_cache_branch_selected:
            exchange_pending_and_published_cache_roles()
            read_body_pose_under_its_lock()
            actor.velocity = published_velocity_or_zero_by_gate()
        apply_exceptional_velocity_guard()
        if snapshot_refresh_allowed:
            motion.cached_velocity = actor.velocity
```

The second actor batch inside each substep is not the named post-physics component job downstream of the outer world step. Conflating these would publish at the wrong cadence.

The optional override may be retained from an earlier state dispatch. Multiple substeps can overwrite the pending cache before publication. Published actor and motion velocities can agree with each other while differing from the current backend body. None of these facts implies a fixed one-frame lag. The [moving contact observation](../validation/contact-motion.md) remains an asynchronous observation, not proof of same-substep execution.

## Input lookup and lock extent

```text
sample_vector(manager, action_id):
    selector = manager.current_context_selector
    enter_manager_read_accounting()
    action = lookup_context_action(selector, action_id)
    payload = action.payload if action exists else shared_fallback
    leave_manager_read_accounting()
    return copy_four_lanes(payload.vector)
```

The selector load precedes entry to the helper. Its accounting decrement precedes the caller's vector copy. This does not prove a race in the original game: other ownership guarantees may exist. It does mean the recovered helper alone cannot justify an atomic action snapshot or keep a selected action alive through the whole read.

Similarly, a lock protecting the override copy does not order the input manager's writer, motion job and world job unless their actual dependencies are joined. The field-storage lock used for an animation scalar copy does not establish a globally synchronized animation producer cache.

The construction sequence publishes the callback owner's identity before completing all initialization and binds the callback with separate stores. The observed local order is not a protocol for installing hooks concurrently. Callback rebinding and manager replacement remain part of identity validation.

## Clocks that must remain distinct

| Value | Known use | Invalid replacement |
| --- | --- | --- |
| Outer consumed interval | Supplies the recovered derivative interval | Unconditionally replacing it with per-substep elapsed time |
| Per-substep elapsed interval | Advances cooking, forces and appropriate timers | Treating selected frequency as a guarantee of fixed elapsed time |
| Periodic input accumulator | Tests the old value, subtracts the threshold at most once and adds elapsed after snow work | A subdivision loop or sample-generation counter |
| Animation accumulated interval | Deferred callbacks preserve accumulated time; full evaluation consumes accumulated plus current time | Advancing graph time once per arbitrary display frame |
| Host capture timestamp | Bounds when the inspector read a group | Native commit time or the age of an input event |

A nonperiodic snow invocation retains previous rate/release fields while still cooking controls. Repeated raw input can still be consumed. An animation field may stay unchanged because its producer group remains ready. These are three different explanations for a flat telemetry line.

For animation, the established reset order is:

```text
if graph_exists and cached_path_conditions_pass:
    run_cached_callbacks(current_dt)
    accumulated_dt += current_dt
    keep_producer_readiness()
else if graph_exists:
    effective_dt = accumulated_dt + current_dt
    accumulated_dt = 0
    reset_defer_counter_and_release_cached_entries()
    evaluate_graph(effective_dt)
    clear_producer_readiness()  # after evaluation
```

The complete byte-counter, pending-count and flag predicate is in the [animation scheduling guide](../systems/animations/scheduling/CLIENT_GUIDE.txt). This abbreviated branch is not a replacement for it.

## Concrete next static leads

1. **Action payload construction and writes.** Start from the concrete vector getter and its action-map return type, already joined in [input probes](research/input-probes.md). Identify the constructor and insertion path that supplies map values; then enumerate direct vector writes and whole-payload copies on that same type. A common field displacement alone does not identify an owner.
2. **Writer publication.** Follow those concrete writes to the enclosing update/commit routine. Determine whether it protects lookup only, vector mutation, ownership replacement, or all three. Any counter must be traced from its writer to both consumers before calling it a sample generation.
3. **Ingestion job registration.** Starting at the proven motion-ingestion caller, identify its installed callback, owning job and submission site. Join that specific owner/request to the world request's predecessor graph. Similar job names or membership lists are insufficient.
4. **State override ordering.** Join the selected motion-state dispatch to the guarded override getter with owner identity and invocation boundaries. Check pending transition handling separately; a requested state is not a committed new state.
5. **Publication cardinality.** Enumerate callers of the selected physical-cache pose route and identify which are post-physics publication versus other queries. Count actual cache exchanges within one owner/request epoch before asserting one publication per request.
6. **Submission exclusion and lifetime.** Trace the caller that stops accepting new work, all already-claimed worker ranges and the ownership release sequence. The known drain observation and callback caching behavior cannot alone support pausing, patching or unloading an adapter.

The existing [callback evidence](../systems/input/action-ownership/evidence.md) identifies exact build-specific targets for researchers with the analyzed image. Portable implementations should depend on the semantic contracts above, not literal addresses.

## Release gates for probes and reconstruction

| Milestone | Evidence required before claiming it |
| --- | --- |
| Shared action-source observation | Matching manager, binding, selector, resolved action, nonfallback status and owner epoch; record field-group read spans and reject changing links |
| Input age measurement | A proved source writer/version, that version observed at each consuming sampler, a matching world/substep invocation and publication attribution; repeated equal values are not version evidence |
| Execution trace | Matched entry/exit records, nesting and thread identities, explicit capacity/drop reporting and dependency attribution; ticket order is not cross-thread causal order |
| Native pause/step experiment | Exclusion of new submissions, completion of claimed callbacks including cached callback pointers, required thread/TLS ownership and safe object lifetime; an observed drained state alone fails this gate |
| Reconstructed input contract | Separate raw action, motion state, physical control and cooked state; preserve context precedence, fallback identity, override branch and distinct read moments |
| Reconstructed scheduler fidelity | Match recovered subdivision and derivative/elapsed semantics, relevant conditional dependencies, pending work completion and publication ordering; identify every chosen serial ordering not recovered from the original |
| Deterministic replay claim | Complete owned checkpoints and reproducible traces under a stated implementation/build; comparison with original event traces is separately required for native equivalence |
| Mod callback API | Defined lifecycle, allowed phase and mutation scope, failure containment, stable owned handles, explicit ordering and capture of mod/version state in replay |

For our reconstruction, explicit input packets, monotonically increasing owned generations and immutable published snapshots are sensible interfaces. Their names and guarantees must be labeled as our design. For the original game, observations should remain read-only and asynchronous until the stronger gates are met; this audit does not authorize or implement a live hook.

A reconstructed scheduler would let us expose reliable phase-specific probes and mods in the replacement engine. It would not automatically establish compatibility with original binary mods, make arbitrary injected calls safe, or resolve the original input source's missing publication protocol.


## Focused follow-up: one motion batch is upstream of world simulation

Inspection of the actual retained function exports closes a useful conditional edge: the pointer-array motion batch named `Physic::PreBeforeSimulation` is a predecessor of `Physic::BeforeSimulation`, which is a predecessor of `PhysicsWorldStep`. The same setup routine installs the generic actor motion-update callback in that first batch. This combines callback ownership with dependency topology; it is stronger than relying on the job's name.

The specific supporting operations are:

1. The action-graph setup computes the `PreBeforeSimulation` job address and stores the generic receiver motion-update thunk into that job's callback field. The adjacent name setter supplies its name. The range executor caches that field and passes each array element as the receiver, without adjustment.
2. The thunk dispatches the receiver's virtual motion-update method. The selected player table binds that method to the inspected player update. With its activity/controller gates satisfied, that method passes its embedded motion object to the routine that directly calls action ingestion, followed by carrier preparation and motion-state dispatch.
3. The setup routine preserves the first job address and the `BeforeSimulation` address in distinct registers until registering the first as the predecessor of the second. Both use the previously established successor-registration method.
4. Its physics-service call supplies that same `BeforeSimulation` job. The concrete service method obtains the physics state through the world manager, retrieves the stored world-step job, and registers it as a successor. The physics-state constructor identifies that stored job as `PhysicsWorldStep`.
5. The candidate batch's array builder copies receiver pointers from its world's registration list without adjusting them. This identifies where to test selected-player membership; it does not establish that membership in a current process.

```text
construct_selected_world_graph():
    pre_before.invoke = generic_motion_update
    register_successor(pre_before, before_simulation)
    register_successor(before_simulation, physics_world_step)

execute_pre_before_claim(claimed_receivers):
    invoke = pre_before.invoke  # cached for this claimed range
    for receiver in reverse(claimed_receivers):
        invoke(receiver)
        # If receiver is the selected player with the supported table,
        # and its gates pass, this reaches motion action ingestion.

# Under the registered active prerequisite chain and matching owner/request:
finish_pre_before_body_and_context_callbacks()
    -> permit_before_simulation_after_its_other_prerequisites()
    -> permit_physics_world_step_after_its_other_prerequisites()
```

This is a conditional **ingestion-call-before-world-body** route. It is not proof that the currently played rider uses that batch, that the batch is its only update route, or that any input value is newly committed. Snow still reads the action store again within each eligible substep. Even after player membership is established, a producer could modify the vector between those two reads unless a separate publication/synchronization guarantee is proved.

Historical next step, superseded by the live correction below: inspect the `PreBeforeSimulation` receiver list and its insertion/removal path. Verify its selected-player entry, callback identity, active prerequisite topology and request association. Then investigate the action writer; no additional generic scheduler reconstruction is needed to identify this candidate ordering.

Verification in this follow-up compared **2,536 exported instruction byte spans across eight existing exports**, plus four concrete callback/service/player table bindings, against the analyzed image. Its SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. The two job names were read from the referenced image strings. This is byte consistency and static control-flow evidence, not execution proof or an independent verification of every previously established prerequisite-release instruction.

The release gate for claiming this player's ingestion precedes a world request is now concrete: establish membership in this particular candidate batch, validate its player method and actor gates, and associate the active dependency holds with that world request. The separate release gate for **sample freshness** is unchanged.

**Live correction (membership):** a guarded live observation found the `PreBeforeSimulation` source (registry entry 24) empty and its storage never allocated. The selected player's actor, by exact pointer, is instead a receiver of the **successor** batch `Physic::BeforeSimulation` (entry 25). That batch installs the same slot-`0x270` thunk, and for the actor that slot is the player update reaching ingestion. The conditional ordering above therefore runs through `BeforeSimulation -> PhysicsWorldStep`. See [motion membership observation](MOTION_MEMBERSHIP_OBSERVATION.md). The subsequent entry/exit study in that document established request association and outer callback order for 701 standing-state requests. Execution of the inner ingestion call, live actor gates and sample freshness remain open.

## Writer freshness follow-up: constructor setup is not sample publication

A bounded follow-up traced the concrete input-manager constructor's final direct setup call. The constructor initializes the context array to inline storage and sets its context count to zero. Its final setup helper is a complete, call-free leaf: it fills an integer table with sentinel patterns and specific integer mappings inside the manager. It does not dereference an action object, populate the context list, copy a four-lane action vector or publish a sample generation. Calling it the missing input commit routine would therefore be unsupported. The mapping's complete semantic labels were not recovered in this pass.

This was a direct read of the analyzed image beginning at an already established constructor call target, ending at the leaf's return after 136 decoded instructions. No game code was executed. The constructor's earlier callback binding still identifies the vector getter, but constructor completion does not create the action payload read later.

The exact remaining boundary is now **later context/binding population**: the getter chooses a context, traverses its registered bindings, asks the tagged map for an action-ID value slot, then dereferences that slot to obtain the action object. That value supplies data, not an unresolved executable callback. The available constructor route does not identify who allocated or inserted that action object. The next meaningful closure must follow a concrete context/binding insertion or action-value allocation path and its writes; enumerating arbitrary calls from the getter or treating the manager's integer mapping table as action-vector storage would not resolve freshness.
