# Build and run the native mod host

The host, startup launcher, plugins, build-specific game adapter and observation
probe are now published as independently authored C source. A checkout can build
the native components without the private research workspace. You still need your
own compatible game installation and Windows or a working Wine environment.

## Build

Install a Windows x64 MinGW compiler and Python 3.9 or later. From the repository
root, choose an output directory outside the repository:

```sh
python3 scripts/build_snow_host.py --adapter steep --out /tmp/snow-host-steep
```

Use `--adapter fixture` for a synthetic host build with no game dependency. The
builder compiles the host DLL, startup launcher, checked loader, two sample
plugins and the separate snow-update observation DLL. It never starts the game.
The checked-in sources were compiled with MinGW using warnings as errors for both
adapters. No compiled game files are distributed.

## Start against your own installation

In a Windows command prompt, use absolute Windows paths:

```text
C:\mods\snow-host\startup_launcher.exe C:\Games\Steep\steep.exe C:\mods\snow-host\snow_host.dll 47017
```

Keep the `plugins` directory beside `snow_host.dll`. On Wine, invoke the launcher
through your configured Wine executable, and supply paths as seen by that Wine
prefix. This does not create a suitable graphics/prefix configuration for you.
The launcher starts the game normally, then loads and starts the host as soon as
the Windows loader is available. It is not an executable-entrypoint hook.

The host listens on loopback. The client implementation and CLI are in
`scripts/snow_host_client.py`; run it with `--help` for its current commands.
Start with `status` and reader commands before trying a mutation. The host
README documents command capabilities, leases and limitations. The standalone
launcher remains the game's parent until exit and has no research-session
five-minute watchdog. The workspace-only `run_late_load.py` automation adds that
watchdog and navigation, but still needs private Highball/control helpers.

## Compatibility and evidence

`steep_adapter.c` is tied to the analyzed image and contains fixed addresses,
short instruction signatures and object-link checks. The analyzed memory-image
hash is recorded in its header; the adapter does not calculate that full hash at
runtime. Passing short guards is not general compatibility proof. Do not rebase
addresses or disable checks to make another build bind.

Pause, step, resume, player reads and speed assignment have a documented live
acceptance receipt in this repository. This turn's publication build does not
repeat that gameplay test. Velocity assignment resets angular velocity; the new
spin-preserving impulse path is not installed in the native game yet.

`snow_update_probe.dll` is a separate experimental observation component. Do not
put it in `plugins`: it does not implement `SnowMod_Initialize`. Its synthetic
Windows fixture passes under Wine, and it now has explicit guarded slot install/restore entry points. Those entry
points have only been exercised against synthetic objects, not the live game. Its README explains configuration, capture close/drain and lifetime
requirements. Source availability does not turn it into a finished live hook.

Game assets, executable payloads, raw memory dumps, recordings, saves and local
credentials remain excluded. Build-specific offsets and our authored integration
source are included so another engineer can actually continue the loader work.
