/* Authored x64 Win64 adapter, not extracted game assembly.
 * 32 bytes of callee shadow space, then 40 bytes of entry metadata.
 * Entry RSP is 8 mod 16, so subtracting 72 aligns RSP for the C call.
 * Nonvolatile registers are untouched; the C callee must preserve them.
 */
.text
.p2align 4
.globl SnowProbe_EntryThunk
.def SnowProbe_EntryThunk; .scl 2; .type 32; .endef
.seh_proc SnowProbe_EntryThunk
SnowProbe_EntryThunk:
    subq $72, %rsp
    .seh_stackalloc 72
    .seh_endprologue
    movq %rdi, 32(%rsp)
    movq %rsi, 40(%rsp)
    movq %rbx, 48(%rsp)
    movq 72(%rsp), %rax
    movq %rax, 56(%rsp)
    leaq 72(%rsp), %rax
    movq %rax, 64(%rsp)
    leaq 32(%rsp), %r9
    call SnowProbe_EntryDispatch
    addq $72, %rsp
    ret
.seh_endproc
