# Physics lock map (protected guard globals)

Static map of the guard globals that the physics code region passes to its protected call stubs: which
functions use each guard, how the calls pair up, what is touched in between, and which reconstructed
routines already run under which guard. This is a read-only static pass over the image. It makes no claim about what the
protected stubs do. The tag "protected guard N" below means only "a global passed in the first
argument of a protected stub"; the lock type is being determined separately and is deliberately not asserted here.

Offsets are evidence anchors for the analysed build, not portable API fields. Nothing here claims
original-engine equivalence, and the tables are an analysis aid, not recovered behavior.

## Method

- Scope: the 66 unwind chunks of the image's physics range that contain a protected call whose
  first argument is loaded from one of 18 guard globals, taken from the thread census (141 sites).
- Each chunk is walked as a control-flow graph. A protected stub appears to return one byte past its call
  when the next byte is not an instruction prefix (the linear decode shows a one-byte filler), so the walk resumes
  after that byte. Without this the CFG invents false branches.
- A per-guard counter (modulo 4) is propagated along all paths. An even count at an exit means the
  calls balanced on that path. Odd exits are followed into the next unwind chunk (cold chunks split off
  the function) so a pair split across chunks is still matched.
- Register provenance tags (global-loaded pointer, argument, offset-of-argument) name the memory touched while
  the count is odd.
- Seven further stub calls have no `mov rcx` immediately before them (the load sits in the previous chunk, or is
  separated by another instruction); they were attached to the guard from register provenance or by looking back across
  the chunk boundary (marked with a star).
- Pairing is positional: first call is called A (acquire hypothesis), second R (release hypothesis).

## Summary

Every guard global G has a sibling global at G-8 that is used as the base pointer of a free-list pool
(count dword at +0x28, free-list head at +0x30), with two exceptions noted below (0x143336858 and 0x1433365d0). On the
second (R) call in 11 of 74 pairs the second argument register still carries that pool pointer (`rdx` loaded from the
global at G-8) when the walk reaches the call; in the remaining cases the register was overwritten or not tracked. For those
pairs the A/R reading has an independent supporting argument.

| Guard | Sites | Chunks | Pairing | Pool global | Best-known role (from existing reconstructions) |
|---|---|---|---|---|---|
| 0x143336bb8 | 22 | 10 | 2 paired, 1 cross-chunk, 1 cross-chunk (release half), 6 paired (loop or repeated) | 0x143336bb0 | contact payload pool; take 18dcff0, batch refill 18de060, return in 1958720/1958ba0 |
| 0x143336800 | 14 | 4 | 4 paired | 0x1433367f8 | 12-byte triple-float body record pool (body+0x1c0 slot); setters 18a9c30/18a9b00/18a9d60, destructor 18be6b0 |
| 0x1433367f0 | 12 | 5 | 5 paired | 0x1433367e8 | 16-byte body parameter record pool (body+0x1b8 slot); setters 18a98d0/18a9e90, destructor 18be6b0 |
| 0x143336aa0 | 12 | 5 | 1 paired (loop or repeated), 4 paired | 0x143336a98 | pose group storage pool; take 18b5c00 (pose_group_pool receipt) |
| 0x1433367d0 | 8 | 4 | 4 paired | 0x1433367c8 | not named in existing docs |
| 0x143336810 | 8 | 4 | 4 paired | 0x143336808 | not named in existing docs |
| 0x143336868 | 8 | 4 | 4 paired | 0x143336860 | not named in existing docs |
| 0x143336878 | 8 | 4 | 4 paired | 0x143336870 | not named in existing docs |
| 0x143336888 | 8 | 4 | 4 paired | 0x143336880 | not named in existing docs |
| 0x143336ac0 | 8 | 5 | 2 paired, 1 paired (loop or repeated), 1 cross-chunk, 1 cross-chunk (release half) | 0x143336ab8 | link object pool; take 18b5d10, refill 18de1e0 |
| 0x143336728 | 6 | 3 | 2 paired, 1 paired (loop or repeated) | 0x143336720 | not named in existing docs |
| 0x1433365d0 | 6 | 3 | 3 paired | 0x1433365c8 (container) | not named in existing docs |
| 0x143336bc8 | 6 | 3 | 1 paired, 2 paired (loop or repeated) | 0x143336bc0 | not named in existing docs |
| 0x143336ab0 | 6 | 3 | 3 paired | 0x143336aa8 | link held-record pool (link+0x78); release 18de3e0, take via 18dd100, return in 1958ba0 |
| 0x1433367e0 | 4 | 2 | 2 paired | 0x1433367d8 | body base-destructor metadata (+0x30) pool; base destructor 18a7bc0 |
| 0x143336858 | 4 | 2 | 2 conditional/ambiguous | 0x143336848 (shared object) | not named in existing docs |
| 0x143336748 | 4 | 2 | 2 paired | 0x143336740 | not named in existing docs |
| 0x143336ba8 | 4 | 2 | 2 paired | 0x143336ba0 | not named in existing docs |

A = first call (acquire hypothesis), R = second call, star = guard attached by look-back across a chunk boundary.

## Protected guard 0x143336bb8

Adjacent pool global 0x143336bb0. contact payload pool; take 18dcff0, batch refill 18de060, return in 1958720/1958ba0.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18dc740 | 0x18dc74d A 0x18dc76a R | paired | calls 0x18dcff0 | none |
| 0x18dc8a0 | 0x18dcaa0 A 0x18dcabc R 0x18dcb83 A 0x18dcb9f R | paired | calls 0x18dcff0 | none |
| 0x18de060 | 0x18de076 A | cross-chunk | none visible | pose_pair_contact_generation, pose_pair_contact_generation receipt |
| 0x18de060 / 0x18de1bb | 0x18de1cc R | cross-chunk (release half) | none visible | pose_pair_contact_generation, pose_contact_pool_batch receipt, pose_pair_contact_generation receipt |
| 0x1958610 / 0x195863c | 0x1958651 A 0x1958674 R | paired (loop or repeated) | pool 0x143336bb0 count +0x28 and head +0x30 (rw); 1 register-relative cells | none |
| 0x1958720 / 0x19587c8 | 0x19587f1 A 0x1958812 R | paired (loop or repeated) | pool 0x143336bb0 count +0x28 and head +0x30 (rw); 1 register-relative cells | pose_link_state_reset, pose_body_connectivity_retire receipt, pose_link_payloads receipt |
| 0x1958896 / 0x195889b | 0x1958908 A 0x1958923 R 0x195898e A 0x19589b1 R | paired (loop or repeated) | pool 0x143336bb0 count +0x28 and head +0x30 (rw); 1 register-relative cells; calls 0x18dcff0 | none |
| 0x1958c30 / 0x1958c61 | 0x1958ca6 A 0x1958cc7 R | paired (loop or repeated) | pool 0x143336bb0 count +0x28 and head +0x30 (rw); 1 register-relative cells | none |
| 0x1989cdc / 0x1989d16 | 0x1989d36 A 0x1989d58 R | paired (loop or repeated) | pool 0x143336bb0 count +0x28 and head +0x30 (rw); 1 register-relative cells | none |
| 0x198f910 | 0x198fcbb A 0x198fcd8 R | paired (loop or repeated) | calls 0x18dcff0 | pose_contact_consumer receipt |

## Protected guard 0x143336800

Adjacent pool global 0x1433367f8. 12-byte triple-float body record pool (body+0x1c0 slot); setters 18a9c30/18a9b00/18a9d60, destructor 18be6b0.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18a9b00 | 0x18a9b39 A 0x18a9b56 R 0x18a9beb A 0x18a9c0c R | paired | pool 0x1433367f8 count +0x28 and head +0x30 (rw); arg0+0x1c0 slot (w); calls 0x18a91c0 | pose_body_parameters receipt |
| 0x18a9c30 | 0x18a9c69 A 0x18a9c86 R 0x18a9d18 A 0x18a9d39 R | paired | pool 0x1433367f8 count +0x28 and head +0x30 (rw); arg0+0x1c0 slot (w); calls 0x18a91c0 | pose_body_parameters receipt |
| 0x18a9d60 | 0x18a9d99 A 0x18a9db6 R 0x18a9e4a A 0x18a9e6c R | paired | pool 0x1433367f8 count +0x28 and head +0x30 (rw); arg0+0x1c0 slot (w); calls 0x18a91c0 | pose_body_parameters receipt |
| 0x18be6b0 | 0x18be720 A 0x18be742 R | paired | pool 0x1433367f8 count +0x28 and head +0x30 (rw); arg0+0x1c0 slot (w) | pose_body_destruction receipt |

## Protected guard 0x1433367f0

Adjacent pool global 0x1433367e8. 16-byte body parameter record pool (body+0x1b8 slot); setters 18a98d0/18a9e90, destructor 18be6b0.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18a8f90 | 0x18a8fa1 A 0x18a8fc7 R | paired | pool 0x1433367e8 count +0x28 and head +0x30 (rw); freed node word 0 (w) | none |
| 0x18a98d0 / 0x18a9944 | 0x18a994a A* 0x18a9965 R | paired | calls 0x18a91c0 | pose_body_parameters receipt |
| 0x18a9e90 / 0x18a9f03 | 0x18a9f08 A* 0x18a9f24 R | paired | calls 0x18a91c0 | pose_body_parameters receipt |
| 0x18be6b0 | 0x18be6db A 0x18be6fd R | paired | pool 0x1433367e8 count +0x28 and head +0x30 (rw); arg0+0x1b8 slot (w) | pose_body_destruction receipt |
| 0x18bec5f / 0x18bee28 | 0x18beeba A 0x18beedc R 0x18beefb A 0x18bef16 R | paired | pool 0x1433367e8 count +0x28 and head +0x30 (rw); 1 register-relative cells; calls 0x18a91c0 | none |

## Protected guard 0x143336aa0

Adjacent pool global 0x143336a98. pose group storage pool; take 18b5c00 (pose_group_pool receipt).

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18b5e70 / 0x18b60a6 | 0x18b60f8 A 0x18b6114 R | paired (loop or repeated) | calls 0x18b5c00 | none |
| 0x18e0ca0 | 0x18e0cc3 A 0x18e0cdf R 0x18e0d0a A 0x18e0d25 R | paired | calls 0x18b5c00 | LINK_SOLVER prose |
| 0x18e19c0 | 0x18e19df A 0x18e19fc R | paired | calls 0x18b5c00 | pose_group_process_bytes |
| 0x18e1a60 | 0x18e1a80 A 0x18e1a9b R | paired | calls 0x18b5c00 | none |
| 0x19572c0 | 0x19572e8 A 0x195730a R | paired | pool 0x143336a98 count +0x28 and head +0x30 (rw); freed node word 0 (w) | CENTRAL_IMPULSE prose |

## Protected guard 0x1433367d0

Adjacent pool global 0x1433367c8. No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18a7cc0 | 0x18a7ce8 A 0x18a7d09 R | paired | pool 0x1433367c8 count +0x28 and head +0x30 (rw); freed node word 0 (w) | none |
| 0x18a8d10 | 0x18a8d35 A 0x18a8d51 R | paired | calls 0x18a7e50 | none |
| 0x18bbaf0 | 0x18bbb0d A 0x18bbb29 R | paired | calls 0x18a7e50 | none |
| 0x19ea0f0 | 0x19ea14a A 0x19ea166 R | paired | calls 0x18a7e50 | none |

## Protected guard 0x143336810

Adjacent pool global 0x143336808. No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18a8fd0 | 0x18a8ff8 A 0x18a901a R | paired | pool 0x143336808 count +0x28 and head +0x30 (rw); freed node word 0 (w) | none |
| 0x18aa5e0 | 0x18aa604 A 0x18aa620 R | paired | calls 0x18a90b0 | none |
| 0x18beb60 | 0x18beb7d A 0x18beb99 R | paired | calls 0x18a90b0 | none |
| 0x19ea0f0 | 0x19ea10e A 0x19ea12a R | paired | calls 0x18a90b0 | none |

## Protected guard 0x143336868

Adjacent pool global 0x143336860. No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18aa680 | 0x18aa68d A 0x18aa6aa R | paired | calls 0x18aa9a0 | none |
| 0x18aa740 | 0x18aa78e A 0x18aa7af R | paired | pool 0x143336860 count +0x28 and head +0x30 (rw); freed node word 0 (w) | pose_resource_lifecycle receipt |
| 0x18abcb0 / 0x18abd80 | 0x18abd8e A* 0x18abda9 R | paired | calls 0x18aa9a0 | none |
| 0x18c5370 | 0x18c5385 A 0x18c53a1 R | paired | calls 0x18aa9a0 | LINK_SOLVER prose |

## Protected guard 0x143336878

Adjacent pool global 0x143336870. No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18aa6c0 | 0x18aa6cd A 0x18aa6ea R | paired | calls 0x18aaab0 | none |
| 0x18aa7e0 | 0x18aa82d A 0x18aa850 R | paired | pool 0x143336870 count +0x28 and head +0x30 (rw); freed node word 0 (w) | none |
| 0x18abe80 / 0x18abf59 | 0x18abf61 A* 0x18abf7d R | paired | calls 0x18aaab0 | none |
| 0x18c63e0 | 0x18c63f4 A 0x18c6411 R | paired | calls 0x18aaab0 | none |

## Protected guard 0x143336888

Adjacent pool global 0x143336880. No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18aa700 | 0x18aa70e A 0x18aa72a R | paired | calls 0x18aaab0 | none |
| 0x18aa900 | 0x18aa94d A 0x18aa96f R | paired | pool 0x143336880 count +0x28 and head +0x30 (rw); freed node word 0 (w) | none |
| 0x18ac050 / 0x18ac120 | 0x18ac128 A* 0x18ac144 R | paired | calls 0x18aaab0 | none |
| 0x18c74f0 | 0x18c7505 A 0x18c7520 R | paired | calls 0x18aaab0 | none |

## Protected guard 0x143336ac0

Adjacent pool global 0x143336ab8. link object pool; take 18b5d10, refill 18de1e0.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18b5b00 | 0x18b5b45 A 0x18b5b66 R | paired | pool 0x143336ab8 count +0x28 and head +0x30 (rw); freed node word 0 (w) | none |
| 0x18b6190 / 0x18b619e | 0x18b61d7 A 0x18b61f3 R | paired (loop or repeated) | calls 0x18b5d10 | none |
| 0x18dc8a0 | 0x18dc9bd A 0x18dc9d9 R | paired | calls 0x18b5d10 | none |
| 0x18de1e0 | 0x18de1f6 A | cross-chunk | none visible | pose_link_pool_refill, pose_pair_link_worker, pose_link_pool_refill receipt |
| 0x18de1e0 / 0x18de2c2 | 0x18de2d5 R | cross-chunk (release half) | none visible | pose_link_pool_refill, pose_pair_link_worker, pose_link_pool_refill receipt |

## Protected guard 0x143336728

Adjacent pool global 0x143336720. No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18a7910 | 0x18a792c A 0x18a7949 R | paired | calls 0x18a7770 | none |
| 0x18b6430 / 0x18b6449 | 0x18b6467 A 0x18b6484 R* | paired (loop or repeated) | calls 0x18a7770 | none |
| 0x18b9bd0 | 0x18b9bf7 A 0x18b9c19 R | paired | pool 0x143336720 count +0x28 and head +0x30 (rw); freed node word 0 (w) | none |

## Protected guard 0x1433365d0

Adjacent global 0x1433365c8 holds an indexed container (not a free-list pool). No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18b6de0 | 0x18b6dfe A 0x18b6e3b R | paired | calls 0x18b6f90 | none |
| 0x18b6e50 | 0x18b6e6b A 0x18b6eb9 R | paired | 1 register-relative cells | none |
| 0x18b6f00 | 0x18b6f16 A 0x18b6f7d R | paired | 3 register-relative cells; calls indirect | none |

## Protected guard 0x143336bc8

Adjacent pool global 0x143336bc0. No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18d9040 | 0x18d905b A 0x18d9078 R | paired | calls 0x18d8f30 | none |
| 0x18d9150 / 0x18d9165 | 0x18d917b A 0x18d919c R | paired (loop or repeated) | pool 0x143336bc0 count +0x28 and head +0x30 (rw); 1 register-relative cells | none |
| 0x18d91e9 / 0x18d9222 | 0x18d927f A 0x18d92a0 R | paired (loop or repeated) | pool 0x143336bc0 count +0x28 and head +0x30 (rw); 1 register-relative cells | none |

## Protected guard 0x143336ab0

Adjacent pool global 0x143336aa8. link held-record pool (link+0x78); release 18de3e0, take via 18dd100, return in 1958ba0.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18de3e0 | 0x18de3f8 A 0x18de41b R | paired | pool 0x143336aa8 count +0x28 and head +0x30 (rw); arg0+0x78 held record (w) | pose_link_held_release, pose_pair_external_contacts, pose_pair_link_worker |
| 0x18e0ad0 | 0x18e0afe A 0x18e0b1a R | paired | calls 0x18dd100 | pose_pair_external_contacts, pose_pair_link_worker, pose_pair_external_contacts receipt |
| 0x1958ba0 | 0x1958bd9 A 0x1958bfa R | paired | pool 0x143336aa8 count +0x28 and head +0x30 (rw); arg0+0x78 held record (w) | pose_body_connectivity_retire, pose_link_state_reset, pose_body_connectivity_retire receipt |

## Protected guard 0x1433367e0

Adjacent pool global 0x1433367d8. body base-destructor metadata (+0x30) pool; base destructor 18a7bc0.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18a7a70 | 0x18a7ae8 A 0x18a7b03 R | paired | calls 0x18a7d40 | none |
| 0x18a7bc0 | 0x18a7bec A 0x18a7c0f R | paired | pool 0x1433367d8 count +0x28 and head +0x30 (rw); arg0+0x30 metadata slot (w) | pose_body_destruction receipt |

## Protected guard 0x143336858

Adjacent global 0x143336848 holds a shared object with a count at +0x8 (not a free-list pool). No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18aae40 | 0x18aae72 A 0x18aaea5 R | conditional/ambiguous | *0x36848+0x8 (rw); calls 0x18c1b10 | none |
| 0x18c1c30 | 0x18c1c56 A 0x18c1cc3 R | conditional/ambiguous | *0x36848+0x8 (rw); *0x36848 (r); calls indirect | none |

## Protected guard 0x143336748

Adjacent pool global 0x143336740. No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18ba600 | 0x18ba60d A 0x18ba62a R | paired | calls 0x18ba4f0 | none |
| 0x18ba6a0 | 0x18ba6b0 A 0x18ba6d9 R* | paired | pool 0x143336740 count +0x28 and head +0x30 (rw); freed node word 0 (w) | LINK_SOLVER prose |

## Protected guard 0x143336ba8

Adjacent pool global 0x143336ba0. No existing reconstruction names it.

| Function (primary / chunk) | Calls in order | Pairing | Between A and R | Existing coverage |
|---|---|---|---|---|
| 0x18d2ac0 | 0x18d2acd A 0x18d2aea R | paired | calls 0x18d3140 | none |
| 0x1985ae0 | 0x1985b07 A 0x1985b29 R | paired | pool 0x143336ba0 count +0x28 and head +0x30 (rw); freed node word 0 (w) | none |

## Lock-order edges

Nested acquisition (a different guard acquired while one is held): **none found.** Within the analysed
chunks the held-set never contained two guards at once (`nested_acquire_edges` is empty).

Calls made while a guard is held (all direct callees are tiny pool allocator / accessor leaves with no
protected calls of their own):

| Held guard | Direct callees | Guards reachable through direct calls |
|---|---|---|
| 0x143336bb8 | 0x18dcff0 | none |
| 0x143336800 | 0x18a91c0 | none |
| 0x1433367f0 | 0x18a91c0 | none |
| 0x143336aa0 | 0x18b5c00 | none |
| 0x1433367d0 | 0x18a7e50 | none |
| 0x143336810 | 0x18a90b0 | none |
| 0x143336868 | 0x18aa9a0 | none |
| 0x143336878 | 0x18aaab0 | none |
| 0x143336888 | 0x18aaab0 | none |
| 0x143336ac0 | 0x18b5d10 | none |
| 0x143336728 | 0x18a7770 | none |
| 0x1433365d0 | 0x18b6f90, indirect | see note |
| 0x143336bc8 | 0x18d8f30 | none |
| 0x143336ab0 | 0x18dd100 | none |
| 0x1433367e0 | 0x18a7d40 | none |
| 0x143336858 | 0x18c1b10, indirect | see note |
| 0x143336748 | 0x18ba4f0 | none |
| 0x143336ba8 | 0x18d3140 | none |

Ordered but not nested (complete pair of one guard, then a pair of another, within one chunk):

| Chunk | Order of guards |
|---|---|
| 0x18be6b0 | 0x1433367f0 then 0x143336800 |
| 0x18dc8a0 | 0x143336ac0 then 0x143336bb8 |
| 0x19ea0f0 | 0x143336810 then 0x1433367d0 |

These sequential edges are the body destructor 0x18be6b0 returning its 16-byte and then its 12-byte record
(guards 0x1433367f0 then 0x143336800, matching the destructor description in LINK_SOLVER), a link-pool take followed by two
contact-payload takes in 0x18dc8a0, and two pool returns in 0x19ea0f0. They document an order that code follows when
it does both; they are not evidence that anything ever holds two guards at once.

## Observations worth keeping

- **Guard 0x143336858 is not a plain pair.** The two chunks (0x18aae40, 0x18c1c30) take the guard only
  when a reference-count style read (`lock xadd` on a shared object at +8) returned a small value, and
  release it under the same flag. The dataflow sees the release reached with both counts, so it is marked
  conditional rather than unpaired. The guard object here is a lazily built shared object (0x18c1b10 creates it
  when the global is null).
- **Cross-chunk pairs.** Guard 0x143336bb8 (0x18de060 to 0x18de1bb) and guard 0x143336ac0 (0x18de1e0 to
  0x18de2c2) acquire in one unwind chunk and release in a different one, with the batch-refill body
  (page table 0x1433365b8, counter 0x14333683c, allocator callee 0x18d7110 and 0x18b5d10) between them. A chunk-local scan
  alone would call these unpaired.
- **Seven census-invisible sites.** Five cold chunks begin exactly at a protected call whose `mov rcx` is in the
  preceding chunk (0x18a9944, 0x18a9f03, 0x18abd80, 0x18abf59, 0x18ac120); two more (the second call in 0x18b6449 and
  0x18ba6a0) have the argument loaded further back. All seven carry the same guard as their partner call.
- **Guard 0x1433365d0** is used with an indexed container at 0x1433365c8 (indexed reads and writes, fields at
  +0x0, +0x8 and +0xc), not with a +0x28/+0x30 free-list pair, so it does not follow the pool pattern of the others.
- **Release arguments.** Where the second call is passed the pool pointer (`rdx` = global at G-8) the call is
  consistent with a leave that needs the pool; see the `rdx` column in `guard_map.json`.
- **Not covered.** About 148 other protected calls in the same range have a first argument that is not a
  fixed global (object-relative address or an inherited register). They are outside this map; a
  nested edge between a guard here and one of them cannot be excluded.

## Explicit unknowns

- Lock type, recursion rules and wait behavior of every guard. A/R is positional only.
- Whether the stubs have effects on other state (they preserve the registers the callers need, per the
  existing link-solver notes, but that is the only contract observed).
- Indirect calls: 0x18c1c30 (vtable call at +0), 0x18b6f00 (three indirect calls under guard 0x1433365d0)
  and the out-of-line slow paths of the pool allocators were not followed.
- Whether any thread other than the census's counted callers takes these guards at runtime. The map is purely static.
- The per-site stub bodies are distinct protected code; the number of distinct targets equals the number of sites.

## Reproduction

`analysis/thread-census/guard_map.py`, `guard_reach.py`, `guard_map_build.py` and `guard_map_doc.py` regenerate
`guard_map.json` (machine-readable, per-site sequences and memory cells) and this table from the image.
