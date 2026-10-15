/* Internal interface between the host core and its plugin manager. All
 * functions are called from the host executor thread only. */
#ifndef SNOW_PLUGINS_H
#define SNOW_PLUGINS_H
#include <stddef.h>
#include <wchar.h>
#include "snow_plugin.h"

#define SNOW_HOST_VERSION "0.6.0"

/* Provided by snow_host.c. */
void snow_host_log(const char *tag, const char *fmt, ...);
void snow_host_state(SnowHostStateV1 *out);
int snow_host_player(SnowPlayerStateV1 *out);
int snow_host_set_velocity(const float v[3]);
int snow_host_set_pose(const SnowPlayerStateV1 *target);

/* Provided by snow_plugins.c. */
int snow_plugins_init(const wchar_t *dir);   /* loads <dir>\plugins\*.dll; returns active count */
int snow_plugins_active(void);
void snow_plugins_on_pause(void);
void snow_plugins_on_step(const SnowStepInfoV1 *step);
void snow_plugins_on_resume(SnowResumeReason reason);
void snow_plugins_on_player(const SnowPlayerEventV1 *event);
size_t snow_plugins_describe(char *buf, size_t n); /* JSON array */
#endif
