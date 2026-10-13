# Reconstruction validation scope

The automated suite covers synthetic fixtures, recovered local numerical kernels and the independent runtime's contracts. It does not establish original-game equivalence. Run `python3 -m unittest discover -s tests -q` from the repository root; HTTP tests require permission to bind loopback.

Current checkpoint: 147 tests passed. Repository packaging, source hashes and local links passed verification; the inspector JavaScript passed syntax checking. The new private-scene browser rendering has not yet been visually validated.

## Private archive checks

The read-only adapter parsed 27 locally available archives containing 165,021 index entries. A selection of 54 resources was decoded in memory with checksum and output-length checks, exercising both Zstandard and LZO paths. No decoded payload is included here. This establishes compatibility with those indexes and samples, not comprehensive decoding of every resource or every archive version.

The parser supports the observed version-27 index and observed compression-layout/type combinations. It rejects malformed bounds, duplicate resource identifiers, inconsistent lengths and unsupported framing. Native codecs are optional adapters to installed libraries. Synthetic tests cover corruption and boundary failures without reproducing game data.

## Private animation checks

The typed adapter was compared against the existing local pose-assembly reference for 100 poses: ten clips, two base rigs and five sample times. Both rigs were deliberately evaluated; this does not prove which rig or clip the game selects in a particular state. Translation scale was explicitly 1 in authored units.

- Maximum translation difference: `7.027405480595403e-08` authored units.
- Maximum sign-invariant quaternion component distance: `0.0006016519442461972`.

The largest quaternion difference occurs at a near-identical-rotation branch. The newer recovered float32 dot product reaches the copy-source threshold while the older host-double reference interpolates. These references are therefore not bit-identical; the discrepancy is retained rather than hidden by a broad tolerance. Live pose agreement remains unverified.

An imported private base rig and navigation clip also completed a 120-tick engine run without a recorded incident. This proves the adapter-to-runtime path for that resource, not correct gameplay selection, world scale, root motion, addon assembly or visual fidelity. The imported scene remains outside the public source repository.

## Determinism and boundaries

Checkpoint/replay tests include graph clocks and configuration changes. Resource replacement and tuning establish a fresh replay base. Exact hash equality is a same-runtime property; it is not a claim of cross-platform numerical determinism or deterministic replay inside the original game.

Original clip payloads, decoded skeleton arrays, private scenes and raw observation receipts are deliberately absent from this repository. Public tests use invented transforms and clips. Active rig merging, authored graph identity, root-motion ownership and actor-to-pose timing remain open reconstruction tasks.
