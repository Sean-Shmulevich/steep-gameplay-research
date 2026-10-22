"""Observe the startup bootstrap and host command service before gameplay navigation finishes."""
import argparse,json,subprocess,time
from pathlib import Path
from snow_host_client import SnowHostClient
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--workspace',type=Path,required=True)
p.add_argument('--build',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--port',type=int,default=47017)
a=p.parse_args();a.output.mkdir(exist_ok=False);result={'ok':False}
try:
 deadline=time.monotonic()+75
 report=a.build/'snow_startup.jsonl';rows=[]
 while time.monotonic()<deadline:
  if report.exists():
   rows=[json.loads(l) for l in report.read_text().splitlines() if l.endswith('}')]
   final=next((r for r in rows if r['phase'] in ['host_started','loader_unavailable','create_process']),None)
   if final:
    assert final['ok'],'Bootstrap failed: '+str(final)
    break
  time.sleep(.1)
 else:raise RuntimeError('No completed startup load before deadline')
 result['bootstrap']=rows
 result['host_started_without_visible_window']=all(r['visible_windows']==0 for r in rows if r['phase'] in ['load_begin','host_started'])
 while time.monotonic()<deadline:
  try:
   with SnowHostClient(port=a.port) as c: result['first_status']=c.call('host.hello')
   break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Host command service did not answer during startup')
 # Record what is visible now; absence of a game window is expected for early startup.
 cap=subprocess.run([str(a.workspace/'runtime/testbench/run3/mac-game-capture'),str(a.output/'early.png')],capture_output=True,text=True,timeout=15)
 (a.output/'capture.txt').write_text(cap.stdout+cap.stderr)
 screenshots=[json.loads(l) for l in cap.stdout.splitlines() if l.startswith('{')]
 result['screen_text']=' '.join(screenshots[-1].get('recognized_text',[])) if screenshots else ''
 text=result['screen_text'].upper();result['gameplay_hud_already_visible']='CHANGE SPORT' in text and 'BINOCULARS' in text
 assert not result['gameplay_hud_already_visible'],'Host load was not observed before gameplay'
 result['ok']=True
except Exception as e:result['error']=str(e)
finally:
 (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result.get(k) for k in ['ok','error','host_started_without_visible_window','screen_text']}),flush=True)
raise SystemExit(0 if result['ok'] else 2)
