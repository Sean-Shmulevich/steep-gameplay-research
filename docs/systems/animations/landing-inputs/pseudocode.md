> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Clip selection, playback and landing pose

The local assets provide one complete landing motion, a one-second male landing clip with 174 tracks. Direct ordinary sampling maps transforms onto 62 rider bones and leaves ten bones at their bind-local transforms. Parent motion still moves those ten bones in model space. The resource belongs to the corpus, but its identity does not appear in the rider graph catalog. Its motion can be previewed offline; its runtime selection is unproved.

Idle resources have metadata and authored graph records. One standing-idle resource owns eight graph outputs. The records identify resource and output identity, not the incoming state decision. Complete idle tracks are unavailable in the supplied pose package.

After a graph chooses a data node, the engine can replace that node's resource through a provider table. The playback instance then stores the selected resource and a permitted time segment. The segment defaults to the full resource duration and can use marker-derived start and end times. Reversed segment bounds return to the full duration. The active resource must therefore be observed after provider replacement.

Normalized phase, clip seconds and keyframe numbers are separate. For a resource of length T, a start phase p and forward phase travel d cover seconds T*p through T*(p+d). Bone tracks use an integer query computed by truncating the float32 product of seconds and 60. Root effective duration divides child duration by its source multiplier, with a one fallback for a near-zero multiplier. The producer of that multiplier and the installed playback-advance callback still need tracing.

Animation receives an absorption-distance scalar built from the current controller scalar and a selected threshold. If the special threshold is zero or the current value exceeds it, the producer selects the default threshold. The output is `max(threshold-current,0)`. Two authored graph records then map distance zero to scalar one and distance about 0.6 to scalar zero. Both records use the same range. Their consumers remain unresolved, so this scalar is not yet a documented landing blend weight or skeletal compression amount.

LandingForce, TimeToLand and AbsorbBoost also have explicit scalar publication paths. Their names do not establish their units or prove that a physical landing-quality classifier supplies them. Mode, Archetype and AnimationSet reach the graph through known bridges, but original sport labels and landing selection are still missing.

The generic blend node clamps negative child weights, normalizes their sum and visits active children in stored order. Each later child blends with `child_weight/accumulated_weight`. A channel mask can scale a global weight by an authored byte divided by 255. Transition duration prefers a valid override, then a nonnegative variable lookup, then a literal value. Applying those rules to a landing requires the actual selected child weights, mask and transition definition.

Procedural foot IK can change a sampled pose. Its established graph callback reaches contact fades, hip-height constraints and foot-on-slope corrections. The separate physical spring and physical target absorber do not by themselves identify skeletal targets. Landing-specific IK activation, equipment selection and the relation between the published absorption scalar and final bone writes remain open.
