/* Example Snow host plugin: reads the bound player's body while the simulation is held.
 *
 * On pause it records the position; after each released world step it logs how far the
 * player has moved since the pause and the current speed. After resume it checks that
 * get_player is refused (the simulation is running again).
 *
 * Build: x86_64-w64-mingw32-gcc -O2 -shared -I.. -o player_logger.dll player_logger.c
 * Requires host 0.3+ (get_player); with an older host it declines to load.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include "snow_plugin.h"

static const SnowHostApiV1 *host;
static float origin[3];
static int have_origin;

static void logf_(const char *fmt, ...) {
    char line[256];
    va_list ap; va_start(ap, fmt);
    vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    host->log(host->context, line);
}

static int read_player(SnowPlayerStateV1 *p) {
    p->struct_size = sizeof *p;
    return host->get_player(host->context, p);
}

static int on_pause(void *user) {
    (void)user;
    SnowPlayerStateV1 p;
    int rc = read_player(&p);
    have_origin = rc == SNOW_OK;
    if (rc) { logf_("paused; no player (%d)", rc); return 0; }
    for (int k = 0; k < 3; k++) origin[k] = p.position[k];
    logf_("paused; player %llu at (%.2f, %.2f, %.2f)", (unsigned long long)p.identity,
          p.position[0], p.position[1], p.position[2]);
    return 0;
}

static int on_step(void *user, const SnowStepInfoV1 *step) {
    (void)user;
    SnowPlayerStateV1 p;
    int rc = read_player(&p);
    if (rc) { logf_("step %llu: no player (%d)", step->steps_released, rc); return 0; }
    const float *v = p.linear_velocity;
    float speed = sqrtf(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    if (have_origin)
        logf_("step %llu: moved (%.2f, %.2f, %.2f) since pause, speed %.2f", step->steps_released,
              p.position[0] - origin[0], p.position[1] - origin[1], p.position[2] - origin[2], speed);
    return 0;
}

static int on_resume(void *user, SnowResumeReason reason) {
    (void)user; (void)reason;
    SnowPlayerStateV1 p;
    logf_("resumed; get_player now returns %d", read_player(&p));
    return 0;
}

__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api, SnowPluginV1 *plugin) {
    if (api->api_version != SNOW_PLUGIN_API_VERSION ||
        api->struct_size < offsetof(SnowHostApiV1, get_player) + sizeof api->get_player || !api->get_player)
        return 1;
    host = api;
    plugin->struct_size = sizeof *plugin;
    plugin->api_version = SNOW_PLUGIN_API_VERSION;
    plugin->name = "player_logger";
    plugin->version = "1.0";
    plugin->on_pause = on_pause;
    plugin->on_step = on_step;
    plugin->on_resume = on_resume;
    return 0;
}
