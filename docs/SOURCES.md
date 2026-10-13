# Source and resource references

## Analyzed build

The local analysis used an RVA-aligned Windows memory image named `analysis/steep-memory-image.exe`, with preferred base `0x140000000` and recorded SHA-256:

```text
32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2
```

That file is not distributed here. This is the identity of the analyzed image, not a download checksum for a Steam release or proof that another platform/update shares its layout. Reports may refer to the original `steep.exe`; neither executable is included.

## Resources

Resource IDs, GUIDs, type IDs, names, graph labels and documented paths are retained as research references. Historical neutral aliases such as `snow_game` and `Region_A` are disclosed rather than presented as original game names. No full asset catalog, extracted sample arrays, skeleton/animation payload, texture or geometry file is bundled.

The local `analysis/snow_game` package contained accompanying data and runnable mathematical references. This publication exports its prose chapters only. The original package's manifest and verification commands do not describe this repository's contents.

## Related references

- [Steep gameplay guide on the community wiki](https://steep.fandom.com/wiki/How_To_Play_Guide_For_Steep): a lead for controls and gameplay scenarios, not proof of internal implementation.
- [Ghidra](https://github.com/NationalSecurityAgency/ghidra): analysis tooling; this repository does not contain Ghidra or a project database.
- [Ghidra BSim documentation](https://ghidra.re/ghidra_docs/GhidraClass/BSim/README.html): possible future comparison of builds; no PS4 build comparison has been completed here.

There are no game download links in this repository.
