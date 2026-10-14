import argparse,json,subprocess,sys,time,struct
from pathlib import Path
parser=argparse.ArgumentParser(description='Guarded pause/load/resume phase for the established local research workspace')
parser.add_argument('--workspace',type=Path,required=True)
parser.add_argument('--build',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
H=args.build.resolve();R=args.workspace.resolve();TB=R/'runtime/testbench';sys.path.insert(0,str(TB/'run36'))
from observe import Persistent
out=args.output.resolve();out.mkdir(exist_ok=False)
subprocess.run([sys.executable,str(TB/'run13/identify_game.py'),'--output',str(out/'identity.json')],check=True,timeout=35,capture_output=True)
i=json.loads((out/'identity.json').read_text());assert i['ok'] and int(i['base'],16)==0x140000000
helper=[sys.executable,str(TB/'wine_helper.py')];native=R/'analysis/engine-event-reset-wait/private/modewrite'
reader=Persistent(i,out);result={'ok':False,'events':[]};entered=False;loaded=False;base=None

def command(tag,exe,args,timeout=15):
 p=subprocess.run(helper+[str(exe)]+args,capture_output=True,text=True,timeout=timeout)
 (out/(tag+'.txt')).write_text(p.stdout+p.stderr)
 rows=[json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
 row=rows[-1] if rows else {'ok':False,'exit':p.returncode}
 result['events'].append({'tag':tag,'result':row});return row

def sample(tag):
 owner=struct.unpack('<Q',reader.readv([(0x14312cfe8,8)])[0])[0]
 assert 0x10000<owner<0x800000000000
 b=reader.readv([(owner+0x40,4),(owner+0x3ab0+0x58,4),(owner+0x4dc8+0x58,4)])
 row={'tag':tag,'owner':hex(owner),'mode':b[0].hex(),'step':struct.unpack('<I',b[1])[0],'end_frame':struct.unpack('<I',b[2])[0]}
 result['events'].append(row);return row
try:
 a=sample('baseline_a');time.sleep(.4);b=sample('baseline_b');base=b['mode'];assert base.startswith('000000') and a['step']!=b['step'],'World Step not active'
 entered=True # Restore even if the call times out after changing state.
 row=command('enter',native/'NativeCall.exe',[str(i['pid']),i['created'],'enter',base]);assert row.get('ok',False)
 a=sample('held_a');time.sleep(.4);b=sample('held_b');assert a['step']==b['step'] and a['end_frame']!=b['end_frame'],'Pause/render behavior not verified'
 dll='Z:'+str(H/'late_probe.dll').replace('/','\\')
 row=command('late_load',H/'load_probe.exe',[str(i['pid']),i['created'],dll]);loaded=row.get('ok',False);assert loaded,'Loader did not verify module'
 marker=(H/'snow_late_probe.bin').read_bytes();magic,pid,created,module=struct.unpack('<IIQQ',marker)
 result['marker_matches']=magic==0x4c415445 and pid==i['pid'] and created==int(i['created'],16) and module==int(row['module'],16)
 (out/'marker.bin').write_bytes(marker);assert result['marker_matches']
 c=sample('loaded_held');assert c['step']==b['step'],'World Step advanced while held'
 result['ok']=True
except Exception as e:result['error']=str(e)
finally:
 if entered:
  try:
   reader.deadline=time.monotonic()+30;current=sample('before_resume')['mode']
   if loaded:
    restored=command('leave',native/'NativeCall.exe',[str(i['pid']),i['created'],'leave',current]).get('ok',False)
   else:restored=False
   if not restored:
    result['byte_restore']=command('restore',native/'ModeWrite.exe',[str(i['pid']),i['created'],current,base])
   a=sample('resumed_a');time.sleep(.7);b=sample('resumed_b');result['resumed']=a['step']!=b['step'] and b['mode']==base
   if result['ok'] and result['resumed']:
    stability=[]
    for k in range(5):
     if k:time.sleep(5)
     stability.append(sample('stability_'+str(k)))
    result['stable_20_seconds']=all(r['mode']==base for r in stability) and all(a['step']!=b['step'] for a,b in zip(stability,stability[1:]))
    result['ok']=result['ok'] and result['stable_20_seconds']
  except Exception as e:result['resume_error']=str(e)
 reader.close();result['ok']=result['ok'] and result.get('resumed',False)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result.get(k) for k in ['ok','error','marker_matches','resumed','stable_20_seconds','resume_error']}),flush=True)
raise SystemExit(0 if result['ok'] else 2)
