"""Bounded read-only collection for animation.get_cached_parent.

Authored experiment orchestration; native field contract is documented in
native/snow_host/README.md#cached-parent-and-callback-inspection. Raw rows belong
in private session storage. Only the aggregate summary is suitable for review
for publication. Identity brackets do not establish atomicity or pin lifetime.
"""
import math
import time


FLAGS = ('primary_present', 'current_present', 'banks_alias',
         'callback_storage_nonempty', 'forwarded_context_nonzero',
         'function_present', 'holder_present', 'holder_target_present',
         'holder_status_sign_bit', 'callback_eligible')
POSES = ('cached_parent', 'primary_parent', 'current_parent')


def _valid(row):
    replies = [row.get(k, {}) for k in ('player', 'observation', 'player_after')]
    if any(r.get('status') != 'completed' for r in replies):
        return None
    before, observation, after = [r.get('result', {}) for r in replies]
    identity = observation.get('identity')
    if identity is None or before.get('identity') != identity or after.get('identity') != identity:
        return None
    if observation.get('guards_matched') is not True:
        return None
    if any(type(observation.get(k)) is not bool for k in FLAGS):
        return None
    if type(observation.get('context_tag')) is not int or not 0 <= observation['context_tag'] <= 3:
        return None
    for name in POSES:
        pose = observation.get(name)
        present = name == 'cached_parent' or observation[name.replace('_parent', '_present')]
        if not present:
            if pose is not None:
                return None
        elif not isinstance(pose, list) or len(pose) != 8 or any(
                type(x) not in (int, float) or not math.isfinite(x) for x in pose):
            return None
    return observation


def summarize_cached_parent(capture):
    """Report changes only across consecutive, accepted, same-identity samples."""
    valid = [(row, _valid(row)) for row in capture['rows']]
    accepted = [(row, pose) for row, pose in valid if pose is not None]
    flag_changes = {key: 0 for key in FLAGS + ('context_tag',)}
    pose_changes = {key: 0 for key in POSES}
    pairs = 0
    for (r0, p0), (r1, p1) in zip(valid, valid[1:]):
        if p0 is None or p1 is None or r1['index'] != r0['index'] + 1 or p0['identity'] != p1['identity']:
            continue
        pairs += 1
        for key in flag_changes:
            flag_changes[key] += p0[key] != p1[key]
        for key in pose_changes:
            pose_changes[key] += p0[key] != p1[key]
    return dict(total_queries=len(valid), accepted_identity_brackets=len(accepted),
                rejected_queries=len(valid)-len(accepted), adjacent_same_identity_pairs=pairs,
                callback_eligible_samples=sum(p['callback_eligible'] for _, p in accepted),
                flag_change_counts=flag_changes, pose_change_counts=pose_changes,
                atomic_snapshot=False, lifetime_pinned=False, invocation_observed=False,
                writer_attribution_established=False, input_causality_established=False,
                safe_native_call_established=False, animation_writes=False)


def capture_cached_parent(client, samples=12, interval=.1):
    """Client must already be connected and bound; transport sets request timeout."""
    if type(samples) is not int or not 1 <= samples <= 32:
        raise ValueError('samples must be 1..32')
    if type(interval) not in (int, float) or not math.isfinite(interval) or not 0 <= interval <= 1:
        raise ValueError('interval must be finite and within 0..1 seconds')
    rows = []
    started = time.monotonic()
    for index in range(samples):
        if index:
            time.sleep(interval)
        begin = time.monotonic()
        wall_begin = time.time_ns()
        player = client.request('player.get')
        observation = client.request('animation.get_cached_parent')
        player_after = client.request('player.get')
        end = time.monotonic()
        rows.append(dict(index=index, elapsed_seconds=end-started,
                         request_span_seconds=end-begin, wall_begin_ns=wall_begin,
                         wall_end_ns=time.time_ns(), player=player,
                         observation=observation, player_after=player_after))
    result = dict(schema='cached-parent-host-capture-v1', rows=rows)
    result['summary'] = summarize_cached_parent(result)
    result['ok'] = result['summary']['accepted_identity_brackets'] > 0
    return result
