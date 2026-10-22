/* Game adapter boundary for the Snow mod host.
 *
 * The host core never contains game addresses. A build links exactly one
 * adapter: the build-specific game adapter or the simulated fixture
 * adapter. Every adapter call happens on the host executor thread.
 */
#ifndef SNOW_ADAPTER_H
#define SNOW_ADAPTER_H
#include <stddef.h>
#include <stdint.h>

/* Mode group bytes in memory order: neighbor, mode, companion, request_arg. */
#define SNOW_GROUP_BYTE(g, i) (((g) >> (8 * (i))) & 0xffu)
#define SNOW_GROUP_HELD(g) (SNOW_GROUP_BYTE(g, 1) == 1 && SNOW_GROUP_BYTE(g, 2) == 1)
#define SNOW_GROUP_ORDINARY(g) (SNOW_GROUP_BYTE(g, 1) == 0 && SNOW_GROUP_BYTE(g, 2) == 0)

typedef struct SnowCounters {
    uint64_t owner;      /* opaque identity of the current engine owner; never an API field */
    uint32_t group;      /* stop-mode group */
    uint32_t step;       /* world Step job, last-run request */
    uint32_t paused;     /* UpdateWhileEngineIsPaused job, last-run request */
    uint32_t end_frame;  /* EndFrame job, last-run request */
} SnowCounters;

/* Raw body state for the bound player. */
typedef struct SnowPlayerRaw {
    float transform[16];           /* four 16-byte columns: three basis vectors, then translation */
    float linear_velocity[3];
    float angular_velocity[3];
    uint32_t flags;                /* SNOW_PLAYER_* flags from snow_plugin.h, or 0 */
} SnowPlayerRaw;

/* One bounded, address-free channel observation. Not an atomic pose snapshot. */
typedef struct SnowAnimationChannelRaw {
    uint32_t found, guards_matched, epoch;
    float vector[4], rotation[4]; /* local provider record; coordinate semantics unresolved */
    float parent_vector[4], parent_rotation[4];
    float provider_vector[4], provider_rotation[4]; /* recovered conversion, not claimed world space */
    uint32_t record_index, bank_flags;
    float owner_matrix[16]; /* stored owner matrix, no freshness/space claim */
    uint32_t owner_accessor_present, owner_reader_word;
} SnowAnimationChannelRaw;

typedef struct SnowCachedParentRaw {
    float cached[8], primary[8], current[8];
    uint32_t guards_matched, primary_present, current_present, banks_alias;
    uint32_t storage_nonempty, context_tag, context_nonzero, function_present;
    uint32_t holder_present, target_present, status_sign, eligible;
} SnowCachedParentRaw;

typedef struct SnowAdapter {
    const char *name;
    /* Verify process/image identity; retryable during startup. Returns 0 or a reason. */
    int (*bind)(char *why, size_t n);
    /* Fresh owner lookup and counter read. Returns 0 or writes a reason. */
    int (*read)(SnowCounters *c, char *why, size_t n);
    /* Atomic compare-and-swap of the mode group only. *seen receives the prior value. */
    int (*cas_group)(uint64_t owner, uint32_t expect, uint32_t want, uint32_t *seen);
    /* The engine's own stop-mode setter (request argument 1) and clear routine. */
    int (*enter)(void);
    int (*leave)(void);
    /* Optional (may be NULL). Bind the player named by an opaque handle string supplied by the
     * client from an external acquisition; the adapter validates it. Returns 0 or writes a reason. */
    int (*player_bind)(const char *handle, char *why, size_t n);
    /* Re-validate the bound player's identity chain and read its body. 0 = ok, 1 = no player,
     * 2 = identity changed (the adapter drops the binding). */
    int (*player_read)(SnowPlayerRaw *out, char *why, size_t n);
    /* Optional. Assign the bound player's linear velocity through the engine's own routine. Called
     * only while the simulation is held, with a finite, bounded value. 0 = ok, 1 = refused,
     * 2 = identity changed (binding dropped). */
    int (*player_set_velocity)(const float v[3], char *why, size_t n);
    /* Optional. Find and bind the selected player in-process (no external handle). 0 or a reason.
     * *world_changed is set to 1 when its world differs from the previously bound player's. */
    int (*player_acquire)(int *world_changed, char *why, size_t n);
    /* Optional. Is the bound player still registered with the engine (cheap, read-only)? 0 = yes,
     * 1 = no (the adapter drops its binding). */
    int (*player_check)(char *why, size_t n);
    /* Optional. Place the bound player through the engine's own routine. transform uses the SnowPlayerRaw
     * layout. Called only while held with validated values. 0 = ok, 1 = refused, 2 = identity changed. */
    int (*player_set_pose)(const float transform[16], const float lin[3], const float ang[3], char *why, size_t n);
    /* Optional read-only observation for one uint32 resource key. Revalidate bound player,
     * skeleton ownership and bank endpoints. 0 success, 1 refused, 2 identity lost.
     * A simulation hold does not by itself prove animation completion. */
    int (*animation_channel)(uint32_t key, SnowAnimationChannelRaw *out, char *why, size_t n);
    int (*cached_parent)(SnowCachedParentRaw *out, char *why, size_t n);
} SnowAdapter;

extern const SnowAdapter snow_adapter;
#endif
