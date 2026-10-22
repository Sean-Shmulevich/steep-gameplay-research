# Powder: external reverse-engineering leads

Inspected upstream commit: `00fdf2af7461ba0f83de7b14801f1b7d4b9924e8`. This note records source inspection and two
local read-only fingerprint comparisons. Powder was not installed, executed,
attached to the game or copied into our implementation. Its source is AGPL-3.0.

## Direct build correlation

Our executable SHA-256 matches Powder's supported Ubisoft Connect TU7 entry:
`e8b14fe6f3b45975080f1b8e78249bf8fefbbd73ee4c182156c0b8a66452e8cb`.
The corresponding 64-byte window in our private mapped image matches Powder's
readiness fingerprint:
`710263eff728e572e93557ae30b9b125415ed61657273c967ae8822b66c0e8e9`.
These are verified local comparisons, not proof of Wine compatibility or a
complete cross-build address mapping. No executable bytes are included here.

## Highest-value leads

1. **Startup readiness.** The launcher checks executable identity, distinguishes
   the long-lived game from a startup stub, and waits for a known code hash with
   nonwritable page protection before attachment. Upstream documents crashes when
   attaching while the protector was still writing. This is a useful hypothesis
   for our timing-sensitive startup failures, not a diagnosis of those failures.
2. **Protection behavior.** Native helper comments identify VMProtect, describe
   code-patch/debug-register detection and a staged TLS interception strategy.
   The source implements that strategy, but we have not independently established
   its protection attribution or reproduced it. It is not a general safe-point,
   physics-scheduler hook, or proof that our prior exits had the same cause.
3. **Replay/ghost acquisition.** Profile entity extended storage exposes upload
   and download paths for saved rides and challenge ghosts. The inspected handler
   stores opaque bytes; it does not decode pose tracks, input timing or simulation
   states. Capture controlled self-recorded runs and investigate that format as a
   new evidence source. Do not call these files deterministic input replays before
   decoding them.
4. **Progression and scoring observations.** Stat event mappings distinguish XP,
   levels, playtime, unlock bitfields and challenge score direction. Upstream says
   these were derived from snapshot/event differences. This can identify observable
   outputs and commit events; it does not provide the in-game trick-score formula.
5. **World/session boundaries.** Matchmaking uses world identifiers and world-cell
   criteria. These could label coarse experimental locations. They are not player
   coordinates or terrain geometry. Host/group migration is service behavior.
6. **Cloud-save isolation.** The service describes slot metadata, integrity checks
   and shared save storage between the two storefront versions. Payloads remain
   opaque and saves are not full scheduler/register checkpoints.
7. **Server plugin API.** Hooks cover HTTP, NEX calls and service events. This is a
   complementary service-mod interface, not an in-process animation/physics API.

## Sources inspected

- [Supported builds and readiness fingerprint](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/powder/launcher/game.py)
- [Process selection and readiness polling](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/powder/launcher/attach.py)
- [Native helper and upstream protection claims](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/native/hook_guard.c)
- [External helper implementation](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/native/armer.c)
- [Replay/entity-file storage](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/powder/server/transport/https/routes_ubi.py)
- [Statistics and challenge events](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/powder/server/services/stats.py)
- [World-cell matchmaking](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/powder/server/services/matchmaking.py)
- [Cloud saves](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/powder/server/services/cloudsaves.py)
- [Server plugin API](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/powder/server/plugins/api.py)
- [Capture-derived data-pack builder](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/powder/server/gamedata/build.py)
- [Readiness tests](https://github.com/SomeRandomNiko/powder/blob/00fdf2af7461ba0f83de7b14801f1b7d4b9924e8/tests/test_launcher.py)

## Boundaries and next experiment

The inspected project primarily reconstructs online services and startup support.
No snow-force equations, skeletal rig decoder, animation graph or physics scheduler
reconstruction was found in the inspected modules. Its game-data pack is assembled
from network responses, not a decoder for the game's asset archives.

First restore the local ability to execute Intel programs; that failure precedes
any game hook. Then compare read-only readiness observations with our existing
startup milestones on this exact build. Separately, use controlled saved-ride
pairs to determine whether ghost payloads contain transforms, animations, inputs,
or compressed combinations. Keep payloads private and publish only format facts,
synthetic fixtures and verified distinctions. Do not deploy Powder's DNS,
certificate or native attachment setup merely to inspect its source.
