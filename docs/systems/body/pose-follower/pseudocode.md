> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Address-free partial motion flow

The controller's rotation, the procedural pose, the animation graph and the physical body are separate state stores. Preserve each one until its producer and consumer are joined.

```text
primary motion entry:
    install selected entry angular limit
    blend/snapshot input and initialize latches
    clear proposal, main angular motion, saved intensity and auxiliary boost

active vector rotation update:
    decode controller proposal with sport-axis remapping
    apply intensity/sign acceptance and direction lock
    if accepted, retain direction/intensity and optional mixed-axis Z boost
    restore main-vector magnitude from intensity and selected angular limit
    assemble heading-rotated vector plus extra Z and auxiliary Z
    update unsigned angular travel
    build procedural target basis with alignment and delayed tilt
    publish target matrix through owning entity callback
    # concrete main-body consumer remains unresolved

animation publication:
    refresh or retain angular cache according to its mode gates
    apply graph override and ordinary write guards
    publish angular and combined fields
    select/sample/blend clips through the authored graph
    # graph rate fields do not establish physical angular velocity

selected physical pose follower, separately confirmed:
    desiredCOM = targetTranslation + rotate(targetQ, localCOM)
    linearRate = (desiredCOM-currentCOM)/h
    errorQ = normalize(targetQ * inverse(currentQ))
    angularRate = axis(errorQ) * 2*acos(errorQ.w)/h
    clamp linear and angular components independently
    assign physical velocities with body-kind and force gates
    # indexed physical-pose body; active main snow-body selection is not proved

normal landing correction:
    evaluate contact candidate and landing policy
    if correction query succeeds and physical runtime exists:
        assign projected cached linear velocity
        assign zero physical angular velocity
        refresh selected runtime state and histories
    publish target, request successor state and apply local rotation reset
```

The physical follower uses a target error divided by the supplied timestep. If the same orientation error persists and the timestep halves, its requested rate doubles until a component hits its bound. The initializer supplies ±32π radians per time unit as each angular component's bound. This is not the selected trick limit or a sport-wide speed table.

A pose-drive impulse mode is also known. It computes a correction from orientation, velocity and acceleration errors, transforms that correction through a drive matrix, multiplies by the timestep and sends an angular impulse onward. A constraint solver is another possible physical consumer. These mechanisms should not share one invented acceleration or damping law.

Release and landing have different lifetimes. A rejected or absent new proposal can retain old angular state. Conditional landing correction explicitly zeros body angular velocity, while independent animation publication can retain or override graph speed fields. Visible turning after such a reset can therefore require a pose/clip explanation; it cannot be classified from appearance alone.

The pending join is the target-publication callback's concrete owner and downstream body. Until that is proved, a model should expose the physical follower as a selected mode with supplied targets, not automatically run it for every spin or flip.
