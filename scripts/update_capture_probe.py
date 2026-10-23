"""Bounded observation-plan controller. No velocity/pose/impulse commands."""
import configparser
import json
from pathlib import Path
import time
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.publication_input_join import delivery_window_coverage


def input_coverage(delivery, summary, records):
    """Authored acceptance gate for one OS pulse, not game ingestion proof."""
    try:
        reports = delivery["delivery_reports"]
        if not isinstance(reports, list) or len(reports) != 2:
            raise ValueError("expected exactly one key-down and one key-up report")
        down, up = reports
        if down["key_up"] is not False or up["key_up"] is not True:
            raise ValueError("delivery reports must be ordered down then up")
        frequency = summary["qpf"]
        if type(frequency) is not int or frequency <= 0:
            raise ValueError("invalid capture QPC frequency")
        if down["scan_raw"] != up["scan_raw"]:
            raise ValueError("delivery key identities differ")
        for report in reports:
            if (report["kind"] != "key_delivery" or report["api_reported_sent"] != 1
                    or type(report["qpc_frequency"]) is not int
                    or report["qpc_frequency"] != frequency):
                raise ValueError("unaccepted delivery or mismatched QPC frequency")
        coverage = delivery_window_coverage(
            [(r["entry"], r["exit"]) for r in records],
            key_down=down["qpc_ticks"], key_up=up["qpc_ticks"])
        return dict(coverage, game_acceptance="unverified")
    except (KeyError, TypeError, ValueError) as exc:
        return dict(covered=False, error=str(exc), game_acceptance="unverified")

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
        if during_capture is not None:
            result['input_coverage']=input_coverage(result['input_delivery'],summary,records)
        result['valid_pairs']=sum(bool(r['before']['valid']&1 and r['after']['valid']&1) for r in records)
        result['attributed_records']=sum(r.get('attribution_attempted')==1 and r.get('attribution_valid')==1 for r in records)
        result['direct_substep_records']=sum(r.get('attribution_valid')==1 and r.get('frame_valid')==1 for r in records)
        result['gate_patterns']=sorted({tuple(r['before']['gates']) for r in records})
        result['request_count']=len({r['before']['request'] for r in records if r['before']['valid']&4})
        result['ok']=(summary['installed']==1 and summary['restored']==1 and summary['drained']==1
                      and (during_capture is None or (result['input_delivery'].get('ok') is True
                           and result['input_coverage']['covered']))
                      and summary['dropped']==0 and len(records)>0 and result['valid_pairs']>0
                      and (not require_attribution or result['attributed_records']>0)
                      and (not require_substeps or result['direct_substep_records']>0))
        if not result['ok']:
            result['error']='Capture installation/restoration/drain/data/input coverage gate failed'
    finally:
        if not resumed:
            try:
                result['final_resume']=client.call('simulation.resume')
            except Exception as exc:
                result['ok']=False
                result['resume_error']=str(exc)
    return result
