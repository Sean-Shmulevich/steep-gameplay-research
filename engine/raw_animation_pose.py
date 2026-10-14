"""Caller-selected raw clip to rig pose adapter; no gameplay selection inference.

Contract: docs/reconstruction/RAW_ANIMATION_POSE.md. Payloads remain caller-owned.
"""
import copy
from .animation_container import parse_clip_body
from .animation_decoder import unpack_serialized_channel, registered_channel_decoder
from .animation_sampling import SampleState
from .asset_adapter import from_decoded
from .animation import _models

ROTATIONS=frozenset((0,9,10,11,12,13,14,15,16,17,21,22,23,24,25,26))
TRANSLATIONS=frozenset((27,28,29))


class RawClipPose:
    """Compile an explicit rig/clip pairing, then sample without mutable cache state.

    time and hint are separate inputs. The caller owns wrapping and gameplay
    selection. Returned cursors may be passed back; failures leave inputs intact.
    Unit scale applies to both bind and sampled translations, not rotations.
    """
    def __init__(self,body,rig,*,unit_scale):
        body=bytes(body);parsed=parse_clip_body(body)
        template={'name':'raw','duration':parsed['duration'],'tracks':[]}
        converted=from_decoded(rig,[template],unit_scale=unit_scale,looping={'raw':False})
        self.rig=converted['bundle']['rig'];self.duration=parsed['duration']
        self.unit_scale=unit_scale;self.channels=[];self.targets=[]
        mapping={b['binding_id']:i for i,b in enumerate(self.rig['bones'])}
        claimed=set();unbound=[];auxiliary=[]
        for track in parsed['tracks']:
            if 'shared_track_reference' in track:
                raise ValueError('shared-track resolution required before pose sampling')
            codec=track['codec'];index=track['track_number']
            channel=unpack_serialized_channel(body,track['serialized_start'])
            field='translation' if codec in TRANSLATIONS else 'quaternion_xyzw' if codec in ROTATIONS else None
            bone=mapping.get(track['binding_hash'])
            target=None
            if field is None:auxiliary.append(index)
            elif bone is None:unbound.append(index)
            else:
                target=(bone,field)
                if target in claimed:raise ValueError('duplicate bound pose component')
                claimed.add(target)
            self.targets.append(target)
            self.channels.append((codec,channel['payload'],4 if codec in (39,40,41,54) else 8 if codec==66 else 16))
        self.diagnostics={'unbound_transform_tracks':unbound,'auxiliary_tracks':auxiliary,
                          'bound_components':len(claimed),'root_motion':'not applied',
                          'rig_selection':'explicit caller pairing','orientation_mapping':'identity only'}

    def sample(self,time,hint,*,cursors=None):
        if cursors is None:cursors=[-1]*len(self.channels)
        if len(cursors)!=len(self.channels):raise ValueError('cursor count mismatch')
        local=[copy.deepcopy(b['local_bind']) for b in self.rig['bones']]
        next_cursors=[];auxiliary=[]
        for i,((codec,payload,width),target,cursor) in enumerate(zip(self.channels,self.targets,cursors)):
            state=SampleState(hint,cursor);value=[]
            registered_channel_decoder(codec,payload,width,time,value,state)
            next_cursors.append(state.cursor)
            if target is not None:
                bone,field=target
                local[bone][field]=[v*self.unit_scale for v in value[:3]] if field=='translation' else value
            elif i in self.diagnostics['auxiliary_tracks']:
                auxiliary.append({'track':i,'encoding':codec,'value':value})
        return {'local_pose':local,'model_pose':_models(self.rig['bones'],local),
                'cursors':next_cursors,'auxiliary':auxiliary,'diagnostics':copy.deepcopy(self.diagnostics)}

    def engine_bundle(self,*,name,loop):
        """Create caller-private JSON resources for graph clocks/checkpoints.

        Auxiliary/unbound payloads stay in this adapter; the engine bundle carries
        only bound pose components and diagnostics. No file is written here.
        """
        if not isinstance(name,str) or not name or type(loop) is not bool:
            raise ValueError('explicit clip name and boolean loop required')
        channels={}
        for (codec,payload,width),target in zip(self.channels,self.targets):
            if target is None:continue
            bone,field=target;field='rotation' if field=='quaternion_xyzw' else field
            channels.setdefault(self.rig['bones'][bone]['name'],{})[field]={
                'encoding':codec,'payload_hex':payload.hex()}
        clip={'duration':self.duration,'loop':loop,'wrap_policy':'inclusive',
              'sampling_policy':'raw_channels','unit_scale':self.unit_scale,
              'channels':channels,'raw_diagnostics':copy.deepcopy(self.diagnostics)}
        return {'category':'asset-decoded','rig':copy.deepcopy(self.rig),'clips':{name:clip}}


def sample_component(spec,time,hint,kind,unit_scale):
    """Stateless sampling for serialized engine resources; fresh cursor each call."""
    if not isinstance(spec,dict) or set(spec)!={'encoding','payload_hex'}:
        raise ValueError('raw component needs encoding and payload_hex')
    codec=spec['encoding']
    allowed=TRANSLATIONS if kind=='translation' else ROTATIONS if kind=='rotation' else ()
    if type(codec) is not int or codec not in allowed:raise ValueError('raw component encoding/type mismatch')
    if not isinstance(spec['payload_hex'],str):raise ValueError('raw component payload must be hex')
    payload=bytes.fromhex(spec['payload_hex']);out=[]
    registered_channel_decoder(codec,payload,16,time,out,SampleState(hint))
    return [v*unit_scale for v in out[:3]] if kind=='translation' else out
