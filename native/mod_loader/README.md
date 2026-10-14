# Native module loader experiments

Status: the startup XInput proxy remains incompatible. An attachment-only DLL
was successfully loaded after gameplay started, while native stop mode held
world simulation. Pause/resume controls still run through the external tools;
there is no in-module control API or hotkey interface yet.

## Run the complete experiment

From the existing game/research workspace, run:

```sh
python3 steep-gameplay-research/scripts/run_late_load.py
```

Or from this repository:

```sh
python3 scripts/run_late_load.py --workspace /path/to/game-research-workspace
```

The command builds the probe, launches the original game, advances recognized
startup screens, verifies gameplay, pauses, loads the module, resumes, observes
20 seconds of simulation, and closes the test session. Leave the controls alone
while it runs. It keeps the original XInput DLL in place. The game launch has a
five-minute maximum and the existing memory watchdog. Ctrl+C requests cleanup.

Each invocation creates a new directory under
`runtime/mod-loader/sessions/` in the workspace. Its `result.json` records the
experiment outcome, original DLL hash check, settings restoration and bottle
shutdown. Stage logs and private evidence stay in that directory. A failed or
unrecognized startup screen stops the experiment instead of loading blindly.

Check prerequisites without starting the game:

```sh
python3 steep-gameplay-research/scripts/run_late_load.py --check
```

This command targets the **already configured local research workspace**.
A public checkout alone is not enough: it needs the owned game, configured
Highball research bottle, MinGW-w64, and the prior local startup, identity,
sampling and native pause helpers. The preflight lists missing files and
refuses a changed original XInput DLL. The local bounded launcher must support
`--native-xinput` and `--result-dir`. Those private environment dependencies,
generated binaries, game files and raw captures are not published here.

The workspace lock prevents two copies of this runner from overlapping. An
already active research bottle is refused. Normal shutdown uses the bounded
launcher's restoration path; a failed watchdog has a guarded backup-restoration
path. This is experimental automation, not a portable installer or a guarantee
of recovery from host termination or power loss.

## Late-load proof

The successful sequence kept the original XInput DLL intact:

1. Reach the gameplay HUD and verify that world Step is advancing.
2. Enter the engine's previously validated native stop mode.
3. Verify Step is held while EndFrame continues.
4. Start a guarded remote thread at the target's LoadLibraryW entry, passing
   only a writable allocation containing the diagnostic DLL's path.
5. Verify the new module in the target module list and its attachment marker.
6. Leave native stop mode and verify Step advances again.

In this session, Step remained at 11084 across the paused observations and
the load, while EndFrame advanced from 11112 to 11172. After resume, Step
advanced through 11330, 11397 and 11585. The module marker matched the process
ID, creation time and full-width module base reported by enumeration. A later
20-second check recorded advancing Step values at all five samples, ordinary
mode throughout, and a visible gameplay HUD. The test session was then closed
intentionally and temporary launch settings were restored.

This proves late loading worked in this tested session. It does not explain
why startup replacement is rejected, prove long-term stability, establish
deterministic replay, or demonstrate a full mod API. No debugger was attached
and no game instruction bytes were patched in this experiment.

### Sources and guards

- `late_probe.c`: attachment-only module. Writes a small binary marker next
  to itself and returns. It installs no hooks or background threads.
- `load_probe.c`: checks process name and creation time; resolves the loader
  through the actual containing module and verifies 16 remote entry bytes
  against the local entry before creating the remote thread. It accepts only
  the diagnostic DLL filename and refuses a second load when already present.
- `late_fixture.c`: disposable process for validating loading and guards.

The fixture rejected a wrong creation time, accepted the correct identity,
matched the attachment marker, remained alive after loading, and exited
normally. A thread wait timeout leaves its path buffer allocated until process
exit rather than freeing memory the loader might still use. The helper does
not terminate a timed-out thread. It verifies the full module base through
enumeration rather than treating a 32-bit thread exit code as a 64-bit handle.

The local orchestration restores pause state on failure and bounds game
lifetime. Those controls remain version-specific external tools; the generic
load helper does not itself pause or resume the game.

Build from this directory with MinGW-w64:

```sh
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -shared -nostdlib -Wl,--entry,LoaderEntry -o late_probe.dll late_probe.c -lkernel32
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -municode -o load_probe.exe load_probe.c
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -o late_fixture.exe late_fixture.c
```

The loader arguments are the fresh Windows PID, its creation FILETIME in hex,
and the absolute Windows path to `late_probe.dll`. Running a load experiment
requires explicit authorization; these build instructions do not authorize
targeting a process. Generated binaries and markers remain outside the public
source package.

The complete command passed a live run on 2026-10-14, including the 20-second
observation, original-DLL hash check, settings restoration and bottle shutdown.
Seven runner guard tests and the full 646-test repository suite passed. See the
[sanitized validation summary](validation.json). These observations establish
this tested session, not general loader stability.

## Startup proxy contract

The proxy preserves the inspected local XInput DLL's 12 exports, including
ordinals 100–103. It forwards them to `snow_xinput_original.dll` and appends
an attach message to `snow_mod_loader.log` beside itself. The only new behavior
is this log write. No game memory writes, hooks, pause commands, or worker
threads are implemented. Export compatibility is specific to the inspected
DLL; check another installation before using it.

This is independently written loader scaffolding. The pause/step work it may
eventually expose is described in
[Native stop mode](../../docs/reconstruction/NATIVE_STOP_MODE.md).

## Build

With MinGW-w64, from this directory:

```sh
x86_64-w64-mingw32-gcc -std=c11 -Wall -Wextra -Werror -O2 -shared -nostdlib -Wl,--entry,LoaderEntry -o XINPUT1_3.dll proxy.c xinput.def -lkernel32
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -o smoke.exe smoke.c
```

Generated binaries and the original DLL are not distributed here. Back up and
hash the original before installing anything. The original must be available
beside the proxy as `snow_xinput_original.dll`. Restore the original after a
failed test; do not overwrite an unrecognized existing modification.

The smoke executable takes the absolute Windows path of the proxy. It loads
the library and resolves each required ordinal. This checks resolution, not
the behavior of every forwarded function.

## Observations, 2026-10-14

- The compiler produced a PE64 DLL importing only KERNEL32.
- Without an explicit override, the Wine smoke test did not run our entry
  point and ordinal 101 was unavailable.
- With `WINEDLLOVERRIDES=xinput1_3=n`, the smoke test logged attachment and
  resolved all 12 exports.
- Under the same native override, Wine's game-load trace identified both the
  proxy and renamed original as native modules. The attach message appeared.
  The game nevertheless exited before displaying a window, reporting exit 0.
- A comparison using the restored original DLL and the same renderer/native
  override progressed into visible game startup screens.

This isolates a proxy-configuration compatibility problem, but does not
identify its cause. Anti-tamper rejection is unproven. Module identity,
forwarding behavior, initialization order and other startup dependencies
remain candidates. Neither successful library loading nor export resolution
establishes that gameplay accepts the proxy.

## Follow-up isolation tests

The empty-entry variant (`empty.c`) contains only an entry point returning
TRUE. With the same export forwarders, it also exited before a game window.
This rules out our attach-log write and DisableThreadLibraryCalls as necessary
causes of the observed failure.

The inspected executable's static import table contains one XInput import:
ordinal 3, XInputSetState. Dynamic resolution of additional functions remains
possible. The original DLL has no TLS directory. Its entry point calls CRT
initialization and its exported DllMain, whose attach branch calls an internal
initialization routine. No filename check was established by this limited
inspection; that is not proof that none exists elsewhere.

`trace.c` replaces ordinal 3 with a typed wrapper and forwards other exports.
It logs entry/return for at most 16 calls and preserves GetLastError across
logging. The original is an explicit import dependency in this variant.
The game wrote the proxy attach message, then exited without a SetState entry
message. An isolated invocation of the same wrapper did log both entry and
return and returned 1167, verifying that the trace path works. This narrows the observation to startup before this wrapper runs;
it does not exclude other dynamically resolved calls.

An isolated call with user index 0 and both vibration motors zero returned
1167 (ERROR_DEVICE_NOT_CONNECTED) from both the original filename and the
renamed original. Renaming therefore does not universally prevent loading or
this API call. Game-specific module checks and initialization dependencies
remain unresolved. A repeated restored-original game launch reached the startup
warning screen, confirming the baseline again.

Build the diagnostic variants from this directory:

```sh
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -shared -nostdlib -Wl,--entry,LoaderEntry -o empty.dll empty.c xinput.def -lkernel32
x86_64-w64-mingw32-dlltool -d original-import.def -l original.a
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -shared -nostdlib -Wl,--entry,LoaderEntry -o trace.dll trace.c trace.def original.a -lkernel32
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -o call-smoke.exe call-smoke.c
```

The call smoke test takes an absolute Windows DLL path. It requests zero
vibration, reports the result, and exits. It does not validate controller
input, gameplay, or every XInput function.

## Next gate

### Exit-path comparison

Two filtered Wine relay traces of the empty proxy recorded a call from the
game to TerminateProcess with the current-process pseudo-handle and exit code
zero. Both recorded the same game-image return address. The call proceeded
through kernelbase to NtTerminateProcess. This establishes explicit
self-termination, rather than inferring a clean launch from exit status zero.
It does not establish the condition that triggered termination or prove
anti-tamper rejection.

An original-DLL control with the same exit-API filter reached a visible
startup screen and ran until the 60-second watchdog stopped it. No matching
TerminateProcess call appeared in that control trace. Launcher-process exits
were distinguished from the game thread's termination call.

A second proxy trace added selected DLL lookup APIs. It recorded game-origin
GetModuleHandleA calls naming the renamed original before termination. The
last observed lookup operations also included ordinary runtime initialization;
their proximity to termination is not proof of causation. Both DLL attach
routines returned success.

The recorded return address lies in a packed image region without raw code in
the on-disk executable. The prior memory image did not provide a reliable
matching call instruction at that boundary. Treat this as a live trace anchor,
not a decoded conditional branch or a patch location.

The traces required no debugger attachment. Wine's
[relay implementation](https://github.com/wine-mirror/wine/blob/wine-10.0/dlls/ntdll/relay.c)
documents the include-list mechanism used here. Exit-only logging selected
ExitProcess, RtlExitUserProcess, TerminateProcess and NtTerminateProcess.
Local trials restored the previous registry section and original DLL and
enforced a 16 MiB diagnostic-log stop threshold. The three retained logs were
approximately 193 KB, 808 KB and 489 KB, respectively. Raw logs remain private.

### Remaining work

#### Host debugger capture boundary

A new bounded LLDB recorder passed a disposable Windows fixture: one hardware
breakpoint at TerminateProcess, unchanged entry bytes, expected exit argument
73, clean detach and fixture exit 73. It collects registers, at most 1 KiB of
stack and four small code windows. Stack words are only candidate code
addresses, not a validated unwind.

Game tests used a diagnostic proxy with a temporary 20-second attach delay.
A fresh process marker and function signature were checked before installing
the hardware breakpoint. Both attempts stopped first on a Mach
EXC_BREAKPOINT / EXC_I386_SGL at the same startup location. Neither reached
the exit breakpoint. The first batch stopped before its explicit cleanup
command; the second included a crash-stop cleanup command and recorded a
successful detach. The bounded launcher restored the original DLL afterward.

That exact startup exception also appears in uninstrumented original-DLL and
proxy logs. The register marker 0xDEADC0DE appears in both as well. Neither
observation independently demonstrates debugger detection or identifies the
proxy rejection condition.

Passing BSD SIGTRAP did not prevent the Mach stop. A fixture showed that
passing the owned breakpoint's trap through detach could itself disrupt
cleanup; restoring the normal policy after the owned hit restored the
expected fixture result. The installed Apple LLDB explicitly rejected
EXC_BREAKPOINT in platform.plugin.darwin.ignored-exceptions. That setting was
tested only on a disposable fixture and was not applied to another game run.
See the upstream [LLDB settings reference](https://lldb.llvm.org/use/settings.html)
for the general setting; support must be checked on the installed build.

The termination predicate remains uncaptured. A Wine-level observer that
preserves the game's exception handling is the next investigation, using
the existing unattached relay traces as controls. Do not treat the host
debugger's startup stop as the original exit decision.

For the startup-proxy route, identifying the termination predicate remains
open. The successful late-load route can proceed independently. The guarded
pause/step/resume operations now run in-process in the [Snow mod host](../snow_host/README.md);
the original note follows. Next port the
guarded pause/step/resume operations into the module, with a bounded command
interface and recovery timer. Preserve fresh engine identity checks and the
working original DLL. Neither native stepping nor module loading establishes
exact deterministic replay.
