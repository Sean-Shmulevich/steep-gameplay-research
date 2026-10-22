"""Recovered immersion classification and contact/air clock update.

CENTRAL_IMPULSE.md, 'Contact clock before normal rebuilding'. Caller supplies
already computed immersion and elapsed interval; no collision query is invented.
"""
from reference.central_impulse import f32


def advance(immersion, air_time, contact_time, elapsed_dt):
    immersion,air_time,contact_time,dt=map(f32,(immersion,air_time,contact_time,elapsed_dt))
    if immersion>f32(.001):
        return {'immersion':immersion,'air_time':0.,'contact_time':f32(contact_time+dt)}
    return {'immersion':0.,'air_time':f32(air_time+dt),'contact_time':0.}
