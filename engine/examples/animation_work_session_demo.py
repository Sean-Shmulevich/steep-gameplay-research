"""Synthetic session demo with explicitly substituted host numerical services."""
import json
import math
from engine.animation_work_session import AnimationWorkSession


def main():
    session=AnimationWorkSession(
        bank=dict(records=[([8.,0.,0.,1.],[0.,0.,0.,1.])],parent_position=None,
                  parent_rotation=None,direct=True,flags=1<<26),
        work=dict(count=0,records=[],elapsed=0.,duration=0.,saved_flag=0,
                  saved_scalar_bits=0,saved_context_token=0,active_context_token=0),
        indices=[0],resolve_context=lambda _:None,
        reciprocal_sqrt=lambda n:1/math.sqrt(n),acos=math.acos,sin=math.sin)
    events=[session.request(1.),session.request(.75),session.advance(.25),session.advance(.75)]
    print(json.dumps(dict(synthetic=True,numerics='host math and exact RSQRT substitutes',
                         scheduler_executed=False,events=events,final=session.snapshot()),indent=2))


if __name__=='__main__':
    main()
