/* Snow mod host: physics safe-point extension. PROPOSED, NOT IMPLEMENTED.
 *
 * This header is a design sketch for docs/reconstruction/PHYSICS_SAFE_POINT_CONTRACT.md. No host
 * build provides these functions, and no host exports them. Every name, value and limit
 * may change. Clause numbers (T8, C3, ...) refer to that contract.
 *
 * Model:
 * - Plugin code runs only on the host plugin thread (contract T1, T8), exactly as in snow_plugin.h.
 *   The new callback on_physics_safe_point runs at a Step-hold (on_pause / after on_step), while
 *   the world is held.
 * - Reads are copies made by the host into caller buffers. Plugins never receive engine pointers.
 *   Bodies and pairs are opaque handles that the host re-checks on every use. Handles are valid only
 *   inside the session and binding that produced them.
 * - Mutations are declarative requests. A plugin queues them during a safe-point call; the host
 *   applies them at the next released step, at the first in-step pair-update point S0, on the engine's
 *   stepping thread, using host-owned code only. The engine's own routines then make the change.
 *   The outcome is reported at the next safe-point call.
 * - Nothing here takes or releases an engine lock. Guard checks are reads, not exclusion (C3).
 *
 * Discovery (proposed): appended to SnowHostApiV1 after set_player_pose as
 *     int (*get_physics_api)(void *context, uint32_t version, const SnowPhysicsApiV1 **out);
 * and to SnowPluginV1 after on_player as
 *     int (*on_physics_safe_point)(void *user, const SnowPhysicsApiV1 *api,
 *                                  const SnowSafePointInfoV1 *info);
 * Plugins check struct_size before using either, as with get_player.
 */
#ifndef SNOW_PHYSICS_SAFE_POINT_H
#define SNOW_PHYSICS_SAFE_POINT_H
#include <stdint.h>
#include "snow_plugin.h"

#define SNOW_PHYSICS_API_PROPOSED 1          /* marker: this API does not exist yet */
#define SNOW_PHYSICS_API_VERSION 1

/* Host limits (AUTHORED POLICY, contract B6, C3, failure table). */
#define SNOW_PHYS_MAX_ROWS 64                /* largest row copy per call */
#define SNOW_PHYS_MAX_REQUESTS_PER_STEP 1    /* T3: one physics request per released step */
#define SNOW_PHYS_INSTEP_BUDGET_US 50        /* host-side work at S0..S2, not plugin time */
#define SNOW_PHYS_GUARD_DEFER_LIMIT 8        /* substeps to wait for free guards before dropping */

#ifdef __cplusplus
extern "C" {
#endif

/* Additional result codes, continuing the SNOW_* codes in snow_plugin.h. */
#define SNOW_E_NOT_AT_SAFE_POINT 6   /* called outside on_physics_safe_point */
#define SNOW_E_TORN 7                /* entry/exit snapshot differed, or S1/S2 was missed */
#define SNOW_E_GUARD_HELD 8          /* a pool guard read as held for the whole defer window */
#define SNOW_E_IDENTITY 9            /* image, vtable, controller or broadphase identity check failed */
#define SNOW_E_STALE_HANDLE 10       /* body or pair handle no longer matches live state */
#define SNOW_E_LOADING 11            /* loading or body lifecycle in flight (contract C8, PENDING) */
#define SNOW_E_BUSY 12               /* request queue full for this step */
#define SNOW_E_UNSAFE_ENV 13         /* dispatcher capacity != 1 or another unobserved configuration (C7) */

/* Safe-point kinds. Only STEP_HOLD reaches plugins (T8). The in-step kinds are listed so outcomes
 * can name where they were applied. */
typedef enum SnowSafePointKind {
    SNOW_SAFE_POINT_STEP_HOLD = 1,      /* candidate A: world held, plugin thread */
    SNOW_SAFE_POINT_PAIR_PRE = 2,       /* candidate B, S0: host code only, stepping thread */
    SNOW_SAFE_POINT_PAIR_MID = 3,       /* candidate B, S1 */
    SNOW_SAFE_POINT_PAIR_POST = 4       /* candidate B, S2 */
} SnowSafePointKind;

/* Opaque handles. The fields are for host bookkeeping; plugins compare them for equality only. */
typedef struct SnowPhysBody { uint64_t identity; uint64_t generation; } SnowPhysBody;
typedef struct SnowPhysPairKey { uint64_t value; } SnowPhysPairKey;   /* engine pair key, session-local */

typedef struct SnowSafePointInfoV1 {
    uint32_t struct_size;
    uint32_t kind;                 /* SnowSafePointKind; always STEP_HOLD for plugin calls */
    uint64_t token;                /* changes at every safe point; requests are bound to it */
    uint64_t world_identity;       /* opaque; changes when the bound player's world changes */
    uint64_t steps_released;       /* same count as SnowHostStateV1 */
    uint32_t flags;                /* SNOW_SAFE_POINT_F_* */
    uint32_t reserved;
} SnowSafePointInfoV1;

#define SNOW_SAFE_POINT_F_PAIR_STATE_FROZEN 0x1u  /* set only once contract slot P1 is ESTABLISHED */
#define SNOW_SAFE_POINT_F_GUARDS_FREE 0x2u        /* every live-sampled guard read free at entry */
#define SNOW_SAFE_POINT_F_IN_WORLD 0x4u           /* SNOW_PLAYER_IN_WORLD at entry */
#define SNOW_SAFE_POINT_F_NO_LOADING 0x8u         /* set only once contract slot P3 supplies a predicate */

/* Which broadphase list a copy reads. */
typedef enum SnowPairList {
    SNOW_PAIR_LIST_OVERLAPPING = 1,   /* every currently overlapping pair (B.vt+0x40/+0x48) */
    SNOW_PAIR_LIST_REMOVED = 2        /* pairs reported removed this substep (B.vt+0x60/+0x68) */
} SnowPairList;

typedef struct SnowPairRowV1 {
    SnowPhysBody a;
    SnowPhysBody b;
    SnowPhysPairKey key;
} SnowPairRowV1;

#define SNOW_LINK_PRESENT 0x1u        /* the provider link tree has a link for the key */
#define SNOW_LINK_ENABLED 0x2u        /* link flag bit0 */
#define SNOW_LINK_FILTER_REJECTED 0x4u /* link flag bit1 */

typedef struct SnowLinkInfoV1 {
    uint32_t struct_size;
    uint32_t flags;               /* SNOW_LINK_* */
    SnowPhysBody a;
    SnowPhysBody b;
} SnowLinkInfoV1;

/* Guard snapshot: a read of one pool guard's CRITICAL_SECTION-shaped pointee. Not exclusion. */
typedef struct SnowGuardStateV1 {
    uint32_t struct_size;
    uint32_t index;               /* 0..10, host order; no address is exposed */
    int32_t lock_count;           /* -1 when free */
    uint32_t owner_nonzero;       /* 1 if OwningThread != 0 */
} SnowGuardStateV1;

/* Declarative requests. */
typedef enum SnowPhysRequestKind {
    SNOW_PHYS_RETIRE_PAIR_LINK = 1    /* T3: retire one link for one substep through select/rebuild/retire */
    /* SUPPRESS_PAIR and body filter changes are deliberately absent (contract 5.2, O5). */
} SnowPhysRequestKind;

typedef struct SnowPhysRequestV1 {
    uint32_t struct_size;
    uint32_t kind;                /* SnowPhysRequestKind */
    SnowPhysPairKey key;
    SnowPhysBody a;               /* must match the key's current row (C5) */
    SnowPhysBody b;
} SnowPhysRequestV1;

typedef enum SnowPhysOutcome {
    SNOW_PHYS_PENDING = 0,        /* not yet applied (no release since it was queued) */
    SNOW_PHYS_SELECTED = 1,       /* engine selected and retired the link */
    SNOW_PHYS_NOT_SELECTED = 2,   /* row reached select but did not pass the engine's gate */
    SNOW_PHYS_NO_LINK = 3,        /* no link existed for the key at S0 */
    SNOW_PHYS_DROPPED = 4         /* refused or abandoned; see error */
} SnowPhysOutcome;

typedef struct SnowPhysResultV1 {
    uint32_t struct_size;
    uint32_t outcome;             /* SnowPhysOutcome */
    uint32_t error;               /* SNOW_OK or SNOW_E_* when DROPPED */
    uint32_t applied_at;          /* SnowSafePointKind where it was applied, 0 if never */
    uint64_t request_id;
    uint32_t link_reused;         /* 1 if the retired link was reused for the same pair in that step */
    uint32_t reserved;
} SnowPhysResultV1;

typedef struct SnowPhysicsApiV1 {
    uint32_t struct_size;
    uint32_t api_version;         /* SNOW_PHYSICS_API_VERSION */
    /* `context` is SnowHostApiV1.context, passed back unchanged. */
    /* Reads. Only inside on_physics_safe_point; otherwise SNOW_E_NOT_AT_SAFE_POINT.
     * *count is in/out: buffer capacity in, rows written out. */
    int (*copy_pairs)(void *context, uint32_t list, SnowPairRowV1 *rows, uint32_t *count, uint32_t *total);
    int (*get_link)(void *context, SnowPhysPairKey key, SnowLinkInfoV1 *out);
    int (*get_player_body)(void *context, SnowPhysBody *main_body, SnowPhysBody *rider_body);
    int (*get_guards)(void *context, SnowGuardStateV1 *out, uint32_t *count);
    /* Mutation. Validates now (C3-C8 as far as checkable while held) and queues. Returns SNOW_OK with
     * *request_id, or SNOW_E_*. The request is discarded with SNOW_E_TORN if this safe point tears. */
    int (*queue_request)(void *context, const SnowPhysRequestV1 *request, uint64_t *request_id);
    /* Outcome of an earlier request. Available from the next safe point after the release. */
    int (*get_result)(void *context, uint64_t request_id, SnowPhysResultV1 *out);
} SnowPhysicsApiV1;

typedef int (*SnowGetPhysicsApiFn)(void *context, uint32_t version, const SnowPhysicsApiV1 **out);
typedef int (*SnowOnPhysicsSafePointFn)(void *user, const SnowPhysicsApiV1 *api, const SnowSafePointInfoV1 *info);

#ifdef __cplusplus
}
#endif
#endif
