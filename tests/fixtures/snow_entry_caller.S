/* Authored fixture caller, no game code. Win64 arguments:
 * actor, elapsed, consumed, register snapshot, target function.
 */
.text
.p2align 4
.globl fixture_entry_call
.globl fixture_entry_return
.def fixture_entry_call; .scl 2; .type 32; .endef
.seh_proc fixture_entry_call
fixture_entry_call:
    pushq %rdi
    .seh_pushreg %rdi
    pushq %rsi
    .seh_pushreg %rsi
    pushq %rbx
    .seh_pushreg %rbx
    subq $32, %rsp
    .seh_stackalloc 32
    .seh_endprologue
    movq 0(%r9), %rdi
    movq 8(%r9), %rsi
    movq 16(%r9), %rbx
    call *96(%rsp)
fixture_entry_return:
    addq $32, %rsp
    popq %rbx
    popq %rsi
    popq %rdi
    ret
.seh_endproc
