"""Two-read shared frame-service placement; no selector stability assumption.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, retirement service joins frame path.
Site A's enclosing phase is not named here. The second is BeginGraphicFrame.
"""


def frame_service_placement(site_a_value, graphic_value):
    for value in (site_a_value, graphic_value):
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('selector samples must be uint8')
    calls=[]
    if site_a_value == 0:
        calls.append('site_a')
    if graphic_value != 0:
        calls.append('begin_graphic_frame')
    return dict(calls=calls, call_count=len(calls),
                predicate_stable=(site_a_value == 0) == (graphic_value == 0))
