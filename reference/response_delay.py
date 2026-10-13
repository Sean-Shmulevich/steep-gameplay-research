"""Delay producer and its separate integrated-exponential response."""
import json
import math


def response_delay(config_scalar, saved_scalar, actor_scalar):
    if not all(math.isfinite(x) for x in (config_scalar,saved_scalar,actor_scalar)):
        raise ValueError('finite scalars required')
    total=config_scalar+saved_scalar
    if total<0:return 0.0
    # Native arithmetic can reach exceptional domains; no native fallback is claimed.
    if total==0 or actor_scalar==0 or config_scalar/total<=0:
        raise ValueError('logarithm/division domain is not defined by this portable helper')
    delay=-math.log(config_scalar/total)*config_scalar/actor_scalar
    return 0.0 if delay<0 else delay


def delayed_response(duration, delay, gain, tau):
    if tau<=0:raise ValueError('positive tau required')
    t=duration-delay
    return 0.0 if t<0 else -gain*(tau*math.expm1(-t/tau)+t)


def examples():
    delay=response_delay(2,2,4)
    return {'synthetic_delay':delay, 'negative_sum':response_delay(2,-3,4),
            'before_delay':delayed_response(delay-.1,delay,.01,.01),
            'after_delay':delayed_response(delay+.1,delay,.01,.01)}


if __name__=='__main__':print(json.dumps(examples(),indent=2))
