"""Acceptance sequence for an already connected Snow host.

Uses real host commands in production; injected speed trial reuses the bounded
live probe. This module does not launch the game or infer a successful startup.
"""
import math
import time
from snow_host_client import demo


def run_acceptance(client, speed_trial, *, steps=3, ready_wait_seconds=0):
    if (isinstance(ready_wait_seconds,bool) or not isinstance(ready_wait_seconds,(int,float))
            or not math.isfinite(ready_wait_seconds) or not 0<=ready_wait_seconds<=20):
        raise ValueError('Readiness wait must be between 0 and 20 seconds')
    report={'ok':False,'stages':[],'readiness_samples':[]}
    def ready_player():
        deadline=time.monotonic()+ready_wait_seconds
        while True:
            # Only successful reads lacking the eligibility flag are polled.
            # Transport failures and host refusals remain failures.
            player=client.call('player.get')
            report['readiness_samples'].append(player)
            if (player.get('identity') and player.get('flags',0)&3==3
                    or time.monotonic()>=deadline):
                return player
            time.sleep(min(.5,max(0,deadline-time.monotonic())))
    def stage(name, action, passed):
        entry={'name':name,'ok':False};report['stages'].append(entry)
        try:
            entry['result']=action()
            entry['ok']=bool(passed(entry['result']))
            if not entry['ok']:entry['error']='Acceptance condition not met'
        except Exception as exc:
            entry['error']=str(exc)
        return entry['ok']
    if not stage('player',ready_player,
                 lambda p:bool(p.get('identity')) and p.get('flags',0)&3==3):
        return report
    if not stage('pause_step_resume',lambda:demo(client,steps,30000),lambda r:r.get('ok') is True):
        return report
    if not stage('brake_boost',speed_trial,lambda r:r.get('ok') is True):
        return report
    if not stage('player_after',lambda:client.call('player.get'),
                 lambda p:bool(p.get('identity')) and p.get('flags',0)&3==3):
        return report
    report['ok']=True
    return report


def prepare_rider(client, forward_pulse):
    """One caller-authorized normal-input pulse for an inactive bound rider.

    Does not use a physics setter or claim ingestion. Caller supplies a bounded,
    identity-checked OS input helper and must return its key-release evidence.
    """
    report={'ok':False,'input_attempted':False,'game_input_ingestion_verified':False}
    try:
        status=client.call('simulation.status')
        if status.get('host_paused') or not status.get('ordinary'):
            raise RuntimeError('Preparation requires ordinary running simulation')
        report['before']=client.call('player.get')
        before=report['before']
        if not before.get('identity') or not before.get('flags',0)&1:
            raise RuntimeError('Preparation requires a valid bound player')
        if before['flags']&2:
            report['ok']=True
            return report
        report['input_attempted']=True
        report['input']=forward_pulse()
        if not report['input'].get('keys_released') or report['input'].get('exit_code')!=0:
            raise RuntimeError('Input helper did not confirm successful key release')
        report['after']=client.call('player.get')
        if report['after'].get('identity')!=before['identity']:
            raise RuntimeError('Player identity changed during preparation')
        report['ok']=True
    except Exception as exc:
        report['error']=str(exc)
    return report
