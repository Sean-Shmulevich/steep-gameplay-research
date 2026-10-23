#ifndef SNOW_COMMAND_ATTACHMENT_H
#define SNOW_COMMAND_ATTACHMENT_H
#include <stdint.h>
/* Authored owner matching the associated-object prefix inspected in
 * REQUEST_COMMAND_LIFECYCLE.md, attachment copying and cleanup sections.
 * Windows x64 only for native use. Host builds are synthetic fixtures.
 * Initialize unpublished storage once, then transfer its one reference through
 * snow_command_admit_attached. On refusal release it or retry submission.
 * No allocator, module pin, execution receipt, or native lifetime qualification.
 */
typedef struct SnowCommandAttachment SnowCommandAttachment;
typedef void (*SnowCommandAttachmentFinalizer)(SnowCommandAttachment *,void *);
typedef struct {
    void (*reserved)(void);
    void (*destroy)(SnowCommandAttachment *);
} SnowCommandAttachmentVtable;
struct SnowCommandAttachment {
    const SnowCommandAttachmentVtable *vtable;
    uint32_t references;
    uint32_t reserved;
    void *context;
    SnowCommandAttachmentFinalizer finalize;
};
/* Storage must not be live/published. Null finalizer is rejected. */
int snow_command_attachment_init(SnowCommandAttachment *,void *,SnowCommandAttachmentFinalizer);
/* Release ONE owned live reference. A finalizer may free this object and may
 * run on any releasing thread, including before admission returns. Keep its
 * code/module resident through return. No access after releasing the last ref.
 * Returns 1 for release, 0 for null/zero count. Zero rejection is authored policy,
 * not protection against stale pointers, double release, or concurrent freeing.
 * Never modify public ABI fields after initialization; no reinitialization while
 * retained. Finalization means ownership ended, not that a command executed.
 */
int snow_command_attachment_release(SnowCommandAttachment *);
#endif
