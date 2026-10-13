# AI provider entry and terminal chains

The two external provider pairs in [the root-to-Step route](ENGINE_ROOT_STEP_ROUTE.md) now have concrete interiors. Both come from one allocated provider object. Its first wrapper contains the AI global update graph; its second contains the AI after-update graph. The connection is established by the singleton writer, constructor, installed virtual table, four getters and explicit successor registrations. Labels corroborate those joins.

This closes the missing structural entry-to-terminal paths. It does not establish that every AI callback terminates, nor that an entire original-game request can be advanced safely from an arbitrary suspension point.

## One receiver owns both pairs

The singleton initializer allocates a provider, constructs it, stores the returned receiver in the same global slot read by Step, then invokes three virtual configuration methods on that receiver. Construction creates two wrappers and several inline worker jobs before installing the graph.

The getters have these exact relationships:

```text
provider.first_entry():
    return provider.global_update_wrapper.allocated_entry
provider.first_terminal():
    return address_of(provider.global_update_wrapper.inline_terminal)
provider.second_entry():
    return provider.after_update_wrapper.allocated_entry
provider.second_terminal():
    return address_of(provider.after_update_wrapper.inline_terminal)
```

The wrapper constructor allocates an ordinary graph node as its entry and embeds another as its terminal. These are not conditional-entry wrappers. Their installed table selects the immediate graph-node begin method documented in [the scheduler rearm audit](SCHEDULER_REARM.md), while their registration and activation methods use the ordinary outgoing dependency list. No implicit entry-to-terminal connection is manufactured by the wrapper constructor.

## First wrapper has several terminal predecessors

The setup routine registers the following graph. Names matching job labels are retained. `CallbackList0` and `CallbackList1` describe two inline jobs whose separate callbacks remain data supplied.

```text
register(GlobalBegin, GlobalUpdateSetup)

register(GlobalUpdateSetup, GlobalUpdateStep1)
register(GlobalUpdateStep1, GlobalUpdateStep2)
register(GlobalUpdateStep2, GlobalUpdateStep3)
register(GlobalUpdateStep3, CoordinatorMultiThreaded)
register(CoordinatorMultiThreaded, CoordinatorSingleThreaded)
register(CoordinatorSingleThreaded, GlobalEnd)

register(GlobalUpdateSetup, CallbackList0)
register(CallbackList0, CallbackList1)
register(CallbackList1, GlobalEnd)

if provider.perception_present_at_setup:
    register(GlobalUpdateSetup, PerceptionManager)
    register(PerceptionManager, GlobalEnd)
else:
    register(GlobalUpdateSetup, GlobalEnd)
```

The callback-list branch is not inferred from adjacent object storage. A helper called with index zero registers Setup to the first job, then a second helper called with index one registers the first job to the second and the second to the supplied terminal. These helpers also install each list's callback hooks, worker context and labels.

`GlobalEnd` is a join. A direct Setup-to-End edge does not mean that the long AI chain can be ignored: its other incoming holds still have to be released. Likewise, reaching CoordinatorSingleThreaded alone does not account for the callback-list branch.

### The perception gate is evaluated during graph setup

There is a consequential ordering detail:

```text
construct_provider():
    provider.perception_present = false
    construct_jobs()
    install_graph(provider)

install_graph(provider):
    # Register the graph above using the CURRENT flag.
    if provider.perception_present:
        register_perception_branch()
    else:
        register_direct_setup_to_end()

    candidate = query_perception_callable()
    if callable_is_available(candidate):
        PerceptionManager.callback = candidate
        provider.perception_present = true
```

On the observed fresh-construction path, the flag is false when the edges are selected. A later successful callable query sets the flag after that selection; it does not insert perception edges at that point. The inspected setup has no second graph-repair call after setting it.

A bounded direct-call search found setup called by this constructor. That does not exclude an indirect later call or another graph mutator. The claim is the fresh-construction ordering, not that perception never runs in the game. A reconstruction must not turn this setup-time branch into a per-frame predicate without new evidence.

## Second wrapper has one worker between its endpoints

```text
register(AfterUpdateBegin, CoordinatorManagerUpdate)
register(CoordinatorManagerUpdate, AfterUpdateEnd)
```

The manager-update job installs an ordinary callable whose receiver is a separate global manager. Its target is a short forwarding stub:

```text
coordinator_manager_update(manager):
    return manager.virtual_update_method()
```

The stub dispatches through the manager's virtual table. This pass does not assign the concrete manager method's work or termination policy. It does establish that completion returns through the ordinary callable job; the terminal is not an unrelated signal guessed from its label.

## Release behavior and callback boundaries

The installed tables were checked at construction:

| Job family | Begin behavior | Successor behavior |
| --- | --- | --- |
| Both allocated entries and inline terminals | Immediate graph-node begin | Ordinary dependency registration, activation and release |
| Setup, optional perception and manager update | Ordinary queued-job begin | Ordinary dependency registration, activation and release |
| AI stages, coordinator lists and callback lists | Ordinary queued-job begin with their concrete worker routines | Ordinary dependency registration, activation and release |

The callable worker checks optional before and after hooks, invokes its main callable, then returns through the scheduler execution wrapper. The list jobs use a signed remaining-count predicate: empty when remaining is nonpositive. As in [the batch-epoch audit](SCHEDULER_BATCH_EPOCH.md), that predicate alone does not establish that claimed callbacks have returned. Worker execution accounting supplies the separate completion boundary.

The provider tables use the same ordinary begin and finalization routes inspected in [the rearm audit](SCHEDULER_REARM.md). There is no additional conditional-list selection in the two provider wrappers. Selected callback bodies, list contents and callback availability are still independent dependencies.

Combining this graph with Step's registered edges yields:

```text
preceding_world_stage
    -> GlobalBegin -> AI graph and its joins -> GlobalEnd
    -> intervening_engine_and_world_stages
    -> AfterUpdateBegin -> CoordinatorManagerUpdate -> AfterUpdateEnd
    -> following_world_stage -> action_stage
```

This is a recovered dependency route with concrete intervening jobs. Normal scheduler completion can release it when the workers return and their holds are satisfied. It is not a claim that submitting the root always executes player physics, because the earlier engine-mode and later world-action gates still apply.

## Remaining questions

- Resolve the manager virtual update target if its side effects or failure behavior are needed for a modding boundary.
- Determine whether any later mutation reconnects the optional perception job after initial construction.
- Decode the callback-list population and AI receiver sets before treating this graph as an empty or constant-cost bridge.
- Preserve engine request completion and ownership rules. Concrete provider paths do not make an arbitrary stopped worker a safe graph-edit point.

## Evidence

The analyzed image SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Hashes below cover complete exception-directory fragments in address order:

| Routine | Bytes | SHA-256 |
| --- | ---: | --- |
| Provider singleton initialization | 280 | `459809e8e914f0281ac98553ea08a89b412dcef1f2d807cbe0bd5e014b8809ec` |
| Concrete provider construction | 1028 | `1579999ddb65dd736d9f7f8abb54ca263cd96bd8129f73bf2d8278739f522ad5` |
| Provider graph setup | 1388 | `bbdcf75dc45a933bfab0ec0d4ffaea58e6888501139d2188bd324508ca73df8b` |
| First callback-list configuration | 499 | `bd36b4257720a27bdce31d24fb5397015647adb4e57b84efc1d8d391e629fe0a` |
| Second callback-list configuration | 286 | `1670e053e0059b154bef722b0564d835ed4921b9a010761c4bb6375dea15156a` |
| Ordinary entry/terminal wrapper construction | 213 | `3d7a7f3d18ebc39fe3183f3ab6249b28b029f9f48d9c0813dd89a483cbbb3e7a` |

The singleton references were found as decoded instruction-relative loads and stores, then traced to the actual constructor and getter table. Getter leaves and the manager forwarding stub have no exception-directory entry and were decoded separately from their installed targets. No game was launched or attached to, and no original payload or raw export is included here.
