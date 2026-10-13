"""Owned simulation transactions, checkpoints and inspection APIs."""
import copy
import math
from . import animation, domains, physics, scheduler, scoring, camera, rigid, graph, gameplay_jobs
from .assets import canonical, digest
from .input import validate
from .math3d import vector
from .world import World
from .trace import Trace
SPORTS=('snowboard','ski','walking','wingsuit','paraglider')
SCENARIO_KEYS={'schema_version','name','sport','world','body','physics','air','environment','scheduler','scoring','animation','resources','camera','physics_mode','rigid','trace','execution_mode'}

class Engine:
    def __init__(self, scenario=None):
        self.load_scenario(scenario or {})
    def load_scenario(self,scenario):
        scenario=copy.deepcopy(scenario)
        if not isinstance(scenario,dict) or set(scenario)-SCENARIO_KEYS:raise ValueError('Unknown scenario field')
        if scenario.get('schema_version',1)!=1:raise ValueError('Unsupported scenario version')
        canonical(scenario)
        sport=scenario.get('sport','snowboard')
        if sport not in SPORTS:raise ValueError('Unsupported sport')
        if scenario.get('physics_mode','point') not in ('point','rigid_cells'):raise ValueError('Unsupported physics mode')
        if scenario.get('physics_mode')=='rigid_cells' and sport not in ('snowboard','ski'):raise ValueError('Rigid cells require snowboard or ski')
        if scenario.get('execution_mode','direct') not in ('direct','mixed'):raise ValueError('Unsupported execution mode')
        trace=Trace(scenario.get('trace',{}).get('capacity',4096))
        world=World(scenario.get('world'))
        raw=scenario.get('body',{})
        if set(raw)-{'position','velocity','orientation','angular_velocity','mass','grounded'}:raise ValueError('Unknown body field')
        floor=world.sample(0,0)['height']
        body=dict(position=[0.,0.,floor+(50 if sport in SPORTS[-2:] else 0)],velocity=[5.,0.,0.],orientation=[0.,0.,0.,1.],angular_velocity=[0.,0.,0.],mass=26.,grounded=sport not in SPORTS[-2:])
        body.update(raw)
        if body['grounded'] and 'velocity' not in raw:
            normal=world.sample(*body['position'][:2])['normal'];vn=sum(v*n for v,n in zip(body['velocity'],normal))
            body['velocity']=[v-vn*n for v,n in zip(body['velocity'],normal)]
        self._validate_body(body)
        if 'resources' in scenario:
            bundle=scenario['resources']
            if set(bundle)!={'category','rig','clips'}:raise ValueError('Resource bundle needs category, rig, clips')
            from .assets import CATEGORIES
            if bundle['category'] not in CATEGORIES:raise ValueError('Unknown resource provenance')
            rig,clips=copy.deepcopy(bundle['rig']),copy.deepcopy(bundle['clips'])
        else:rig,clips=animation.default_resources()
        animation.validate_resources(rig,clips)
        pose=_evaluate_animation(rig,clips,{},0,body,validate({}),scenario.get('animation',{}))
        state=dict(tick=0,time=0.,body=body,environment={'time_of_day':12.,'weather_scalar':0.},scheduler={},scoring={},animation=pose['state'],pose=pose,controls=validate({}),input_generation=0,paused=False,diagnostics={},camera={})
        # Only publish a new scenario after validation succeeds.
        self.trace=trace;self.scenario=scenario;self.world=world;self.rig=rig;self.clips=clips;self.state=state
        self.journal=[];self.events=[];self.incidents=[];self.last_good=copy.deepcopy(state);self.commands=[];self.replay_base=None
        return self.snapshot()
    @staticmethod
    def _validate_body(b):
        for name in ('position','velocity','angular_velocity'):vector(b[name])
        q=vector(b['orientation'],4)
        if abs(sum(x*x for x in q)-1)>1e-4:raise ValueError('Body quaternion must be unit length')
        if isinstance(b['mass'],bool) or not isinstance(b['mass'],(int,float)) or not math.isfinite(b['mass']) or b['mass']<=0:raise ValueError('Positive body mass required')
        if type(b['grounded']) is not bool:raise ValueError('Grounded must be boolean')
    def snapshot(self):return copy.deepcopy(self.state)
    def state_hash(self):return digest(self.state)
    def checkpoint(self):
        return copy.deepcopy(dict(schema_version=1,scenario=self.scenario,scenario_hash=digest(self.scenario),state=self.state,journal=self.journal,events=self.events,trace=self.trace.snapshot()))
    def restore(self,checkpoint):
        checkpoint=copy.deepcopy(checkpoint)
        if checkpoint.get('schema_version')!=1 or checkpoint.get('scenario_hash')!=digest(checkpoint['scenario']):raise ValueError('Invalid checkpoint scenario hash')
        candidate=Engine(checkpoint['scenario']);state=checkpoint['state'];canonical(state);self._validate_body(state['body'])
        if set(state)!=set(candidate.state) or type(state['tick']) is not int or state['tick']<0 or state['time']<0:raise ValueError('Invalid checkpoint state')
        state['controls']=validate(state['controls'])
        _evaluate_animation(candidate.rig,candidate.clips,state['animation'],0,state['body'],state['controls'],candidate.scenario.get('animation',{}))
        if 'trace' in checkpoint:candidate.trace=Trace.restore(checkpoint['trace'])
        candidate.replay_base=copy.deepcopy(checkpoint);candidate.commands=[]
        candidate.state=state;candidate.journal=checkpoint['journal'];candidate.events=checkpoint['events'];candidate.last_good=copy.deepcopy(state)
        self.__dict__.update(candidate.__dict__)
        return self.snapshot()
    def replace_resources(self,bundle):
        """Validated local asset replacement; resets visual clocks, preserves physics.

        Starts a checkpoint-based replay segment with the new resource content.
        A complete original-game hot reload protocol is not claimed.
        """
        scenario=copy.deepcopy(self.scenario);scenario['resources']=copy.deepcopy(bundle)
        candidate=Engine(scenario)
        pose=_evaluate_animation(candidate.rig,candidate.clips,{},0,self.state['body'],self.state['controls'],scenario.get('animation',{}))
        self.scenario=scenario;self.rig=candidate.rig;self.clips=candidate.clips
        self.state['animation']=pose['state'];self.state['pose']=pose
        self.last_good=copy.deepcopy(self.state);self.replay_base=self.checkpoint();self.commands=[]
        return self.snapshot()
    def tune(self,changes):
        """Change explicit subsystem settings atomically and begin a replay segment."""
        allowed={'physics','air','rigid','camera','environment','scoring'}
        if not isinstance(changes,dict) or not changes or set(changes)-allowed:raise ValueError('Unsupported tuning section')
        scenario=copy.deepcopy(self.scenario)
        for section,values in changes.items():
            if not isinstance(values,dict):raise ValueError('Tuning section must be an object')
            scenario[section]={**scenario.get(section,{}),**copy.deepcopy(values)}
        # Validate on an isolated next-tick probe, never on the published engine.
        candidate=Engine(scenario);candidate.state=copy.deepcopy(self.state)
        candidate._tick(scenario.get('scheduler',{}).get('fixed_dt',1/120),scenario.get('scheduler',{}).get('fixed_dt',1/120))
        self.scenario=scenario;self.last_good=copy.deepcopy(self.state)
        self.replay_base=self.checkpoint();self.commands=[]
        return self.snapshot()
    def set_input(self,actions):
        actions=validate(actions)
        self.state['controls']=actions;self.state['input_generation']+=1
        self.journal.append(dict(tick=self.state['tick'],generation=self.state['input_generation'],actions=copy.deepcopy(actions)))
        self.commands.append(dict(op='input',actions=copy.deepcopy(actions)))
        self.trace.emit('input_committed',tick=self.state['tick'],generation=self.state['input_generation'],actions=actions)
    def pause(self,value=True):
        self.state['paused']=bool(value);self.commands.append(dict(op='pause',value=bool(value)))
    def recover(self):
        self.state=copy.deepcopy(self.last_good);self.state['paused']=False
        self.replay_base=self.checkpoint();self.commands=[]
        return self.snapshot()
    def _phase_physics(self,context):
        dt=context['dt'];before=context['before'];phase_fields=context['phase_fields']
        b=self.state['body'];start=list(b['position']);controls=self.state['controls'];sport=self.scenario.get('sport','snowboard')
        if sport in SPORTS[-2:]:
            # Designed air-sport landing lifecycle: remain landed until scenario reset.
            was_grounded=b['grounded']
            if was_grounded:
                info=dict(sport=sport,events=[],grounded=True,policy='synthetic landed hold until reset')
                b['velocity']=[0.,0.,0.];b['angular_velocity']=[0.,0.,0.]
            else:info=domains.step_air(b,controls,dt,dict(self.scenario.get('air',{}),sport=sport))
            floor=self.world.sample(*b['position'][:2])['height']
            if not was_grounded and b['position'][2]<=floor:
                impact=max(0.,-b['velocity'][2]);b['position'][2]=floor;b['velocity'][2]=0;b['grounded']=True;b.pop('air',None)
                info['events']=[dict(type='landing',quality='crash' if impact>8 else 'clean',impact_speed=impact,policy='synthetic')]
            elif not was_grounded:b['grounded']=False
        elif self.scenario.get('physics_mode')=='rigid_cells':info=rigid.step(b,controls,self.world,dt,dict(sport=sport,rigid=self.scenario.get('rigid',{})))
        else:info=physics.step(b,controls,self.world,dt,dict(sport=sport,physics=self.scenario.get('physics',{})))
        hit=self.world.sweep(start,b['position'])
        if hit:
            b['position']=[hit['point'][i]+hit['normal'][i]*.001 for i in range(3)]
            inward=sum(x*y for x,y in zip(b['velocity'],hit['normal']))
            if inward<0:b['velocity']=[v-inward*n for v,n in zip(b['velocity'],hit['normal'])]
            b.pop('air',None);info.setdefault('events',[]).append(dict(type='obstacle',obstacle=hit['obstacle'],policy='synthetic'))
        for event in info.get('events',[]):
            if event.get('type')=='landing':info['landing_clean']=event['quality']=='clean';info['crashed']=event['quality']=='crash'
        self.trace.emit('physics_complete',tick=before['tick'],body=b,events=info.get('events',[]),**phase_fields)
        context['info']=info
    def _phase_environment(self,context):
        context['env']=domains.step_environment(self.state['environment'],context['dt'],self.scenario.get('environment',{}))
    def _phase_scoring(self,context):
        context['score_events']=scoring.update(self.state['scoring'],self.state['body'],context['info'],context['dt'],self.scenario.get('scoring',{}))
    def _phase_animation(self,context):
        pose=_evaluate_animation(self.rig,self.clips,self.state['animation'],context['dt'],self.state['body'],self.state['controls'],self.scenario.get('animation',{}))
        self.state['animation']=pose['state'];self.state['pose']=pose
        self.trace.emit('animation_complete',tick=context['before']['tick'],animation_state=pose['state'],**context['phase_fields'])
    def _phase_camera(self,context):
        camera.update(self.state['camera'],self.state['body'],context['dt'],self.scenario.get('camera',{}))
    def _tick(self,dt,derivative_dt):
        before=copy.deepcopy(self.state);event_count=len(self.events)
        invocation=self.trace.attempted
        phase_fields=dict(invocation=invocation,frame_invocation=getattr(self,'_frame_invocation',None),input_generation=before['input_generation'])
        self.trace.emit('substep_enter',tick=before['tick'],elapsed_dt=dt,derivative_dt=derivative_dt,**phase_fields)
        try:
            context=dict(dt=dt,before=before,phase_fields=phase_fields)
            phases={name:getattr(self,'_phase_'+name) for name in gameplay_jobs.PHASES}
            if self.scenario.get('execution_mode','direct')=='mixed':
                gameplay_jobs.run(phases,context,self.trace,tick=before['tick'],**phase_fields)
            else:
                for phase in phases.values():phase(context)
            b=self.state['body'];info=context['info'];env=context['env'];score_events=context['score_events']
            self.state['tick']+=1;self.state['time']+=dt
            self.state['diagnostics']=dict(physics=info,environment=env,elapsed_dt=dt,derivative_dt=derivative_dt,derivative_dt_consumer='recorded; point controller currently consumes elapsed_dt only')
            self._validate_body(b);canonical(self.state)
            for event in info.get('events',[])+score_events:self.events.append(dict(event,tick=self.state['tick']))
            self.events=self.events[-4096:];self.last_good=copy.deepcopy(self.state)
            self.trace.emit('substep_committed',tick=self.state['tick'],state_hash=self.state_hash(),**phase_fields)
        except Exception as exc:
            self.state=before;self.state['paused']=True;self.events=self.events[:event_count]
            self.incidents.append(dict(tick=before['tick'],error=type(exc).__name__,message=str(exc)))
            self.incidents=self.incidents[-100:]
            self.trace.emit('substep_aborted',tick=before['tick'],error=type(exc).__name__,**phase_fields)
            raise
    def step(self,count=1):
        if type(count) is not int or not 0<=count<=100000:raise ValueError('Invalid step count')
        dt=self.scenario.get('scheduler',{}).get('fixed_dt',1/120)
        if not isinstance(dt,(int,float)) or not math.isfinite(dt) or not 0<dt<=.05:raise ValueError('Step dt must be in (0,.05]')
        completed=0
        try:
            for _ in range(count):
                if self.state['paused']:break
                self._tick(dt,dt);completed+=1
        finally:
            if completed:self.commands.append(dict(op='step',count=completed))
        return self.snapshot()
    def advance(self,frame_dt):
        if self.state['paused']:return self.snapshot()
        before=copy.deepcopy(self.state);events=copy.deepcopy(self.events);last_good=copy.deepcopy(self.last_good)
        self._frame_invocation=self.trace.attempted
        self.trace.emit('frame_enter',tick=before['tick'],frame_invocation=self._frame_invocation)
        try:
            steps=scheduler.schedule(self.state['scheduler'],frame_dt,self.scenario.get('scheduler',{}))
            self.trace.emit('frame_planned',tick=self.state['tick'],frame_dt=frame_dt,steps=steps,scheduler=self.state['scheduler'],frame_invocation=self._frame_invocation)
            if any(s['elapsed_dt']>.05 for s in steps):raise ValueError('Substep exceeds controller domain')
            for step in steps:self._tick(step['elapsed_dt'],step['derivative_dt'])
            self.commands.append(dict(op='advance',frame_dt=frame_dt))
            self.trace.emit('frame_committed',tick=self.state['tick'],frame_dt=frame_dt,state_hash=self.state_hash(),frame_invocation=self._frame_invocation)
        except Exception:
            self.state=before;self.events=events;self.last_good=last_good
            self.trace.emit('frame_aborted',tick=before['tick'],frame_dt=frame_dt if isinstance(frame_dt,(int,float)) and math.isfinite(frame_dt) else None,frame_invocation=self._frame_invocation)
            raise
        finally:
            self._frame_invocation=None
        return self.snapshot()


def _evaluate_animation(rig,clips,state,dt,body,controls,config):
    if 'graph' in config:
        values=dict(controls,grounded=body['grounded'],air=not body['grounded'],speed=math.sqrt(sum(v*v for v in body['velocity'])))
        result=graph.evaluate_pose(rig,clips,state.get('graph_state',{}),dt,config['graph'],values)
        result['state']={'graph_state':result['state']}
        return result
    request={}
    if 'transition' not in state and 'bend' in clips:
        request['clip']='bend' if controls['jump'] or not body['grounded'] else ('idle' if 'idle' in clips else next(iter(clips)))
    return animation.evaluate(rig,clips,state,dt,request)
