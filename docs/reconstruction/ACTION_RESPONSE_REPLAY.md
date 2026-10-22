# Directional response sequence inspector

Run the independent response chain without the original binary or a live game:

```sh
python3 -m engine.action_response_replay tests/fixtures/action_response_synthetic.json
```

The included file is a synthetic demonstration, not actual player tuning.
The command writes one JSON result to stdout after all events succeed. Errors
produce a diagnostic on stderr and exit status 2, with no partial result. It
does not launch, attach to, read or modify a game. Input files are limited to
8 MiB; sequences to 10,000 events, curves to 64 keys and retained state to eight
axis entries. These are inspector bounds, not inferred engine limits.

The public `replay_response(document)` function accepts the same schema and
returns detached JSON-compatible results without mutating its input. See
[implementation](../../engine/action_response_replay.py) and
[synthetic input](../../tests/fixtures/action_response_synthetic.json).

## Explicit input contract

All listed fields are required. Unknown fields are rejected to catch misspelled
settings instead of silently applying defaults.

- `schema`: `directional-response-v1`.
- `provenance`: caller-written nonempty label. The tool reports it as caller
  provenance, not verified evidence.
- `settings`: `duration`, `axis_mode`, `keys`, `input_bounds`, `output_bounds`.
  Bounds are two numbers or null. Each key supplies `x`, `y`, two-lane
  `incoming` and `outgoing` control points, and integer `mode`.
- `initial`: `clock` and `states`. Each state has uint32 `current`, uint32
  `remembered` and finite `timer`. The initial clock uses the ramp's converted
  clock scalar, not raw uint64 ticks.
- `events`: ordered records containing four-lane `vector`, `start_ticks`,
  `end_ticks`, `ramp_enabled`, `diagonal_enabled`, `global_gate` and
  `configuration_available`. Ticks are uint64 values or null for an absent
  clock object. Stage flags are bool or null; null uses the reconstructed
  chain's unresolved-configuration invocation rule. Internal gates are bool.

Each event represents one invocation, not necessarily one rendered frame or
physics substep. Both clock reads are explicit because the callback reads
twice. Tick inputs correspond to the selected clock's divided_ticks field;
the ramp converts them to a float32 scalar divided by 1,000. Units of seconds
are supported by the producer chain but live source selection remains open.
No elapsed time is invented from event count or wall time.

## Output and fidelity

For each event the result includes four output lanes and their exact 16-byte
hex representation, retained states and timer bytes, saved clock and bytes,
curve query phases, and each stage's invoked flag plus raw/working/published
bytes. Hex encoding is little endian and preserves signed zero. These
receipts allow comparison at the stage where a disagreement first appears.

The implementation composes the [validated directional chain](MOTION_MEMBERSHIP_OBSERVATION.md#composed-directional-response),
keyed curves and ordered root solver. It uses independent reconstructed
acos/cos, with Python sqrt/power rounded to float32. Those remaining math
choices are reported in every output. The finite-intermediate contract
rejects unsupported zero-divisor/non-finite paths; it does not repair them
silently. Inspecting a synthetic sequence does not validate actual tuning,
input-device queries, action arbitration or scheduler placement.

Keep any future private captured settings and raw capture files private. The
public fixture contains only authored test values. Captured parameter
provenance must be checked separately before interpreting replay as a match
to an observed player response.
