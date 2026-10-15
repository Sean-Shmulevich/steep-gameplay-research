/* Example Snow host plugin: logs pause/resume and every 10th released world step.
 *
 * Build: x86_64-w64-mingw32-gcc -O2 -shared -I.. -o step_logger.dll step_logger.c
 * Install: copy step_logger.dll into the plugins folder next to snow_host.dll.
 * Optional config (plugins\step_logger.ini):  [step_logger]  every=10
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "snow_plugin.h"

static const SnowHostApiV1 *host;
static unsigned every = 10;
static unsigned long long seen;

static void logf_(const char *fmt, ...) {
    char line[256];
    va_list ap; va_start(ap, fmt);
    vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    host->log(host->context, line);
}

static int on_pause(void *user) {
    (void)user;
    logf_("paused");
    return 0;
}

static int on_step(void *user, const SnowStepInfoV1 *step) {
    (void)user;
    seen++;
    if (step->steps_released % every == 0)
        logf_("step %llu (batch %u/%u, release %.2f ms)", step->steps_released,
              step->index_in_batch + 1, step->batch_size, step->release_ms);
    return 0;
}

static int on_resume(void *user, SnowResumeReason reason) {
    (void)user;
    SnowHostStateV1 st = {sizeof st, 0, 0};
    host->get_state(host->context, &st);
    logf_("resumed (reason %d); saw %llu steps, host total %llu", (int)reason, seen, st.steps_released);
    return 0;
}

__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api, SnowPluginV1 *plugin) {
    if (api->api_version != SNOW_PLUGIN_API_VERSION || api->struct_size < sizeof *api) return 1;
    host = api;
    WCHAR path[MAX_PATH];
    if (MultiByteToWideChar(CP_UTF8, 0, api->config_path, -1, path, MAX_PATH)) {
        UINT v = GetPrivateProfileIntW(L"step_logger", L"every", 10, path);
        if (v >= 1 && v <= 100000) every = v;
    }
    plugin->struct_size = sizeof *plugin;
    plugin->api_version = SNOW_PLUGIN_API_VERSION;
    plugin->name = "step_logger";
    plugin->version = "1.0";
    plugin->on_pause = on_pause;
    plugin->on_step = on_step;
    plugin->on_resume = on_resume;
    logf_("initialized; logging every %u steps", every);
    return 0;
}
