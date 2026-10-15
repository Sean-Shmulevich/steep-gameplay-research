/* Snow mod host plugin API, version 1.
 *
 * A plugin is a DLL in the `plugins` folder next to snow_host.dll that exports
 *
 *     int SnowMod_Initialize(const SnowHostApiV1 *host, SnowPluginV1 *plugin);
 *
 * The host passes a zeroed `plugin`. Initialize fills it and returns 0, or
 * returns nonzero to decline loading. It must set api_version to
 * SNOW_PLUGIN_API_VERSION and struct_size to sizeof(SnowPluginV1).
 *
 * Threading and timing:
 * - Every call into a plugin (Initialize and all callbacks) runs on the host's
 *   plugin thread, one call at a time. Plugins need no locking against the host.
 * - on_step runs after the host has released exactly one world Step and
 *   re-armed the hold, so the world simulation is held while it runs.
 *   Rendering continues meanwhile.
 * - Each call has a time budget (SNOW_PLUGIN_CALL_BUDGET_MS). A call that
 *   exceeds it, crashes (access violation, illegal instruction, divide by zero,
 *   stack overflow), or returns nonzero disables that plugin for the rest of
 *   the session. The host keeps running and other plugins are unaffected.
 *   A plugin disabled by a nonzero return gets on_unload and is unloaded.
 *   A crashed or timed-out plugin is never unloaded, because its code may
 *   still be on a stack.
 * - Containment is best-effort: a plugin that faults while holding a lock it
 *   shares with the game (for example the process heap) can still hang the game.
 * - Plugin DllMain runs under the loader lock and is not contained; keep it trivial.
 *
 * Callbacks must not call back into the command channel, and must not block on
 * the game. They receive the plugin's own `user` pointer.
 */
#ifndef SNOW_PLUGIN_H
#define SNOW_PLUGIN_H
#include <stdint.h>

#define SNOW_PLUGIN_API_VERSION 1
#define SNOW_PLUGIN_CALL_BUDGET_MS 250

#ifdef __cplusplus
extern "C" {
#endif

typedef struct SnowHostStateV1 {
    uint32_t struct_size;
    uint32_t host_paused;      /* 1 while the host holds a pause */
    uint64_t steps_released;   /* world steps released by this host since start */
} SnowHostStateV1;

typedef struct SnowStepInfoV1 {
    uint32_t struct_size;
    uint32_t index_in_batch;   /* 0-based position within one step_world request */
    uint32_t batch_size;       /* steps requested by that request */
    uint32_t reserved;
    uint64_t steps_released;   /* host-wide count, including this step */
    double release_ms;         /* time from release to Step starting */
} SnowStepInfoV1;

/* Selected player's physical body, read while the simulation is held (host 0.3+).
 * Units are the engine's world units (not calibrated to metres); velocities are per second
 * as stored by the engine. The position is the body origin, not necessarily the visible board
 * centre. `identity` is opaque and changes whenever the host binds a different player. */
/* SnowPlayerStateV1.flags (host 0.6+; zero from older hosts).
 * When SNOW_PLAYER_IN_WORLD is clear, the main body is not part of a physics world and is not being
 * simulated: its values are stale. Observed live after a crash and during respawn staging, while the actor
 * stayed the same (no player event). The setters refuse in that state. */
#define SNOW_PLAYER_FLAGS_VALID 0x1u     /* the adapter filled the bits below */
#define SNOW_PLAYER_IN_WORLD 0x2u        /* the main body belongs to a physics world (is being simulated) */

typedef struct SnowPlayerStateV1 {
    uint32_t struct_size;
    uint32_t flags;                /* SNOW_PLAYER_* above (was reserved) */
    uint64_t identity;
    float position[3];
    float axes[3][3];              /* orientation: the body's three basis vectors in world space */
    float linear_velocity[3];
    float angular_velocity[3];
} SnowPlayerStateV1;

/* get_player results. */
#define SNOW_OK 0
#define SNOW_E_BAD_ARGS 1          /* null pointer or struct_size too small */
#define SNOW_E_NOT_HELD 2          /* only callable while the host holds the simulation (on_pause, on_step) */
#define SNOW_E_NO_PLAYER 3         /* no player bound, or unsupported by this adapter */
#define SNOW_E_PLAYER_CHANGED 4    /* the bound player's identity checks failed; the binding was dropped */
#define SNOW_E_REFUSED 5           /* value rejected (non-finite or above the host's limit) or unsupported */

/* Largest velocity magnitude set_player_velocity accepts, in world units per second. */
#define SNOW_MAX_SET_SPEED 300.0f
/* Largest distance set_player_pose may move the player in one call, in world units. Larger moves risk
 * placing the player where the world is not loaded. */
#define SNOW_MAX_TELEPORT_DISTANCE 100.0f

/* Player binding events (host 0.6+). The host re-checks the bound player against the engine's live
 * registries about every 250 ms and before every setter. When the player disappears or is replaced
 * (respawn, sport switch, world change) it reports LOST, drops the binding, and reports ACQUIRED once it
 * has found the new player. */
typedef enum SnowPlayerEventKind {
    SNOW_PLAYER_ACQUIRED = 1,
    SNOW_PLAYER_LOST = 2
} SnowPlayerEventKind;

typedef struct SnowPlayerEventV1 {
    uint32_t struct_size;
    uint32_t kind;                 /* SnowPlayerEventKind */
    uint64_t identity;             /* ACQUIRED: the new identity; LOST: the identity that is gone */
    uint32_t world_changed;        /* ACQUIRED: 1 if the new player is in a different world than the previous one */
    uint32_t reserved;
} SnowPlayerEventV1;

typedef enum SnowResumeReason {
    SNOW_RESUME_REQUESTED = 0,     /* simulation.resume */
    SNOW_RESUME_LEASE_EXPIRED = 1,
    SNOW_RESUME_CLIENT_DISCONNECTED = 2
} SnowResumeReason;

typedef struct SnowHostApiV1 {
    uint32_t struct_size;
    uint32_t api_version;          /* SNOW_PLUGIN_API_VERSION */
    const char *host_version;
    void *context;                 /* per-plugin; pass back unchanged */
    /* Append one line to snow_host.log, tagged with the plugin name. */
    void (*log)(void *context, const char *message);
    /* UTF-8 path of plugins\<plugin file name without .dll>.ini. The file may not exist. */
    const char *config_path;
    /* Snapshot of host state. Returns 0 on success. */
    int (*get_state)(void *context, SnowHostStateV1 *out);
    /* Host 0.3+ (check struct_size >= offsetof(SnowHostApiV1, get_player) + sizeof(void *)).
     * Fills *out (set out->struct_size first) and returns SNOW_OK or a SNOW_E_* code. */
    int (*get_player)(void *context, SnowPlayerStateV1 *out);
    /* Host 0.4+ (check struct_size as above). Sets the bound player's linear velocity through the
     * engine's own velocity assignment, which also zeroes angular velocity and resets the player's
     * speed history. Only while the simulation is held; takes effect on the next released step.
     * Returns SNOW_OK or a SNOW_E_* code. */
    int (*set_player_velocity)(void *context, const float velocity[3]);
    /* Host 0.5+ (check struct_size as above). Places the bound player through the engine's own placement
     * routine: position, axes (orthonormal), linear and angular velocity are taken from *target
     * (struct_size must be set; identity is ignored). Typical use: get_player, edit, set_player_pose.
     * Only while held; moves of at most SNOW_MAX_TELEPORT_DISTANCE. Returns SNOW_OK or SNOW_E_*. */
    int (*set_player_pose)(void *context, const SnowPlayerStateV1 *target);
} SnowHostApiV1;

typedef struct SnowPluginV1 {
    uint32_t struct_size;          /* sizeof(SnowPluginV1) */
    uint32_t api_version;          /* SNOW_PLUGIN_API_VERSION */
    const char *name;              /* short, stable identifier; required */
    const char *version;           /* free-form; optional */
    void *user;
    /* All callbacks are optional. Return 0, or nonzero to disable the plugin. */
    int (*on_pause)(void *user);
    int (*on_step)(void *user, const SnowStepInfoV1 *step);
    int (*on_resume)(void *user, SnowResumeReason reason);
    void (*on_unload)(void *user);
    /* Host 0.6+, optional; plugins built against older headers simply leave it out. Runs on the plugin
     * thread like every callback, but the simulation may be running, so get_player and the setters may
     * refuse. Return 0, or nonzero to disable the plugin. */
    int (*on_player)(void *user, const SnowPlayerEventV1 *event);
} SnowPluginV1;

typedef int (*SnowModInitializeFn)(const SnowHostApiV1 *host, SnowPluginV1 *plugin);

#ifdef __cplusplus
}
#endif
#endif
