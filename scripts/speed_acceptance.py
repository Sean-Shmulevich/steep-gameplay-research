"""Bounded speed acceptance with retained failure and recovery evidence.

capture/advance are supplied live I/O; no synthetic motion is inferred here.
"""
import math
import time


def steps_ok(result, count):
    return all(type(result.get(key)) is int and result[key] == count
               for key in ('completed', 'requested', 'exactly_one'))


def velocity3(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 3 or
            any(type(x) not in (int, float) or not math.isfinite(x) for x in value)):
        raise ValueError('Expected three finite velocity components')
    return value


def run_speed_acceptance(client, capture, advance, *, sleep=time.sleep):
    records = []
    if client.call('simulation.status').get('host_paused'):
        return dict(ok=False,trials=[],error='Existing host hold; trial refused')
    for delta in (-2.0, 2.0):
        trial = {'delta_speed': delta, 'eligibility': [], 'ok': False}
        records.append(trial)
        for attempt in range(6):
            try:
                client.call('simulation.pause', lease_ms=15000)
                before = client.call('player.get')
                trial['eligibility'].append(before)
                speed = math.sqrt(sum(x*x for x in velocity3(before['linear_velocity'])))
                spin = math.sqrt(sum(x*x for x in velocity3(before['angular_velocity'])))
                eligible = before['flags'] & 3 == 3 and speed >= 3 and spin <= .25 and (delta < 0 or speed < 60)
                if eligible:
                    capture(f'speed-{len(records)}-before')
                    trial['before'] = before
                    trial['adjust'] = client.call('player.adjust_speed', delta_speed=delta)
                    after = trial['adjust']['after']
                    target = max(0.0, speed + delta)
                    if delta > 0:
                        target = min(60.0, target)
                    trial['expected_speed_target'] = target
                    reported_target = trial['adjust']['speed_target']
                    if not math.isfinite(reported_target) or abs(reported_target - target) >= .001:
                        raise RuntimeError('Host target disagrees with requested speed change')
                    trial['readback_matches'] = all(abs(a - b * target / speed) < .001 for a,b in zip(velocity3(after['linear_velocity']), before['linear_velocity']))
                    if not trial['readback_matches']:
                        raise RuntimeError('Velocity readback disagrees with requested speed change')
                    trial['samples'] = []
                    for count in (1, 4):
                        step = client.call('simulation.step_world', count=count)
                        sample = client.call('player.get')
                        trial['samples'].append({'requested_count': count, 'step': step, 'player': sample})
                        if not steps_ok(step, count) or sample['identity'] != before['identity']:
                            raise RuntimeError('Step count or player identity changed during speed trial')
                    capture(f'speed-{len(records)}-after-5')
                    trial['ok'] = trial['readback_matches'] and all(steps_ok(x['step'], x['requested_count']) and x['player']['identity'] == before['identity'] for x in trial['samples'])
                    break
            except Exception as exc:
                trial['error']=str(exc)
                trial['ok']=False
                break
            finally:
                try:
                    trial.setdefault('resumes',[]).append(client.request('simulation.resume'))
                    if trial['resumes'][-1].get('status')!='completed':
                        trial['ok']=False
                        trial['recovery_error']='Resume did not complete'
                except Exception as exc:
                    trial['ok']=False
                    trial['recovery_error']=str(exc)
            if trial.get('recovery_error'):
                break
            # Only retry eligibility, never a mutation. Move forward briefly to
            # leave a stationary spawn; release input before the next hold.
            if attempt<5:
                try:
                    advance()
                    sleep(.5)
                except Exception as exc:
                    trial['error']=str(exc)
                    break
        if not trial['ok']:
            break
        sleep(.5)
    return {'ok': len(records) == 2 and all(x['ok'] for x in records), 'trials': records}
