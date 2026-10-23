#ifndef SNOW_LOCAL_PROTECTION_H
#define SNOW_LOCAL_PROTECTION_H
#include <windows.h>
#include <stdint.h>
/* Experimental local-build resolver. Fresh identity checks are not a lifetime
 * pin for the private continuation allocation. Resolve once before observation;
 * retain this context and its dependencies until process exit. */
typedef LONG (WINAPI *SnowNativeProtect)(HANDLE,PVOID *,SIZE_T *,ULONG,PULONG);
typedef ULONG (WINAPI *SnowStatusError)(LONG);
typedef struct {
    int compatible,sampled,joined,rechecked,pinned;
    SnowNativeProtect call;
    SnowStatusError error;
    volatile LONG calls,last_status;
} SnowLocalProtection;
int snow_local_protection_resolve(SnowLocalProtection *out);
BOOL snow_local_protection_apply(void *context,void *address,SIZE_T size,DWORD protection,DWORD *old);
#endif
