"""Self-contained camera equations for snow_game.

"""
import json,math,struct
F=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
A=lambda a,b:F(F(a)+F(b)); M=lambda a,b:F(F(a)*F(b)); S=lambda a,b:F(F(a)-F(b))
EPS=F(1e-5)
def spring(position,velocity,target,omega,dt,epsilon=1e-5):
 position,velocity,target,omega,dt=map(F,(position,velocity,target,omega,dt))
 if abs(omega)<=EPS:return target,velocity
 if abs(S(position,target))<epsilon and abs(velocity)<epsilon:return target,0.
 y=S(position,target);q=M(omega,dt)
 decay=F(1/A(A(A(1,q),M(M(.48,q),q)),M(M(M(.235,q),q),q)))
 temp=M(A(velocity,M(omega,y)),dt)
 return A(target,M(A(y,temp),decay)),M(S(velocity,M(omega,temp)),decay)
def asymmetric_spring(position,velocity,target,rising_frequency,falling_frequency,dt,epsilon=1e-5):
 """Choose rising frequency only when target is greater than current position."""
 omega=F(rising_frequency if F(target)>F(position) else falling_frequency)
 if abs(omega)<=EPS:return F(target),0.
 return spring(position,velocity,target,omega,dt,epsilon)

def vector_spring(position,velocity,target,omega,dt,epsilon=1e-5):
 """Four-lane filter with a combined norm settle gate."""
 p=list(map(F,position));v=list(map(F,velocity));t=list(map(F,target))
 if abs(F(omega))<=EPS:return t,v
 if math.sqrt(sum(S(a,b)**2 for a,b in zip(p,t)))<epsilon and math.sqrt(sum(a*a for a in v))<epsilon:
  return t,[0.]*len(v)
 # Disable scalar settle: this routine's gate belongs to the combined vector.
 pairs=[spring(a,b,c,omega,dt,epsilon=-1) for a,b,c in zip(p,v,t)]
 return [a for a,b in pairs],[b for a,b in pairs]

def angle_wrap(a):
 # Mathematical version of[-pi,+pi] reduction; float32 boundarydetails differ.
 while a>math.pi:a-=2*math.pi
 while a<-math.pi:a+=2*math.pi
 return a

def distance_scaled_spring(position,velocity,target,damping_factor,frequency_multiplier,
                           elapsed,smoothed_anchor_speed,normal_speed,minimum_speed,
                           epsilon=1e-5,current_time=1.,angular=False):
 """Local scalar update; caller provides already-smoothed anchor speed.
 elapsed/current_time are clock units; speed is displacement per clock unit.
 normal_speed/minimum_speed are serialized names, not physical rider speed.
 """
 position,velocity,target,damping_factor,frequency_multiplier,elapsed,smoothed_anchor_speed,normal_speed,minimum_speed=map(F,(position,velocity,target,damping_factor,frequency_multiplier,elapsed,smoothed_anchor_speed,normal_speed,minimum_speed))
 speed=max(smoothed_anchor_speed,minimum_speed) if abs(F(current_time))>EPS else 0.
 fraction=F(speed/normal_speed) if abs(normal_speed)>EPS else 1.
 fraction=min(fraction,1.) # No lower zero clamp in this local routine.
 if abs(fraction)<=EPS:velocity=0.
 effective_dt=M(elapsed,fraction)
 if abs(damping_factor)<=EPS:return target,velocity
 if abs(frequency_multiplier)<=EPS or abs(effective_dt)<=EPS:return position,velocity
 omega=M(damping_factor,frequency_multiplier)
 if angular:
  y=F(angle_wrap(S(position,target)))
  if abs(S(position,target))<epsilon and abs(velocity)<epsilon:return target,0.
  # The machine gate tests raw position error, then the integrator uses wrapped y.
  q=M(omega,effective_dt)
  decay=F(1/A(A(A(1,q),M(M(.48,q),q)),M(M(M(.235,q),q),q)))
  temp=M(A(velocity,M(omega,y)),effective_dt)
  p=A(target,M(A(y,temp),decay));v=M(S(velocity,M(omega,temp)),decay)
  return F(angle_wrap(p)),v
 return spring(position,velocity,target,omega,effective_dt,epsilon)

def anchor_speed(current_anchor,previous_anchor,elapsed,gain=1.):
 """Anchor rate producer; all four vector lanes contribute to the norm."""
 return math.sqrt(sum((a-b)**2 for a,b in zip(current_anchor,previous_anchor)))/elapsed*max(0,min(1,gain)) if abs(elapsed)>EPS else 0.

def camera_angle_conversion(angle,mode,conversion_ratio=None):
 """Confirmed local conversion using the current renderer aspect cache."""
 angle=F(angle)
 if mode in (1, 'Horizontal') and conversion_ratio is not None:
  return F(2*F(math.atan(F(F(conversion_ratio)*F(math.tan(M(angle,.5)))))))
 return angle

def select_camera(node,owner,excluded,selected=None):
 """Matches the recursive ordered-child selector's shared output semantics."""
 if not node['enabled']:return selected
 selected=node
 if node.get('search_children',True):
  for child in node.get('children',[]):
   condition=child.get('condition')
   if child['enabled'] and (condition is None or not child.get('condition_active',True) or condition(owner)):
    selected=select_camera(child,owner,excluded,selected)
    if selected is None or selected['name'] not in excluded:return selected
    selected=None
 return selected

def perspective_projection(vertical_angle,aspect,near,far,crop=(0.,0.,1.,1.)):
 """Documented renderer matrix, row-major storage, conventional column names."""
 x,y,w,h=crop
 half=math.tan(vertical_angle/2)*near
 left=2*(x-.5)*half*aspect;right=2*(x+w-.5)*half*aspect
 top=-2*(y-.5)*half;bottom=-2*(y+h-.5)*half
 return [[2*near/(right-left),0,0,0],
         [0,2*near/(top-bottom),0,0],
         [(right+left)/(right-left),(top+bottom)/(top-bottom),far/(near-far),-1],
         [0,0,near*far/(near-far),0]]

def aspect_preserving_angle(vertical_angle,actual_aspect,reference_aspect):
 return 2*math.atan(math.tan(vertical_angle/2)*reference_aspect/actual_aspect) if actual_aspect<reference_aspect else vertical_angle


def boolean_rule(children,operation="AND"):
    """children are {enabled, value}; disabled children are skipped."""
    if not children:return False
    active=[bool(c['value']) for c in children if c.get('enabled',True)]
    if operation=="AND":return all(active)
    if operation=="OR":return any(active)
    return False

class DelayGate:
    """Continuous-true gate. Ticks have the observed 30000-per-time-unit scale."""
    def __init__(self,delay_seconds):
        self.delay_ticks=int(F(F(delay_seconds)*F(30000)))
        self.started=False
        self.deadline_ticks=0
    def update(self,any_child_true,now_ticks):
        if not any_child_true:
            self.started=False;self.deadline_ticks=now_ticks
            return False
        if not self.started:
            self.started=True;self.deadline_ticks=now_ticks+self.delay_ticks
            return False
        return now_ticks>=self.deadline_ticks


def action_camera_eligible(first_action_camera_override,second_action_camera_override,action_camera_menu_block,action_camera_item_block):
    return (first_action_camera_override or second_action_camera_override) and not action_camera_menu_block and not action_camera_item_block

def paraglide_eligible(delay_gate,now_ticks,paraglide_exit_guard,paraglide_follow_state,
                        paraglide_discipline,automatic_camera_override):
    delayed=delay_gate.update(not paraglide_exit_guard,now_ticks)
    return delayed and paraglide_follow_state and paraglide_discipline and automatic_camera_override


def interactive_angle_update(current_angle,input_rate,dt,lower_inverse_limit,
                              upper_inverse_limit,input_active=True,absolute_override=None):
    """An absolute override takes priority. Bounds are inverse serialized limits."""
    if absolute_override is not None and absolute_override>=0:return F(absolute_override)
    if not input_active:return F(current_angle)
    lower=F(1/F(lower_inverse_limit));upper=F(1/F(upper_inverse_limit))
    candidate=A(current_angle,M(input_rate,dt))
    return F(min(max(candidate,lower),upper))


def examples():
    out={}
    out['spring_first_step']=spring(0,0,1,15,1/60)
    out['distance_speed_floor']=distance_scaled_spring(0,2,1,15,1,1/60,0,10,2)
    out['distance_at_normal_speed']=distance_scaled_spring(0,2,1,15,1,1/60,10,10,2)
    out['vertical_config_passthrough_deg']=math.degrees(camera_angle_conversion(math.pi/3,'Vertical',9/16))
    out['horizontal_config_conversion_given_height_over_width_deg']=math.degrees(camera_angle_conversion(math.pi/3,'Horizontal',9/16))
    out['projection_matrix']=perspective_projection(math.pi/3,16/9,.1,1000)
    out['action_camera_one_override']=action_camera_eligible(True,False,False,False)
    out['action_camera_menu_blocks']=action_camera_eligible(True,False,True,False)
    gate=DelayGate(2)
    out['delay_timeline']=[dict(ticks=t,eligible=gate.update(v,t)) for t,v in [(0,True),(30000,True),(59999,True),(60000,True),(61000,False),(62000,True),(122000,True)]]
    out['interactive_clamp']=interactive_angle_update(1.0,100,1/60,2,0.5)
    out['interactive_override']=interactive_angle_update(1,100,1/60,2,.5,absolute_override=.7)
    assert out['delay_timeline'][0]['eligible'] is False
    assert out['delay_timeline'][3]['eligible'] is True
    assert out['action_camera_one_override'] and not out['action_camera_menu_blocks']
    return out

if __name__=='__main__':print(json.dumps(examples(),indent=2))
