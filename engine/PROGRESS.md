
- Live invocation capture of the body connectivity refresh `18b8860`. A private
  registry-row swap on controller listener `18b8670` used no code patch or
  protection change, and was restored and drained in all 3 sessions. It
  observed 10,552 path A calls, all on empty +0x80 rings; 0 path B calls; and
  19,078 nonempty-ring event-0 calls, all priority-set and quiet 0 (no refresh).
  All 32 captured real invocations matched the Python chain: 64 of 64 stamp
  bytes predicted, 0 unattributed differing bytes, Unicorn 32 of 32.
  Selection, rebuild and retire were not reached in game. Receipt:
  `native/snow_host/pose_connectivity_live_invocation_validation.json`.
