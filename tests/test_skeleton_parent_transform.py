import json
from pathlib import Path
import unittest
from reference.skeleton_parent_transform import prepare_skeleton_parent_transform

class SkeletonParentTransformTests(unittest.TestCase):
    def test_joined_original_instruction_receipt(self):
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/refresh_parent_join_validation.json').read_text())
        self.assertEqual(report['cases'],64)
        seen=set()
        for row in report['rows']:
            result=prepare_skeleton_parent_transform(**row['inputs'])
            self.assertEqual(list(result['parent_position']),row['result']['parent_position'])
            self.assertEqual(list(result['parent_rotation']),row['result']['parent_rotation'])
            self.assertEqual(result['rotation_branch'],row['result']['rotation_branch'])
            self.assertEqual(result['parent_position'][3],0)
            seen.add((row['indirect'],row['swapped'],result['rotation_branch']))
        self.assertEqual(len(seen),16)
    def test_translation_w_cleared_without_scaling(self):
        matrix=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]
        result=prepare_skeleton_parent_transform(matrix,[4,5,6,27])
        self.assertEqual(result['parent_position'],(4,5,6,0))
        self.assertEqual(result['parent_rotation'],(0,0,0,1))
    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):prepare_skeleton_parent_transform([[1,0,0,0]]*2,[0]*4)
    def test_reset_parent_instruction_receipt(self):
        from reference.skeleton_parent_transform import prepare_reset_parent_transform
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/reset_parent_join_validation.json').read_text())
        self.assertEqual(report['cases'],64)
        for row in report['rows']:
            result=prepare_reset_parent_transform(**row['inputs'])
            self.assertEqual(list(result['parent_position']),row['result']['parent_position'])
            self.assertEqual(list(result['parent_rotation']),row['result']['parent_rotation'])
            self.assertEqual(result['parent_position'][3],1)
            self.assertEqual(row['events'].count('default_pose'),2)
            self.assertEqual(row['events'][-2:],['copy_mode5','unlock'])
    def test_configured_slot_instruction_receipt(self):
        from reference.skeleton_parent_transform import reset_configured_parent_slots
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/slot_parent_join_validation.json').read_text())
        self.assertEqual(report['cases'],80)
        for row in report['rows']:
            writes=[]
            parent=reset_configured_parent_slots(**row['inputs'],slots=row['slots'],
                reset_parent=lambda bank,pose:writes.append((bank,pose)))
            self.assertEqual([bank for bank,pose in writes],row['write_order'])
            self.assertEqual(list(parent['parent_position']),row['result']['parent_position'])
            self.assertEqual(list(parent['parent_rotation']),row['result']['parent_rotation'])
            self.assertTrue(all(pose is parent for bank,pose in writes))
    def test_slot_failure_stops_before_later_bank(self):
        from reference.skeleton_parent_transform import reset_configured_parent_slots
        writes=[]
        def fail(bank,pose):
            writes.append(bank)
            raise RuntimeError('supplied reset failed')
        with self.assertRaises(RuntimeError):
            reset_configured_parent_slots([[1,0,0,0],[0,1,0,0],[0,0,1,0]],
                [1,2,3,4],[0,1],fail)
        self.assertEqual(writes,[0])
    def test_volume_spawn_gate_instruction_receipt(self):
        from reference.skeleton_parent_transform import publish_volume_spawn_transform
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/spawn_parent_dispatch_validation.json').read_text())
        for row in report['rows']:
            state={'publication_state':row['initial_state']};events=[]
            def prepare(state):
                events.append('prepare');state['publication_state']=73
            def publish(state):
                events.extend(['publish','publish_state_'+str(state['publication_state'])])
            publish_volume_spawn_transform(state,prepare,publish)
            self.assertEqual(events,row['events'])
            self.assertEqual(state['publication_state'],row['final_state'])
    def test_volume_spawn_failed_service_does_not_clear(self):
        from reference.skeleton_parent_transform import publish_volume_spawn_transform
        state={'publication_state':9}
        def fail(state):raise RuntimeError('service failure')
        with self.assertRaises(RuntimeError):publish_volume_spawn_transform(state,fail,fail)
        self.assertEqual(state['publication_state'],9)
    def test_player_spawn_wrapper_instruction_receipt(self):
        from reference.skeleton_parent_transform import publish_player_spawn_transform
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/player_spawn_wrapper_validation.json').read_text())
        self.assertEqual(report['cases'],34)
        for row in report['rows']:
            state={'position':row['initial_position'],'rotation':row['initial_rotation']};events=[]
            def get_provider(owner):
                self.assertEqual(owner,'owner');events.append('get_provider')
                return 'provider' if row['present'] else None
            def get_context(owner):
                self.assertEqual(owner,'owner');events.append('get_context');return 'context'
            def configure(provider,context,mode):
                self.assertEqual((provider,context,mode),('provider','context',0));events.append('configure')
            def position(provider):
                self.assertEqual(provider,'provider');events.append('position');return row['position']
            def rotation(provider):
                self.assertEqual(provider,'provider');events.append('rotation')
                self.assertEqual(list(state['position']),row['result_position'])
                return row['rotation']
            def publish(value):
                self.assertIs(value,state);events.append('publish')
            publish_player_spawn_transform(state,'owner',get_provider=get_provider,
                get_context=get_context,configure=configure,read_position=position,
                read_rotation=rotation,publish=publish)
            self.assertEqual(events,row['events'])
            self.assertEqual(list(state['position']),row['result_position'])
            self.assertEqual(list(state['rotation']),row['result_rotation'])
    def test_player_spawn_service_failure_preserves_partial_update(self):
        from reference.skeleton_parent_transform import publish_player_spawn_transform
        state={'position':(0,0,0,9),'rotation':(2,3,4,5)};published=[]
        def fail(provider):raise RuntimeError('rotation unavailable')
        with self.assertRaises(RuntimeError):
            publish_player_spawn_transform(state,object(),get_provider=lambda _:0,
                get_context=lambda _:None,configure=lambda *args:None,
                read_position=lambda _:[4,5,6],read_rotation=fail,publish=published.append)
        self.assertEqual(state['position'],(4,5,6,0))
        self.assertEqual(state['rotation'],(2,3,4,5))
        self.assertEqual(published,[])
    def test_spawn_coordinate_original_instruction_receipt(self):
        from reference.skeleton_parent_transform import resolve_spawn_position,resolve_spawn_rotation
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/spawn_coordinates_validation.json').read_text())
        self.assertEqual(report['cases'],60)
        for row in report['rows']:
            self.assertEqual(list(resolve_spawn_position(row['position'],row['parent_matrix'])),row['result_position'])
            self.assertEqual(list(resolve_spawn_rotation(row['rotation'],row['parent_matrix'],
                matrix_template=row['matrix_template'])),row['result_rotation'])
            self.assertEqual(row['rotation_events'],['resolve_mask']+(['accessor'] if row['mode']=='indirect' else []))
    def test_spawn_initialized_template_default_and_parentless_copy(self):
        from reference.skeleton_parent_transform import resolve_spawn_rotation,resolve_spawn_position
        self.assertEqual(resolve_spawn_rotation([2,3,4,5]),(2,3,4,5))
        self.assertEqual(resolve_spawn_position([1,2,3,99]),(1,2,3,99))
        identity=[[float(i==j) for j in range(4)] for i in range(4)]
        self.assertEqual(resolve_spawn_rotation([0,0,0,1],identity),(0,0,0,1))
        self.assertEqual(resolve_spawn_position([1,2,3,99],identity),(1,2,3,0))

    def test_spawn_original_initializer_composition_receipt(self):
        from reference.skeleton_parent_transform import resolve_spawn_rotation
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/spawn_coordinates_validation.json').read_text())
        self.assertTrue(report['template_initialization_recovered'])
        rows=[row for row in report['rows'] if row['template_source']=='original_initializer']
        self.assertEqual(len(rows),30)
        for row in rows:
            self.assertEqual(list(resolve_spawn_rotation(row['rotation'],row['parent_matrix'])),row['result_rotation'])
    def test_spawn_publication_matrix_instruction_receipt(self):
        from reference.skeleton_parent_transform import build_spawn_publication_matrix
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/spawn_publication_matrix_validation.json').read_text())
        self.assertEqual(report['cases'],80)
        for row in report['rows']:
            norms=[]
            def estimate(norm):norms.append(norm);return row['result']['reciprocal_estimate']
            result=build_spawn_publication_matrix(row['position'],row['rotation'],estimate,matrix_template=row['matrix_template'])
            self.assertEqual([list(r) for r in result['matrix']],row['result']['matrix'])
            self.assertEqual(list(result['normalized_rotation']),row['result']['normalized_rotation'])
            self.assertEqual(norms,[row['result']['squared_norm']])
            self.assertEqual(result['matrix'][3][3],1)
    def test_spawn_publication_rejects_invalid_normalization(self):
        from reference.skeleton_parent_transform import build_spawn_publication_matrix
        for rotation,estimate in (([0,0,0,0],1),([0,0,0,1],0),([0,0,0,1],float('nan'))):
            with self.assertRaises(ValueError):build_spawn_publication_matrix([0,0,0,0],rotation,lambda _:estimate)
    def test_spawn_publication_refines_supplied_estimate(self):
        from reference.skeleton_parent_transform import build_spawn_publication_matrix
        result=build_spawn_publication_matrix([1,2,3,99],[0,0,0,2],lambda _:0.5)
        self.assertEqual(result['normalized_rotation'],(0,0,0,1))
        self.assertEqual(result['matrix'],((1,0,0,0),(0,1,0,0),(0,0,1,0),(1,2,3,1)))
    def test_spawn_entity_dispatch_instruction_receipt(self):
        from reference.skeleton_parent_transform import publish_spawn_entity_transform
        from reference.entity_transform_update import TransformEntity
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/spawn_entity_dispatch_validation.json').read_text())
        self.assertEqual(report['cases'],36)
        for row in report['samples']:
            old=bytes(64);new=bytes([1])*64;depth=row['initial_depth'];events=[]
            entity=TransformEntity(old,list(range(row['pre_count'])),7 if depth else None,depth)
            def notify(phase,component,entity):
                events.append(dict(kind=phase,transform='old' if entity.transform==old else 'new'))
                self.assertEqual(entity.lock_depth,depth+1)
                if phase=='pre':entity.components=list(range(row['replacement_count']))
            def cache(entity):events.append(dict(kind='cache',transform='new'))
            def linked(entity,first,second,flags):
                self.assertIs(first,second);self.assertEqual(flags,31)
                self.assertEqual(entity.lock_depth,depth)
                self.assertEqual(entity.lock_owner,7 if depth else None)
                events.append(dict(kind='linked',transform='new'))
            publish_spawn_entity_transform(entity,new,derived=row['derived'],propagate_linked=linked,
                thread_id=7,notify=notify,publish_cache=cache)
            self.assertEqual(events,row['events'])
            self.assertEqual(entity.transform,new)
    def test_spawn_derived_requires_service_before_mutation(self):
        from reference.skeleton_parent_transform import publish_spawn_entity_transform
        from reference.entity_transform_update import TransformEntity
        entity=TransformEntity(bytes(64))
        with self.assertRaises(NotImplementedError):
            publish_spawn_entity_transform(entity,bytes([1])*64,derived=True,
                thread_id=1,notify=lambda *args:None,publish_cache=lambda _:None)
        self.assertEqual(entity.transform,bytes(64))
    def test_linked_spawn_loop_instruction_receipt(self):
        from reference.skeleton_parent_transform import propagate_linked_spawn_transforms
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/linked_spawn_validation.json').read_text())
        self.assertEqual(report['cases'],24)
        for row in report['rows']:
            state={'links':list(row['links']),'local_transforms':report['local_transforms']};events=[];outputs=[]
            packet={'first':report['first'],'second':report['second'],'flags':row['flags']}
            def acquire(target):
                events.append(['acquire',target]);return target,('cleanup',target)
            def predicate(target):events.append(['predicate',target]);return target==2
            def release(token):
                self.assertEqual(token[0],'cleanup');events.append(['release',token[1]])
            def dispatch(target,packet):
                events.append(['dispatch',target]);outputs.append(dict(target=target,**packet))
                if len(outputs)==1 and row['scenario'] in ('shrink','grow','replace'):
                    state['links']=[3] if row['scenario']=='shrink' else [3,4]
            result=propagate_linked_spawn_transforms(state,packet,resolve=lambda handle:None if handle==0 else handle,
                target_flags=lambda target:1 if target==1 else 0,acquire_descriptor=acquire,
                descriptor_blocks=predicate,release_descriptor=release,dispatch=dispatch)
            self.assertTrue(result);self.assertEqual(events,row['events']);self.assertEqual(outputs,row['outputs'])
    def test_linked_descriptor_failure_releases_without_dispatch(self):
        from reference.skeleton_parent_transform import propagate_linked_spawn_transforms
        events=[]
        def fail(_):raise RuntimeError('predicate unavailable')
        with self.assertRaises(RuntimeError):
            propagate_linked_spawn_transforms({'links':[1]}, {},resolve=lambda x:x,target_flags=lambda _:0,
                acquire_descriptor=lambda _:('descriptor','cleanup'),descriptor_blocks=fail,
                release_descriptor=events.append,dispatch=lambda *args:events.append('dispatch'))
        self.assertEqual(events,['cleanup'])
    def test_linked_descriptor_original_instruction_join(self):
        from reference.skeleton_parent_transform import propagate_linked_spawn_transforms,linked_spawn_descriptor_blocks
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/linked_spawn_descriptor_validation.json').read_text())
        self.assertEqual(report['cases'],96)
        identity=[[float(i==j) for j in range(4)] for i in range(4)]
        for row in report['rows']:
            descriptor=dict(row['descriptor']);mask=descriptor.pop('tls_mask');events=[];mask_calls=[]
            def acquire(_):events.append('acquire');return descriptor,'cleanup'
            def visibility():mask_calls.append(True);return mask
            def predicate(d):
                events.append('predicate');result=linked_spawn_descriptor_blocks(d,visibility)
                self.assertEqual(result,row['blocked']);return result
            def release(token):self.assertEqual(token,'cleanup');events.append('release')
            def dispatch(*args):events.append('dispatch')
            propagate_linked_spawn_transforms({'links':[1],'local_transforms':[identity]},
                {'first':identity,'second':identity,'flags':31},resolve=lambda x:x,
                target_flags=lambda _:0,acquire_descriptor=acquire,descriptor_blocks=predicate,
                release_descriptor=release,dispatch=dispatch)
            self.assertEqual(events,row['events'])
            self.assertEqual(len(mask_calls),row['mask_calls']-1)
            self.assertEqual(row['final_holder_counts'],[2,2])
    def test_joined_spawn_publication_instruction_receipt(self):
        from reference.skeleton_parent_transform import publish_spawn_pose
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/spawn_pipeline_validation.json').read_text())
        self.assertEqual(report['cases'],12)
        for row in report['rows']:
            events=[]
            def entity(state):events.append('entity');return 'entity'
            def parent(state,phase):events.append('parent');return row['first_parent' if phase=='position' else 'second_parent']
            def publish(e,m):events.append('publish');self.assertEqual([list(r) for r in m],row['result']['matrix'])
            def skeleton(e):events.append('skeleton');return None if row['slots'] is None else {'slots':row['slots']}
            def reset(bank,pose):events.append('reset_'+str(bank))
            result=publish_spawn_pose(row['state'],get_entity=entity,read_parent=parent,
                reciprocal_sqrt=lambda _:row['estimate'],publish_entity=publish,find_skeleton=skeleton,reset_parent=reset)
            self.assertEqual(events,row['events'])
            self.assertEqual([list(r) for r in result['matrix']],row['result']['matrix'])
    def test_spawn_publication_example(self):
        from engine.examples.spawn_publication_probe import run_probe
        result=run_probe()
        self.assertEqual(result['matrix'][3],(11,22,33,1))
        self.assertEqual(result['final_lock_depth'],0)
        self.assertEqual(result['events'],['entity','parent_position','parent_rotation','publish',
            'pre_synthetic-component','cache','post_synthetic-component','skeleton','reset_a','reset_b'])
    def test_nonempty_bank_reset_instruction_receipt(self):
        import struct
        from reference.skeleton_parent_transform import reset_animation_bank_parent
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/bank_record_reset_validation.json').read_text())
        self.assertEqual(report['cases'],16)
        for row in report['rows']:
            sentinel=bytes([0x5a])*32;old=bytes([0xa5])*32
            bank=dict(parent=old,default_pose=old,records=[sentinel]*(row['count']+1),count=row['count'],reset_word=123)
            parent=struct.pack('<8f',*row['parent']);default=struct.pack('<8f',*row['default_pose']);calls=[]
            def supply():calls.append(True);return default
            reset_animation_bank_parent(bank,parent,row['reset'],supply)
            self.assertEqual(bank['parent'],parent)
            self.assertEqual(bank['default_pose'],default if row['reset'] else old)
            self.assertEqual(bank['records'][:row['count']],[default if row['reset'] else sentinel]*row['count'])
            self.assertEqual(bank['records'][-1],sentinel)
            self.assertEqual(bank['reset_word'],0 if row['reset'] else 123)
            self.assertEqual(len(calls),row['count']+1 if row['reset'] else 0)
    def test_joined_nonempty_publication_receipt(self):
        import struct
        from reference.skeleton_parent_transform import publish_spawn_pose,reset_animation_bank_parent
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/spawn_pipeline_records_validation.json').read_text())
        self.assertEqual(report['cases'],12)
        default=struct.pack('<8f',0,0,0,0,0,0,0,1);sentinel=bytes([0x5a])*32
        for row in report['rows']:
            banks=[dict(parent=bytes(32),default_pose=bytes(32),records=[sentinel]*4,count=3,reset_word=123) for _ in range(2)]
            calls=[]
            def reset(index,pose):
                calls.append(index)
                reset_animation_bank_parent(banks[index],struct.pack('<8f',*(pose['parent_position']+pose['parent_rotation'])),True,lambda:default)
            result=publish_spawn_pose(row['state'],get_entity=lambda _:'entity',
                read_parent=lambda _,phase:row['first_parent' if phase=='position' else 'second_parent'],
                reciprocal_sqrt=lambda _:row['estimate'],publish_entity=lambda *args:None,
                find_skeleton=lambda _:None if row['slots'] is None else {'slots':row['slots']},reset_parent=reset)
            self.assertEqual(calls,[s for s in (row['slots'] or []) if s is not None])
            self.assertEqual([list(r) for r in result['matrix']],row['result']['matrix'])
            for index,bank in enumerate(banks):
                self.assertEqual(bank['records'][:3],[default if index in calls else sentinel]*3)
                self.assertEqual(bank['records'][3],sentinel)
                self.assertEqual(bank['reset_word'],0 if index in calls else 123)
    def test_cached_parent_prefix_instruction_receipt(self):
        from reference.skeleton_parent_transform import publish_cached_parent_prefix,prepare_skeleton_parent_transform
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/cached_parent_prefix_validation.json').read_text())
        self.assertEqual(report['cases'],24)
        for row in report['rows']:
            pose=prepare_skeleton_parent_transform(**row['inputs'])
            component={'primary':0,'current':1,'cached_parent':pose};writes=[]
            def callback(c):
                c['cached_parent']=dict(c['cached_parent'],parent_position=c['cached_parent']['parent_position'][:3]+(1.,))
                if row['mode']=='callback_swap':c['current']=2
            def store(bank,p,reset):writes.append((bank,p['parent_position'][3],reset))
            publish_cached_parent_prefix(component,before_publish=None if row['mode']=='none' else callback,set_parent=store)
            self.assertEqual(writes,[(0,row['published_w'],False),(row['current_index'],row['published_w'],False)])
    def test_cached_prefix_missing_primary_skips_callback(self):
        from reference.skeleton_parent_transform import publish_cached_parent_prefix
        def unexpected(*args):self.fail('unexpected service')
        self.assertFalse(publish_cached_parent_prefix({'primary':None},before_publish=unexpected,set_parent=unexpected))
    def test_cached_parent_callback_gate_instruction_receipt(self):
        from reference.skeleton_parent_transform import cached_parent_callback_gate
        report=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/cached_callback_gate_validation.json').read_text())
        self.assertEqual(report['cases'],168)
        for row in report['rows']:
            inputs={k:v for k,v in row.items() if k not in ('invoked','forwarded_context')}
            self.assertEqual(cached_parent_callback_gate(**inputs),
                {k:row[k] for k in ('invoked','forwarded_context')})
