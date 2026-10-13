"""Command replay including fixed ticks, frame scheduling and checkpoint bases."""
import copy
from .runtime import Engine
from .assets import digest

def record(engine):
    return copy.deepcopy(dict(schema_version=2,scenario=engine.scenario,scenario_hash=digest(engine.scenario),base=engine.replay_base,commands=engine.commands,final_tick=engine.state['tick'],expected_hash=engine.state_hash()))

def replay(recording):
    if recording.get('schema_version')!=2 or digest(recording['scenario'])!=recording['scenario_hash']:raise ValueError('Invalid replay scenario')
    engine=Engine(recording['scenario'])
    if recording.get('base'):
        if recording['base']['scenario_hash']!=recording['scenario_hash']:raise ValueError('Checkpoint/replay scenario mismatch')
        engine.restore(recording['base'])
    for command in recording['commands']:
        op=command['op']
        if op=='input':engine.set_input(command['actions'])
        elif op=='step':engine.step(command['count'])
        elif op=='advance':engine.advance(command['frame_dt'])
        elif op=='pause':engine.pause(command['value'])
        else:raise ValueError('Unknown replay operation')
    if engine.state['tick']!=recording['final_tick'] or engine.state_hash()!=recording['expected_hash']:raise ValueError('Replay state hash mismatch')
    return engine
