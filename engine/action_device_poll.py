"""Recovered device-state polling helper semantics with explicit native-call inputs.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Input cache polling and copy order.
Callbacks model external device methods; no native process or device is touched.
"""


def poll_device_cache(previous_buffer, *, packet, device_present, get_state,
                      acquire, maximum_acquire_calls=64):
    """Return retained buffer, success and call counts, preserving failed writes.

    get_state(bytearray) may modify the initialized buffer and returns uint32
    HRESULT bits. acquire() returns uint32 HRESULT bits. The original retries
    0x8007001e without a bound; this inspector raises on a caller-defined bound.
    Reacquisition never reissues get_state within this invocation.
    """
    size=20 if packet else 256
    if type(packet) is not bool or type(device_present) is not bool:
        raise ValueError('explicit bool packet/device flags required')
    if not isinstance(previous_buffer,bytes) or len(previous_buffer)!=size:
        raise ValueError('exact previous cache bytes required')
    if type(maximum_acquire_calls) is not int or maximum_acquire_calls<1:
        raise ValueError('positive acquire-call limit required')
    data=bytearray(previous_buffer)
    data[:20 if packet else 8]=bytes(20 if packet else 8)
    def status(value):
        if type(value) is not int or not 0<=value<1<<32:raise ValueError('uint32 HRESULT bits required')
        return value
    reads=attempts=0;success=False
    if device_present:
        reads=1;result=status(get_state(data))
        if len(data)!=size:raise ValueError('device callback resized buffer')
        if result<0x80000000:success=True
        else:
            while True:
                if attempts>=maximum_acquire_calls:raise ValueError('reacquisition limit reached; original loop is unbounded')
                result=status(acquire());attempts+=1
                if result!=0x8007001e:break
    return dict(buffer=bytes(data),success=success,state_calls=reads,acquire_calls=attempts)
