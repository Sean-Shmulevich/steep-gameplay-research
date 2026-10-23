# Windows quick start

Use the Windows x64 starter ZIP from this repository's GitHub Releases, or build
from source below. The ZIP contains independently authored host/launcher/plugin
binaries, the Python client and checksums. It contains no game files. Native
Windows gameplay acceptance has not yet been performed; the documented live
acceptance runs used Wine on macOS.

## Use the starter ZIP

1. Extract the entire ZIP to a writable directory such as `C:\snow-host`.
   Keep the `plugins` directory beside `snow_host.dll`.
2. Install Python 3.10 or later for the command-line client. No compiler is needed
   to use the prebuilt package.
3. In PowerShell, launch your own compatible game installation:

```powershell
cd C:\snow-host
.\startup_launcher.exe "C:\Games\Steep\steep.exe" "C:\snow-host\snow_host.dll" 47017
```

Use a second PowerShell window to check the host:

```powershell
cd C:\snow-host
python .\snow_host_client.py status
```

The launcher loads the host after the Windows loader becomes available and stays
alive until the game exits. This is not an executable-entrypoint hook. A successful
connection and status response establish host connectivity; they do not establish
that the game adapter has passed its guards or that the player is ready.

The `step_logger.dll` and `player_logger.dll` files in `plugins` are host plugins.
The separate `snow_*_probe.dll` files are experimental components with different
interfaces; do not copy them into `plugins` or inject every DLL individually.
The new command-admission research sources are not integrated into this standard
host package. There is no arbitrary gameplay-mutation API in this release.

## If startup or binding fails

Keep `snow_startup.jsonl`, `snow_host.log`, the client status output and any error
message. Record the game executable's version and hash, game distribution, Windows
version, package revision and whether the game starts normally without the host.
Do not disable signature checks to make an unsupported build bind. The game
adapter uses fixed addresses and short signatures for the analyzed build; this
package does not promise compatibility with every Steam/Ubisoft executable.

The host listens on loopback port 47017. Ensure another instance is not already
using that port. Player reads can require an externally acquired player handle;
a missing player binding is not evidence that host injection failed.

## Build from source instead

Install Python 3.10+ and a MinGW-w64 **x64** GCC toolchain. From the repository root:

```powershell
python scripts/build_snow_host.py --adapter steep --cc gcc --out C:\snow-host
python scripts/snow_host_client.py --help
```

If your compiler is named `x86_64-w64-mingw32-gcc`, omit `--cc gcc`. Verify that
`gcc -dumpmachine` identifies an x86_64 Windows target, not 32-bit or Linux GCC.
The build output directory must be outside the repository. The builder never
starts the game. Use `--adapter fixture` for a synthetic host with no game binding.

Compiled DLLs are ignored by Git. Source is tracked; compiled starter packages
belong in Releases. `MANIFEST.json` in a starter ZIP identifies the source commit
and SHA-256 of each packaged file. A source build uses the client under `scripts`;
the starter ZIP places the standalone client at its root.
