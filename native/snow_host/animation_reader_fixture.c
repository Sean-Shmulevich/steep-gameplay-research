/* Portable test entry. This file never opens a process. */
#include "snow_animation_reader.h"
int snow_animation_fixture(SnowAnimationRead read, void *context, uint64_t entity,
        const SnowAnimationProfile *profile, uint32_t key, SnowAnimationChannelRaw *out) {
    return snow_animation_observe(read,context,entity,profile,key,out);
}

int snow_cached_parent_fixture(SnowAnimationRead read, void *context, uint64_t entity,
        const SnowAnimationProfile *profile, SnowCachedParentRaw *out) {
    return snow_cached_parent_observe(read,context,entity,profile,out);
}
