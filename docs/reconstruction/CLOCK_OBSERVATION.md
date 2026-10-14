# Passive clock hierarchy observation

The [clock reader](../../engine/clock_observation.py) prepares the next original-game timing observation. It has synthetic transport tests, but has not yet been run against a live game. It never launches a process, attaches a debugger, sends input or writes memory.

## Static hierarchy connection

The inspected world constructor initializes three embedded clocks and passes each to a helper on the global root clock. The helper locks the child vector, searches for an existing identical pointer, and appends only when absent. The ordinary, alternate and third records are thus statically connected to the root's child collection. The shared updater later traverses this collection and recursively updates each child.

This closes the constructor-to-child-list link left open in the [driver policy](FRAME_CLOCK_POLICY.md). Runtime removal, re-registration, current membership and update cadence still require observation. A world lifecycle method searches this same collection and invokes another vector helper on a matching entry; its complete lifecycle semantics are not reconstructed here.

The timer-reading wrapper forwards to a helper that invokes an indirect API and returns its output counter. The frequency wrapper returns a cached global. Initialization derives the driver's divisor from that frequency using integer division by 1000. The imported API identity and actual frequency on Wine remain to be verified. None of these observations justifies assuming a particular native timer resolution on macOS.

## Reader contract

```python
capture_clocks(readv, image_base=current_base, world=current_world,
               guards=current_identity_guards)
```

The caller must acquire and validate the current process/player/world first, verify the supported image build, enforce read deadlines and own transport cleanup. `readv` accepts address/size pairs and returns exact byte strings. The reader rejects short reads and checks the external identity guards before acquisition and around the data sample.

It reads the current root and driver pointers plus timer divisor from build-specific globals. Root child-vector capacity uses the low 14 bits of its tagged capacity; its count is uint16. A conservative observation limit rejects capacities above 512. It reads the bounded pointer list and compares entries with the three embedded world clocks without dereferencing arbitrary child pointers. Root/driver globals, divisor, vector header, list contents and external identity guards are checked again before and after the scalar sample.

The result includes root/world interval bits and values, scales, flags, holds, history fields, tick counters, driver mode/rate/table storage and history storage. Nonfinite scalar bits are preserved with a null numeric value. Driver storage is reported without assuming its count/index is valid for simulation. Output contains membership indices rather than target addresses.

These are sequential reads. Matching guards do not pin object lifetimes, rule out address reuse or make the sample atomic. Even a matched interval does not prove the same update generation across objects. The result explicitly leaves scheduler stepping and policy-to-world execution unproved.

## Validation and next live capture

The [static receipt](clock_hierarchy_validation.json) records inspected span hashes and 1007 arithmetic checks of the frequency-divisor reduction.

Five synthetic transport tests cover complete membership, changed list contents at the final check, oversized lists, short reads, missing guards, signed fields and nonfinite bit preservation. The private passive runner now accepts a clock option alongside fresh player acquisition and scheduler observations. No live clock result is claimed in this pass.

The next bounded session should take several passive samples with no debugger. Establish live root membership, active mode, interval range, scales and holds before introducing another breakpoint. Then collect component selection flags and packet values in a separate bounded debugger window. An idle/movement comparison additionally needs an observed movement or active-clip signal.
