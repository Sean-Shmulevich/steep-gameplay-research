/* Bounded passive reader. Layout evidence: CENTRAL_IMPULSE.md, composed player
 * animation observation API; engine/player_animation_observation.py.
 * Observer bounds/rechecks are authored policy, not native synchronization.
 * Transport must perform exact safe reads and enforce process/build identity.
 * No pointer is returned. Equality does not exclude ABA or concurrent mutation. */
#ifndef SNOW_ANIMATION_READER_H
#define SNOW_ANIMATION_READER_H
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "snow_adapter.h"
#include "snow_provider_transform.h"

typedef int (*SnowAnimationRead)(void *, uint64_t, void *, size_t);
typedef struct SnowAnimationProfile {
    uint64_t entity_tables[16], skeleton_table, type_getter, descriptor_global;
    unsigned entity_table_count;
} SnowAnimationProfile;
typedef struct SnowAnimationSpan {
    uint64_t address;
    size_t size;
    unsigned char bytes[256];
} SnowAnimationSpan;
typedef struct SnowAnimationCapture {
    SnowAnimationRead read;
    void *context;
    unsigned count;
    SnowAnimationSpan spans[512];
} SnowAnimationCapture;

static int snow_anim_range(uint64_t a, size_t n) {
    return a >= 0x10000 && a < UINT64_C(0x800000000000) && n <= UINT64_C(0x800000000000)-a;
}
static int snow_anim_keep(SnowAnimationCapture *c, uint64_t a, void *out, size_t n) {
    if (!snow_anim_range(a,n)) return 0;
    unsigned char *dst = out;
    while (n) {
        if (c->count == 512) return 0;
        SnowAnimationSpan *s = &c->spans[c->count++];
        s->address = a; s->size = n > 256 ? 256 : n;
        if (!c->read(c->context, a, s->bytes, s->size)) return 0;
        memcpy(dst, s->bytes, s->size);
        a += s->size; dst += s->size; n -= s->size;
    }
    return 1;
}
static uint16_t snow_anim_u16(const void *p) { uint16_t v; memcpy(&v,p,2); return v; }
static uint64_t snow_anim_u64(const void *p) { uint64_t v; memcpy(&v,p,8); return v; }

static int snow_anim_bind(SnowAnimationCapture *c, uint64_t entity,
        const SnowAnimationProfile *p, uint64_t *out) {
    uint64_t table,components[256],component=0,owner,getter,descriptor,name;
    unsigned char header[12],code[8],typename_bytes[18],bounds[4],cache[4],tag;
    unsigned matches=0,count;
#define KEEP(a,v) do { if (!snow_anim_keep(c,(a),&(v),sizeof(v))) goto refused; } while(0)
    KEEP(entity,table);
    unsigned accepted=0;
    for (unsigned i=0;i<p->entity_table_count;i++) accepted |= table == p->entity_tables[i];
    if (!accepted) goto refused;
    KEEP(entity+0x88,header); count=snow_anim_u16(header+10);
    if (count>256) goto refused;
    KEEP(entity+0x1aa,cache); KEEP(entity+0x1f9,tag);
    if (count && !snow_anim_keep(c,snow_anim_u64(header),components,count*8)) goto refused;
    for (unsigned i=0;i<count;i++) {
        KEEP(components[i],table);
        if (table==p->skeleton_table) { component=components[i]; matches++; }
    }
    if (matches!=1 || !snow_anim_range(component,0xc5c)) goto refused;
    KEEP(p->skeleton_table+0x30,getter);
    if (getter!=p->type_getter) goto refused;
    KEEP(getter,code);
    int32_t displacement; memcpy(&displacement,code+3,4);
    if (memcmp(code,"\x48\x8b\x05",3) || code[7]!=0xc3 ||
        getter+7+(int64_t)displacement!=p->descriptor_global) goto refused;
    KEEP(p->descriptor_global,descriptor);
    if (!snow_anim_range(descriptor,0x50)) goto refused;
    KEEP(descriptor+0x18,name);
    KEEP(name,typename_bytes);
    if (memcmp(typename_bytes,"SkeletonComponent",18)) goto refused;
    KEEP(descriptor+0x4c,bounds); KEEP(component+0x10,owner);
    if (owner!=entity) goto refused;
    *out=component; return 1;
refused: return 0;
#undef KEEP
}

/* Returns 0 only after all retained spans match. Output stays zero on refusal.
 * Returns local records and recovered provider conversion; no clip identity. */
static int snow_animation_observe(SnowAnimationRead read, void *context,
        uint64_t entity, const SnowAnimationProfile *p, uint32_t key,
        SnowAnimationChannelRaw *out) {
    if (!out) return 1;
    memset(out,0,sizeof *out);
    if (!read || !p || !p->entity_table_count || p->entity_table_count > 16) return 1;
    if (!snow_anim_range(entity,0x1fa) || !snow_anim_range(p->skeleton_table,0x38)) return 1;
    SnowAnimationCapture *c = calloc(1,sizeof *c);
    if (!c) return 1;
    c->read=read; c->context=context;
    SnowAnimationChannelRaw result = {0};
    uint64_t component=0, owner, resource, metadata, records;
    unsigned char header[12], selection[32], sizes[4];
    uint32_t epoch, flags, entries[4096][2];
    uint16_t record_count;
    unsigned count, index=65535;
#define KEEP(a,v) do { if (!snow_anim_keep(c,(a),&(v),sizeof(v))) goto refused; } while(0)
    if (!snow_anim_bind(c,entity,p,&component)) goto refused;
    owner=entity;
    /* The indirect getter refreshes then copies owner+0x20 into scratch. Observe
     * the backing matrix without invoking it or treating scratch as current. */
    uint64_t accessor;
    KEEP(owner+0x18,accessor);
    if (accessor) {
        if (!snow_anim_range(accessor,0x99)) goto refused;
        uint64_t backlink; unsigned char state[13];
        KEEP(accessor+0x40,backlink);
        if (backlink!=owner) goto refused;
        KEEP(accessor+0x8c,state);
        memcpy(&result.owner_reader_word,state,4);
        result.owner_accessor_present=1;
    }
    KEEP(owner+0x20,result.owner_matrix);
    for(unsigned i=0;i<16;i++) if (!isfinite(result.owner_matrix[i])) goto refused;

    KEEP(component+0x258,selection); KEEP(component+0xc58,epoch);
    KEEP(component+0x240,resource);
    if (resource) {
        if (!snow_anim_range(resource,0x44)) goto refused;
        KEEP(resource+0x38,header); count=snow_anim_u16(header+10);
        if (count>4096) goto refused;
        if (count && !snow_anim_keep(c,snow_anim_u64(header),entries,count*8)) goto refused;
        for (unsigned i=1;i<count;i++) if (entries[i][0]<entries[i-1][0]) goto refused;
        unsigned lo=0,hi=count;
        while (lo<hi) { unsigned mid=lo+(hi-lo)/2; if(entries[mid][0]<key)lo=mid+1;else hi=mid; }
        if (lo<count && entries[lo][0]==key) index=entries[lo][1]&65535;
    }
    if (index!=65535) {
        uint64_t bank=snow_anim_u64(selection);
        if (!snow_anim_range(bank,0x1a0)) goto refused;
        KEEP(bank+0x8c,flags); KEEP(bank+0x190,metadata);
        if (!snow_anim_range(metadata,0x5c)) goto refused;
        KEEP(metadata+0x14,sizes); KEEP(metadata+0x5a,record_count);
        unsigned allocation=snow_anim_u16(sizes+((flags&(1u<<28))?2:0));
        if (index>=record_count || (uint32_t)record_count*32>allocation) goto refused;
        KEEP(bank+0x198,records);
        if (records<0x10000 || records>UINT64_C(0x800000000000)-(uint64_t)record_count*32) goto refused;
        float lanes[8]; KEEP(records+(uint64_t)index*32,lanes);
        for(unsigned i=0;i<8;i++) if (!isfinite(lanes[i])) goto refused;
        memcpy(result.vector,lanes,16); memcpy(result.rotation,lanes+4,16);
        float parent[8]; KEEP(bank,parent);
        for(unsigned i=0;i<8;i++) if (!isfinite(parent[i])) goto refused;
        memcpy(result.parent_vector,parent,16); memcpy(result.parent_rotation,parent+4,16);
        snow_provider_transform(lanes,lanes+4,parent,parent+4,!!(flags&(1u<<26)),
                                result.provider_vector,result.provider_rotation);
        for(unsigned i=0;i<4;i++) if (!isfinite(result.provider_vector[i]) || !isfinite(result.provider_rotation[i])) goto refused;
        result.record_index=index; result.bank_flags=flags;
        result.found=1;
    }
    for (unsigned i=0;i<c->count;i++) {
        unsigned char bytes[256]; SnowAnimationSpan *s=&c->spans[i];
        if (!read(context,s->address,bytes,s->size) || memcmp(bytes,s->bytes,s->size)) goto refused;
    }
    result.epoch=epoch; result.guards_matched=1; *out=result;
    free(c); return 0;
refused:
    free(c); return 1;
#undef KEEP
}

/* Address-free callback observation. It does not validate executable permissions. */


static inline int snow_cached_parent_observe(SnowAnimationRead read, void *context,
        uint64_t entity, const SnowAnimationProfile *p, SnowCachedParentRaw *out) {
    if (!out) return 1;
    memset(out,0,sizeof *out);
    if (!read || !p || !p->entity_table_count || p->entity_table_count>16 ||
        !snow_anim_range(entity,0x1fa) || !snow_anim_range(p->skeleton_table,0x38)) return 1;
    SnowAnimationCapture *c=calloc(1,sizeof *c);
    if (!c) return 1;
    c->read=read; c->context=context;
    SnowCachedParentRaw r={0}; uint64_t component,banks[2],callback[5],target=0;
    unsigned char holder[16]; uint32_t status=0;
#define KEEP(a,v) do { if (!snow_anim_keep(c,(a),&(v),sizeof(v))) goto refused; } while(0)
    if (!snow_anim_bind(c,entity,p,&component)) goto refused;
    KEEP(component+0x130,r.cached); KEEP(component+0x250,banks);
    KEEP(component+0x290,callback);
    r.primary_present=!!banks[0]; r.current_present=!!banks[1];
    r.banks_alias=banks[0] && banks[0]==banks[1];
    r.storage_nonempty=!!(callback[0] || (callback[2]&~UINT64_C(3)));
    r.context_tag=callback[2]&3; r.context_nonzero=!!(callback[2]&~UINT64_C(3));
    r.function_present=!!callback[3]; r.holder_present=!!callback[4];
    if (callback[4]) {
        KEEP(callback[4],holder); target=snow_anim_u64(holder); memcpy(&status,holder+12,4);
    } else if (r.primary_present && r.storage_nonempty) goto refused;
    r.target_present=!!target; r.status_sign=!!(status&UINT32_C(0x80000000));
    r.eligible=r.primary_present && r.storage_nonempty && r.target_present && r.status_sign;
    if (banks[0]) KEEP(banks[0],r.primary);
    if (banks[1]) KEEP(banks[1],r.current);
    for (unsigned i=0;i<8;i++)
        if (!isfinite(r.cached[i]) || !isfinite(r.primary[i]) || !isfinite(r.current[i])) goto refused;
    for (unsigned i=0;i<c->count;i++) {
        unsigned char bytes[256]; SnowAnimationSpan *span=&c->spans[i];
        if (!read(context,span->address,bytes,span->size) || memcmp(bytes,span->bytes,span->size)) goto refused;
    }
    r.guards_matched=1; *out=r; free(c); return 0;
refused: free(c); return 1;
#undef KEEP
}
#endif
