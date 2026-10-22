"""Local snow jump branch, using caller-evaluated compiled curve gains.

Evidence: docs/systems/snow/integration/CLIENT_GUIDE.txt and
CENTRAL_IMPULSE.md, 'Stateful jump consumer'. This is not a complete controller.
Curve selection, body locks, input ingestion and backend dispatch are external.
"""
from reference.central_impulse import f32, advance_preconsume_countdown


def jump_step(*, cached_factor, cooldown, elapsed_dt, air_time, base_factor,
              release_signal, coil_gain, depth_gain, speed_gain, gravity,
              combined_mass, configured_rider_mass, rider_present):
    """Return next scalar state and ordered central-impulse requests.

    Gains are already evaluated at release, depth and projected speed. Finite
    float32 inputs, positive gravity and a boolean rider flag are authored API
    validation. No clamp is added to the configured main-body mass split.
    """
    cached_factor = f32(cached_factor)
    cooldown = advance_preconsume_countdown(cooldown, elapsed_dt)
    if f32(air_time) > 0 or f32(base_factor) <= 0:
        return {'branch':'disabled', 'cached_factor':0., 'cooldown':0., 'submissions':()}
    if cooldown > 0:
        return {'branch':'cooldown', 'cached_factor':cached_factor, 'cooldown':cooldown, 'submissions':()}
    if f32(release_signal) <= 0:
        return {'branch':'no_release', 'cached_factor':0., 'cooldown':cooldown, 'submissions':()}
    gravity = f32(gravity)
    if gravity <= 0 or type(rider_present) is not bool:
        raise ValueError('positive gravity and boolean rider_present required')
    factor = f32(f32(f32(coil_gain) * f32(base_factor)) / gravity)
    factor = f32(f32(depth_gain) * factor)
    factor = f32(f32(speed_gain) * factor)
    rider_mass = f32(configured_rider_mass)
    requests = []
    if rider_present:
        requests.append({'body':'rider', 'impulse':(0.,0.,f32(factor*rider_mass)), 'force':True})
    main_mass = f32(f32(combined_mass)-rider_mass)
    requests.append({'body':'main', 'impulse':(0.,0.,f32(main_mass*factor)), 'force':True})
    return {'branch':'submit', 'cached_factor':factor, 'cooldown':f32(.333),
            'submissions':tuple(requests)}
