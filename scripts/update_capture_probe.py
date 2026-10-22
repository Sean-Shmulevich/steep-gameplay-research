"""Bounded observation-plan controller. No velocity/pose/impulse commands."""
import configparser
import json
from pathlib import Path
import time

def capture_update(client, build, *, timeout=12, during_capture=None):
    build=Path(build)
    log=build/'snow_host.log'
    trace=build/'plugins/update_capture.ini.trace.jsonl'
    if trace.exists():
        raise RuntimeError('Refusing a pre-existing capture export; use a fresh session directory')
    start=len(log.read_bytes()) if log.exists() else 0
    config=configparser.ConfigParser()
    config.read(build/'plugins/update_capture.ini')
    require_attribution=config.getboolean('capture','attribute_jobs',fallback=False)
    require_substeps=config.getboolean('capture','require_substeps',fallback=False)
    result={'ok':False,'attribution_required':require_attribution,'substeps_required':require_substeps}
    status=client.call('simulation.status')
    if status.get('host_paused') or status.get('engine', {}).get('held'):
        raise RuntimeError('Already held; refusing to take over an existing pause')
    resumed=False
    try:
        result['pause']=client.call('simulation.pause',lease_ms=30000)
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            text=log.read_bytes()[start:].decode(errors='replace') if log.exists() else ''
            if 'capture configured; resume starts bounded observation' in text: break
            time.sleep(.1)
        else: raise RuntimeError('Capture configuration was not confirmed; inspect host log')
        result['resume']=client.call('simulation.resume')
        resumed=True
        if during_capture is not None:
            result['input_delivery']=during_capture()
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:
                rows=[json.loads(line) for line in trace.read_text().splitlines()]
                if rows and len(rows)-1==rows[0]['records']: break
            except (OSError,ValueError,KeyError): pass
            time.sleep(.1)
        else: raise RuntimeError('No complete capture export before deadline')
        summary=rows[0]; records=rows[1:]
        result['summary']=summary
        result['valid_pairs']=sum(bool(r['before']['valid']&1 and r['after']['valid']&1) for r in records)
        result['attributed_records']=sum(r.get('attribution_attempted')==1 and r.get('attribution_valid')==1 for r in records)
        result['direct_substep_records']=sum(r.get('attribution_valid')==1 and r.get('frame_valid')==1 for r in records)
        result['gate_patterns']=sorted({tuple(r['before']['gates']) for r in records})
        result['request_count']=len({r['before']['request'] for r in records if r['before']['valid']&4})
        result['ok']=(summary['installed']==1 and summary['restored']==1 and summary['drained']==1
                      and (during_capture is None or result['input_delivery'].get('ok') is True)
                      and summary['dropped']==0 and len(records)>0 and result['valid_pairs']>0
                      and (not require_attribution or result['attributed_records']>0)
                      and (not require_substeps or result['direct_substep_records']>0))
        if not result['ok']: result['error']='Capture installation/restoration/drain/data gate failed'
    finally:
        if not resumed:
            try:
                result['final_resume']=client.call('simulation.resume')
            except Exception as exc:
                result['ok']=False
                result['resume_error']=str(exc)
    return result
