"""Partial recovered frame entry with synthetic hierarchy commands.

Run: python3 -m engine.examples.begin_commands_probe
Evidence: ANIMATION_CONTEXT_RETIREMENT.md, BeginEngineFrame command binding.
No original game, native locks or complete engine graph is executed.
"""
import json
from engine.mixed_scheduler import MixedScheduler
from reference.hierarchy_commands import drain_hierarchy_commands


def run_probe(paused, *, graphics_overlap=False):
    if type(paused) is not bool or type(graphics_overlap) is not bool:raise ValueError('boolean branch selection required')
    seen=[];command_results=[]
    def commands(context,receiver):
        result=drain_hierarchy_commands(pending=0,deferred=1,
            record_targets=['synthetic-child'],entity_bytes={'synthetic-child':129},
            read_index=0,capacity=4)
        command_results.append(result);seen.append('commands')
    def branch(name):
        return lambda context,receiver:seen.append(name)
    definitions=[
        dict(id='BeginFrame',kind='callback',successors=['BeginEngineFrame']),
        dict(id='BeginEngineFrame',kind='callback',handler='commands',successors=['CheckEngineStop']),
        dict(id='CheckEngineStop',kind='conditional',condition=paused,
             successors=['UpdateWhileEngineIsPaused'],secondary=['UniverseLinkStart']),
        dict(id='UpdateWhileEngineIsPaused',kind='callback',handler='paused',successors=['ProbeEnd']),
        dict(id='UniverseLinkStart',kind='callback',handler='normal',successors=['ProbeEnd']),
        dict(id='ProbeEnd',kind='terminal')]
    if graphics_overlap:
        definitions[0]['successors'].append('BeginGraphicFrame')
        definitions.extend([
            dict(id='BeginGraphicFrame',kind='callback',successors=['GraphicFrame']),
            dict(id='GraphicFrame',kind='callback',successors=['EndGraphicFrame']),
            dict(id='EndGraphicFrame',kind='callback',successors=['ProbeEnd'])])
    handlers={key:dict(version='synthetic-v1',callback=callback) for key,callback in
              [('commands',commands),('paused',branch('paused_route')),('normal',branch('normal_route'))]}
    scheduler=MixedScheduler(definitions,handlers)
    scheduler.activate('BeginFrame');scheduler.submit('BeginFrame')
    root=scheduler.reserve('BeginFrame');scheduler.execute_callback(root);scheduler.finish_dispatch(root)
    graphic=None
    if graphics_overlap:
        entry=scheduler.reserve('BeginGraphicFrame');scheduler.execute_callback(entry);scheduler.finish_dispatch(entry)
        graphic=scheduler.reserve('GraphicFrame');scheduler.execute_callback(graphic)
    token=scheduler.reserve('BeginEngineFrame');scheduler.execute_callback(token)
    jobs=scheduler.snapshot()['jobs']
    before_finish=dict(commands_executed=len(command_results),
        begin_executions=jobs['BeginEngineFrame']['executions'],
        branch_holds=jobs['CheckEngineStop']['holds'],branch_requested=jobs['CheckEngineStop']['requested'])
    scheduler.finish_dispatch(token);scheduler.run_ready()
    overlap=None
    if graphics_overlap:
        jobs=scheduler.snapshot()['jobs']
        overlap=dict(graphic_executions=jobs['GraphicFrame']['executions'],
                     route_executed=any(x in seen for x in ('normal_route','paused_route')),
                     terminal_begins=jobs['ProbeEnd']['terminal_begins'])
        scheduler.finish_dispatch(graphic);scheduler.run_ready()
    return dict(graphics_overlap=overlap,scope='Partial recovered entry topology with synthetic bodies; ProbeEnd is authored. No native snapshot safety proof.',
                paused=paused,events=seen,before_dispatch_finish=before_finish,
                commands=command_results,completed=scheduler.snapshot()['jobs']['ProbeEnd']['terminal_begins']==1)


if __name__=='__main__':
    print(json.dumps([run_probe(False),run_probe(True),run_probe(False,graphics_overlap=True),run_probe(True,graphics_overlap=True)],indent=2))
