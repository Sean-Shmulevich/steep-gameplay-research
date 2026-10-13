> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Contact state and landing logic

Immersion measures how much of the selected gameplay hull lies within environmental fluid planes. Rock and ice can have those profiles too. It is not a snow-only signal or a universal grounded flag.

The environmental query chooses a profile for each cell or face. Clipped volume and the selected profile feed pressure and contact response. The game then updates separate timers for sufficient and insufficient immersion. A later summary step can clear immersion without revisiting those timers.

The actor refresh copies the insufficient-immersion timer's threshold result into a cached skip flag. Landing entry tests the timer itself. The cached skip and timer can therefore describe different update phases. Motion snapshot copying, physical body motion, landing entry and rendered pose are separate observations.

Three contact representations must stay separate:

- The per-plane fluid profile supplies physical coefficient curves and authored gameplay density.
- A retained dominant collision-mask key controls a low-bit eligibility test. It can survive an update with no new selected winner.
- A numeric nearby-surface query category filters landing direction replacement. A failed query can still overwrite the category.

A current material label requires a selected per-plane profile from a completed query, its update identity, and a verified resource-name mapping. A cached category or retained mask cannot provide that proof. A collision hit may also succeed without a fluid profile.

The ordinary landing path requires recent sufficient immersion and motion into the selected contact direction. It can replace that direction with an accepted nearby-surface result. It calculates alignment angle and normal motion magnitude, then a selected base-plus-scale response. Upright, grab and state conditions apply afterward. This is a partial physical transition path, not the complete crash decision or the animation clip selector.

Sample131 is useful precisely because the timer and cached flag disagree. Its short read interval does not make the sample atomic. A dense sequence around the next timer reset can test whether the mismatch persists across repeated reads or exists only at a read boundary.

The decoded weather and time-of-day settings establish authored controller and sky bindings. A connection to changing contact profiles or grip has not been demonstrated.
