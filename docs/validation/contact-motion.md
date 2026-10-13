> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Moving rider capture

767 complete guarded groups over1959.2624ms. Body translation changed by60.7051 runtime units; maximum observed speed33.724 runtime units per time unit. Active bit26 stayed true and dispatch inhibit stayed0. Movement is independently supported by body telemetry, unlike the prior stationary-field captures.

The sample began with absence timer0.8452, zero immersion and skip1. At helper time524.7843ms, observed immersion returned to0.130915, absence reset to0 and skip cleared. At1394.8772ms, skip was1 again with absence0.042921 and zero immersion. Thus this run observed absence -> contact return -> absence. No video or synchronized input receipt establishes which particular jump/terrain collision these transitions represent.

All767 accepted groups agree with skip == (absence >= float32(.04)); no mismatch reproduced. This is sample agreement, not proof of exclusive writers, atomicity or same-substep execution.

The online event flag is false because that detector requires contact -> absence -> reset inside the window; this recording began in absence and did not include the second reset. Do not interpret event=false as no contact return: contact-audit.json records the actual transitions.

Cadence failed: p95 group interval14.7668ms, maximum40.8ms. No precise phase-order conclusion is supported. The next recorder revision should arm during verified movement, retain pre-trigger history and detect an initial absence-to-contact return without requiring a preceding contact sample. Improve buffering/transport cadence separately. User cue preceded fresh acquisition, so exact jump-to-capture alignment remains unproved.
