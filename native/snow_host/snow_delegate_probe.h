#ifndef SNOW_DELEGATE_PROBE_H
#define SNOW_DELEGATE_PROBE_H
#include "snow_delegate_trace.h"
#include "snow_update_snapshot.h"
#include "snow_motion_observation.h"
#ifdef SNOW_DELEGATE_PROBE_BUILD
#define SNOW_DELEGATE_API __declspec(dllexport)
#else
#define SNOW_DELEGATE_API
#endif
/* Experimental main-delegate record ABI v3. Caller verifies build/code identity and
 * guarantees owner storage remains allocated and unreused during Configure,
 * Install and Restore, and preserves the function/context ABI for cached callers.
 * Guards/CAS do NOT establish these lifetime and binding prerequisites.
 * Configure once; one install attempt; Restore is retryable and conflict-aware.
 * This module and original image are pinned. Never unload/reuse recorder state.
 */
typedef struct {
    uint64_t owner_global, owner, job_table, dispatch_method;
    uint64_t function, auxiliary, context, invoker;
} SnowDelegateBinding;
/* Fixed inspected layouts only; this is not an arbitrary-offset hook API. */
typedef enum { SNOW_DELEGATE_GRAPHICS_MAIN=1, SNOW_DELEGATE_ENGINE_MAIN=2 } SnowDelegateSite;
SNOW_DELEGATE_API int SnowDelegateProbe_ConfigureSite(const SnowDelegateBinding *, SnowDelegateSite);
/* Legacy Configure selects GRAPHICS_MAIN. Record layout/version unchanged. */
SNOW_DELEGATE_API uint32_t SnowDelegateProbe_ABIVersion(void);
SNOW_DELEGATE_API size_t SnowDelegateProbe_RecordSize(void);
SNOW_DELEGATE_API int SnowDelegateProbe_Configure(const SnowDelegateBinding *);
SNOW_DELEGATE_API int SnowDelegateProbe_Install(void);
SNOW_DELEGATE_API int SnowDelegateProbe_Restore(void);
SNOW_DELEGATE_API int SnowDelegateProbe_Close(size_t *,size_t *);
SNOW_DELEGATE_API int SnowDelegateProbe_Read(size_t,void *,size_t);
/* One optional authored observation delivered by the next intercepted delegate.
 * Arm after Configure, before Install; one attempt, never rearm. Does not submit
 * to the native command queue or authorize gameplay mutation. Module/storage
 * remain resident. Read succeeds only after the forwarding invocation returns.
 * Manager samples are sequential read-only pointers, not ownership or snapshots.
 */
typedef struct {
    uint64_t request_id, entry_tick, exit_tick, thread, caller, receiver, storage;
    uint64_t manager_before, manager_after, result;
    uint32_t valid_before, valid_after;
} SnowDelegateRequestObservation;
SNOW_DELEGATE_API int SnowDelegateProbe_ArmObservation(uint64_t request_id);
SNOW_DELEGATE_API int SnowDelegateProbe_ReadObservation(SnowDelegateRequestObservation *);
/* Reusable single-slot observation, authored policy, not native queue semantics.
 * Submit only after successful Install; IDs must strictly increase (no wrap).
 * A pending/running/uncollected request applies backpressure. Collect consumes
 * one returned, cancelled or stale receipt. ReadObservation remains non-consuming and
 * reports returned receipts only. Control calls serialize internally.
 * CloseObservations permanently refuses new requests and cancels one unclaimed
 * request. A callback that already claimed it finishes normally. Restore/Close
 * also close requests. Neither collection nor closure authorizes module unload.
 * Submission can be claimed and returned before SubmitObservation returns.
 */
typedef enum {
    SNOW_OBSERVATION_ACCEPTED=1, SNOW_OBSERVATION_BUSY=2,
    SNOW_OBSERVATION_CLOSED=3, SNOW_OBSERVATION_INVALID=4,
    SNOW_OBSERVATION_STALE_BINDING=5
} SnowObservationAdmission;
typedef enum {
    SNOW_OBSERVATION_NOT_READY=0, SNOW_OBSERVATION_RETURNED=1,
    SNOW_OBSERVATION_CANCELLED=2, SNOW_OBSERVATION_STALE_BEFORE=3,
    SNOW_OBSERVATION_STALE_AFTER=4
} SnowObservationReceipt;
SNOW_DELEGATE_API SnowObservationAdmission SnowDelegateProbe_SubmitObservation(uint64_t);
SNOW_DELEGATE_API SnowObservationReceipt SnowDelegateProbe_CollectObservation(SnowDelegateRequestObservation *);
SNOW_DELEGATE_API void SnowDelegateProbe_CloseObservations(void);
/* Claimed observations recheck owner/descriptor and actual call arguments before
 * and after forwarding. A mismatch suppresses the manager read at that boundary,
 * latches request admission closed and yields STALE_BEFORE or STALE_AFTER.
 * The original callback is always forwarded: these statuses describe observation
 * qualification, not cancellation of native work. Before failure takes precedence.
 * Restored original invoker is allowed for an already claimed/cached call.
 * Sequential identity checks cannot detect an intervening change-and-restore,
 * retain owner storage, or make a freed receiver safe for original forwarding.
 */
/* Optional read-only physics channel. Configure once before arming/installing,
 * from a freshly acquired actor and externally verified build profile. No actor
 * discovery or ownership pin. World/counter binding stays fixed for this session;
 * body links refresh per sample. Invalid samples are zero, independent of delegate
 * return status. Counters identify the physics job, not this engine request.
 */
typedef struct {
    uint64_t request_id;
    uint32_t configured;
    SnowUpdateSnapshot before,after;
} SnowDelegatePhysicsObservation;
SNOW_DELEGATE_API int SnowDelegateProbe_ConfigurePhysics(uint64_t actor,const SnowUpdateProfile *);
/* Atomic collection of the request receipt and its associated physics samples.
 * Both outputs required; non-consuming primary ReadObservation is unchanged. */
SNOW_DELEGATE_API SnowObservationReceipt SnowDelegateProbe_CollectPhysics(
    SnowDelegateRequestObservation *,SnowDelegatePhysicsObservation *);
/* Optional motion observations share receipt publication, not an atomic memory
 * snapshot with physics. Enable after ConfigurePhysics and before any request. */
typedef struct {
    uint64_t request_id;
    uint32_t configured,valid_before,valid_after;
    SnowMotionObservation before,after;
} SnowDelegateMotionObservation;
SNOW_DELEGATE_API int SnowDelegateProbe_EnableMotion(void);
/* All three outputs required. Legacy collectors remain ABI-compatible. */
SNOW_DELEGATE_API SnowObservationReceipt SnowDelegateProbe_CollectState(
    SnowDelegateRequestObservation *,SnowDelegatePhysicsObservation *,SnowDelegateMotionObservation *);
#endif
