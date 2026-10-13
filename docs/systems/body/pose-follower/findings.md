> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Trick motion, physical targets and angular assignment

The confirmed spin/flip path still ends at a procedural target matrix and a separate angular cache. This pass recovers a concrete physical pose follower and its final body-velocity assignments, but does not prove that the player trick target selects that follower for the main snow body. [Static, partial ownership join]

## New results

A selected physical-pose branch accepts an indexed body pointer, target translation, target quaternion, timestep and a force flag. Its equations are:

```text
targetCOM = targetTranslation + rotate(targetQuaternion, bodyLocalCOM)
linearRequested = (targetCOM - currentPhysicalCOM) / h

relative = normalize(targetQuaternion * inverse(currentQuaternion))
angle = 2 * acos(relative.w)
axis = (0,0,1) if relative is componentwise within epsilon of identity
       otherwise normalize(relative.xyz)
angularRequested = axis * angle / h

linearAssigned[i] = clamp(linearRequested[i], lowerLinear[i], upperLinear[i])
angularAssigned[i] = clamp(angularRequested[i], lowerAngular[i], upperAngular[i])
assign body linear velocity
assign body angular velocity, subject to body-kind/force gate
```

Quaternions use XYZW and Hamilton multiplication. The error multiplication order is target times inverse current. The rate is radians per supplied time unit. Translation and linear velocity retain the body's coordinate units; SI calibration is not established by this routine. The current orientation comes from the physical body basis, not a graph speed field. Axis names beyond XYZ depend on the transform convention and should not be renamed pitch, roll or spin without the player join. [Static formula]

The initializer installs per-component linear bounds of ±120 and angular bounds of ±100.53096771240234, float32 approximating 32π. These are defaults for this final setter path. The frozen image contains zeroed storage before initialization; using those zero values as runtime bounds would be wrong. This pass does not prove current caps or exclude later writers. [Static initializer]

The setter replaces angular velocity. It does not add an impulse, integrate a torque or divide by inertia. Its body-kind gate can suppress assignments; force bypasses that restriction and can request backend dispatch when a world exists. The caller's force argument is true only when its incoming flag equals one. [Static final consumer]

The newly joined consumer has a concrete body provenance: an indexed physical-pose loop supplies a selected body's pointer and a 32-byte target record containing translation and quaternion. A separate selected branch instead writes the body matrix and zeros both velocities. These branches establish physical target following, but the inspected target body is not joined to the player's main snow-body identity. [Static ownership boundary]

The helper has no local shortest-arc sign correction. Negating a quaternion can produce a different rate for the same orientation. It also has no local positive-timestep guard. Exact negative identity and invalid inputs are outside the portable receipt's domain. A higher caller may provide guards or sign continuity; this pass does not substitute them silently. [Static numerical boundary]

## Previously known, rechecked

The trick controller maps input into a proposal, including the ski X/Y exchange, applies acceptance and direction gates, saves intensity, optionally computes auxiliary Z boost, restores main-vector magnitude, then assembles heading and extra Z terms. It builds a procedural target pose, updates unsigned angular travel and publishes the target through its entity callback. Those stages were already documented.

The assembled vector is:

```text
assembled = rotateAroundZ(main, radians(heading))
assembled.z += auxiliaryZ + optionalExtraZ
history[i] += abs(dt) * assembled[i]^2 / length(assembled)
```

The history expression applies when the vector is non-negligible and its padding lane is zero. It attributes unsigned angular travel, not signed Euler orientation. Target basis rotations and the delayed response angle are procedural orientation outputs; graph publication is another store with its own gates and overrides. None of those facts alone proves the main body's physical angular rate. [Prior static results]

Normal landing correction already has a confirmed physical consumer: after its contact query succeeds and the runtime exists, it assigns a projected cached linear velocity and assigns zero angular velocity to the main body. The local trick reset clears specified rotation fields but leaves the auxiliary boost and published angular cache outside that block's ownership. Zero input or input release does not universally clear an accepted rotation. [Prior static lifecycle]

The separate recovered pose-drive path applies an angular impulse using orientation error, velocity error, acceleration error and a drive matrix. It is a different actuation mode from the direct-assignment follower recovered here. Complete constraint selection, solving and the connection to the main trick target remain open. [Prior static physics-pose result]

## Validation and limits

Fresh byte checks passed for 4,965 instruction spans in 24 exports against the required image hash. Eight offline formula checks passed, including noncommuting quaternion order, rate changes with timestep, saturation, local-COM transformation and quaternion-sign sensitivity. They are synthetic checks, not original-instruction execution or game parity. Exact proof sites, prior sources and object provenance are in [private/EVIDENCE.md](evidence.md).

Run36's recorded body angular velocities remain observations with uncontrolled input and clip state. No live experiment ran in this task. The decisive remaining join is the concrete consumer of the player's target-publication callback.
