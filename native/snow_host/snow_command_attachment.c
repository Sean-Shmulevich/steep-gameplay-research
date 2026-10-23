#include "snow_command_attachment.h"
#include <stddef.h>
_Static_assert(sizeof(void *)==8,"attachment requires 64-bit pointers");
_Static_assert(offsetof(SnowCommandAttachment,references)==8,"reference ABI");
_Static_assert(offsetof(SnowCommandAttachmentVtable,destroy)==8,"destructor ABI");
static void destroy(SnowCommandAttachment *a) {
    SnowCommandAttachmentFinalizer finalize=a->finalize;
    void *context=a->context;
    finalize(a,context); /* May free a. Do not access it afterward. */
}
static const SnowCommandAttachmentVtable table={0,destroy};
int snow_command_attachment_init(SnowCommandAttachment *a,void *context,
                                SnowCommandAttachmentFinalizer finalize) {
    if(!a || !finalize)return 0;
    a->vtable=&table;a->references=1;a->reserved=0;
    a->context=context;a->finalize=finalize;
    return 1;
}
int snow_command_attachment_release(SnowCommandAttachment *a) {
    if(!a)return 0;
    uint32_t count=__atomic_load_n(&a->references,__ATOMIC_SEQ_CST);
    for(;;) {
        if(!count)return 0;
        if(__atomic_compare_exchange_n(&a->references,&count,count-1,0,
                                      __ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST))break;
    }
    if(count==1)destroy(a);
    return 1;
}
