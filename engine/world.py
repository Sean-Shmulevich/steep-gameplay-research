"""Synthetic analytic terrain and explicit material queries. No extracted assets."""
import copy
import math
from .math3d import normalize, vector, finite

DEFAULT_MATERIAL=dict(name='synthetic_packed',density=600.,thickness=.12,normal_frequency=7.,tangent_frequency=.6,grip=1.)

class World:
    def __init__(self,description=None):
        d=copy.deepcopy(description or {})
        if not isinstance(d,dict):raise ValueError("World must be an object")
        if set(d)-{'slope','height','bumps','patches','obstacles','material'}:raise ValueError("Unknown world field")
        d.setdefault('slope',[-.12,0.]);d.setdefault('height',0.);d.setdefault('bumps',[]);d.setdefault('patches',[]);d.setdefault('obstacles',[])
        vector(d['slope'],2);finite([d['height']])
        d['material']=self.material(d.get('material',{}))
        for bump in d['bumps']:
            vector(bump['center'],2);finite([bump['height'],bump['radius']])
            if bump['radius']<=0:raise ValueError("Bump radius must be positive")
        for patch in d['patches']:
            bounds=vector(patch['bounds'],4)
            if bounds[0]>=bounds[2] or bounds[1]>=bounds[3]:raise ValueError("Invalid patch bounds")
            patch['material']=self.material(patch['material'])
        for o in d['obstacles']:
            vector(o['center'],2);finite([o['radius'],o['height']])
            if o['radius']<=0 or o['height']<=0:raise ValueError("Invalid obstacle")
        self._description=d
    @staticmethod
    def material(overrides):
        if not isinstance(overrides,dict) or set(overrides)-set(DEFAULT_MATERIAL):raise ValueError("Unknown material field")
        m={**DEFAULT_MATERIAL,**overrides}
        if not isinstance(m['name'],str):raise ValueError("Material name required")
        finite([v for k,v in m.items() if k!='name'])
        if any(m[k]<0 for k in m if k!='name'):raise ValueError("Negative material value")
        return m
    def to_dict(self):return copy.deepcopy(self._description)
    def sample(self,x,y):
        finite([x,y]);d=self._description;dx,dy=d['slope'];height=d['height']+dx*x+dy*y
        for bump in d['bumps']:
            u=x-bump['center'][0];v=y-bump['center'][1];radius=bump['radius'];b=bump['height']*math.exp(-(u*u+v*v)/(radius*radius))
            height+=b;dx-=2*u*b/(radius*radius);dy-=2*v*b/(radius*radius)
        material=d['material']
        for patch in d['patches']:
            a,b,c,e=patch['bounds']
            if a<=x<c and b<=y<e:material=patch['material']
        return dict(height=height,normal=normalize([-dx,-dy,1.]),material=copy.deepcopy(material),velocity=[0.,0.,0.])
    def sweep(self,start,end,radius=.2):
        # Designed swept vertical-cylinder collision; not original collision solver.
        hits=[];dx=end[0]-start[0];dy=end[1]-start[1];a=dx*dx+dy*dy
        for index,o in enumerate(self._description['obstacles']):
            ox=start[0]-o['center'][0];oy=start[1]-o['center'][1];rr=radius+o['radius'];c=ox*ox+oy*oy-rr*rr
            b=2*(ox*dx+oy*dy);discriminant=b*b-4*a*c
            if c<=0:t=0.
            elif a>1e-16 and discriminant>=0:t=(-b-math.sqrt(discriminant))/(2*a)
            else:continue
            if not 0<=t<=1:continue
            z=start[2]+t*(end[2]-start[2]);base=self.sample(*o['center'])['height']
            if not base-radius<=z<=base+o['height']+radius:continue
            point=[start[i]+t*(end[i]-start[i]) for i in range(3)]
            n=[point[0]-o['center'][0],point[1]-o['center'][1],0.]
            if math.hypot(*n[:2])<1e-10:n=[-dx,-dy,0.] if a>1e-16 else [1.,0.,0.]
            hits.append(dict(fraction=t,normal=normalize(n),point=point,obstacle=index))
        return min(hits,key=lambda h:h['fraction']) if hits else None
