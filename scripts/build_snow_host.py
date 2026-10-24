#!/usr/bin/env python3
"""Build independently authored Windows mod-host sources; never launches a game."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--adapter', choices=('fixture', 'steep'), default='fixture')
    ap.add_argument('--capture-plugin', action='store_true', help='Build opt-in experimental update capture plugin; steep adapter only')
    ap.add_argument('--animation-queue-capture-plugin', action='store_true', help='Build opt-in triggered animation queue dispatch capture; steep adapter only')
    ap.add_argument('--delegate-capture-plugin', action='store_true', help='Build opt-in experimental graphics/engine delegate capture; steep adapter only')
    ap.add_argument('--finalizer-capture-plugin', action='store_true', help='Build opt-in filtered finalizer capture; steep adapter only')
    ap.add_argument('--scheduler-phase-capture-plugin', action='store_true', help='Build opt-in paired main/finalizer capture; steep adapter only')
    ap.add_argument('--command-manager-startup-plugin', action='store_true', help='Build opt-in read-only command manager initialization observation; steep adapter only')
    ap.add_argument('--command-manager-write-plugin', action='store_true', help='Build opt-in one-shot startup page-write experiment; steep adapter only')
    ap.add_argument('--command-manager-execute-plugin', action='store_true', help='Build opt-in one-shot constructor-page execution experiment; steep adapter only')
    ap.add_argument('--execution-control-plugin', action='store_true', help='Build opt-in execution observer control on an authored private allocation')
    ap.add_argument('--protection-api-snapshot-plugin', action='store_true', help='Build opt-in read-only protection API entry snapshots')
    ap.add_argument('--protection-context-snapshot-plugin', action='store_true', help='Build opt-in read-only protection context/stream snapshots; steep adapter only')
    ap.add_argument('--protection-continuation-control-plugin', action='store_true', help='Build opt-in continuation identity/authored-page control; steep adapter only')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--cc', default='x86_64-w64-mingw32-gcc')
    args = ap.parse_args()
    if (args.animation_queue_capture_plugin or args.capture_plugin or args.delegate_capture_plugin or args.finalizer_capture_plugin or args.scheduler_phase_capture_plugin or args.command_manager_startup_plugin or args.command_manager_write_plugin or args.command_manager_execute_plugin or args.protection_context_snapshot_plugin or args.protection_continuation_control_plugin) and args.adapter != 'steep':
        ap.error('capture plugins require --adapter steep')
    cc = shutil.which(args.cc)
    if not cc:
        ap.error('MinGW x64 compiler unavailable: '+args.cc)
    out = args.out.resolve()
    if out.is_relative_to(ROOT):
        ap.error('Use an output directory outside the findings repository')
    out.mkdir(parents=True, exist_ok=True)
    (out/'plugins').mkdir(exist_ok=True)
    src = ROOT/'native/snow_host'
    flags = [cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(src)]
    def build(name, sources, extra):
        subprocess.run(flags+[str(src/s) for s in sources]+extra+['-o', str(out/name)], check=True, timeout=120)
    build('snow_host.dll', ['snow_host.c','snow_plugins.c', args.adapter+'_adapter.c'] + (['snow_update_snapshot.c'] if args.adapter=='steep' else []), ['-shared','-lws2_32'])
    build('host_loader.exe', ['host_loader.c'], ['-municode'])
    build('startup_launcher.exe', ['startup_launcher.c'], ['-municode','-luser32'])
    build('plugins/step_logger.dll', ['examples/step_logger.c'], ['-shared'])
    build('plugins/player_logger.dll', ['examples/player_logger.c'], ['-shared'])
    build('snow_update_probe.dll', ['snow_update_probe.c','snow_update_trace.c','snow_update_snapshot.c','snow_entry_attribution.c','snow_batch_frame.c','snow_entry_thunk.S','snow_motion_observation.c'], ['-shared'])
    build('snow_action_probe.dll', ['snow_action_probe.c','snow_action_trace.c'], ['-shared'])
    build('snow_animation_queue_probe.dll', ['snow_animation_queue_probe.c','snow_animation_queue_trace.c','snow_animation_queue.c'], ['-shared'])
    build('snow_delegate_probe.dll', ['snow_delegate_probe.c','snow_delegate_trace.c','snow_update_snapshot.c','snow_motion_observation.c'], ['-shared'])
    build('snow_finalizer_probe.dll', ['snow_finalizer_probe.c','snow_delegate_trace.c'], ['-shared'])
    if args.command_manager_write_plugin:
        build('plugins/command_manager_write.dll', ['examples/command_manager_write.c','snow_first_write.c'], ['-shared'])
    if args.command_manager_execute_plugin:
        build('plugins/command_manager_execute.dll', ['examples/command_manager_execute.c','snow_first_execute.c','snow_local_protection.c','snow_continuation_identity.c'], ['-shared'])
    if args.execution_control_plugin:
        build('plugins/execution_control.dll', ['examples/execution_control.c','snow_first_execute.c'], ['-shared'])
        (out/'fixtures').mkdir(exist_ok=True)
        build('fixtures/execution_control_image.dll', ['../../tests/fixtures/snow_first_execute_image.c'], ['-shared','-fno-toplevel-reorder'])
    if args.protection_api_snapshot_plugin:
        build('plugins/protection_api_snapshot.dll', ['examples/protection_api_snapshot.c'], ['-shared'])
    if args.protection_context_snapshot_plugin:
        build('plugins/protection_context_snapshot.dll', ['examples/protection_context_snapshot.c'], ['-shared'])
    if args.protection_continuation_control_plugin:
        build('plugins/protection_continuation_control.dll', ['examples/protection_continuation_control.c','snow_continuation_identity.c','snow_first_execute.c'], ['-shared'])
    if args.command_manager_startup_plugin:
        build('plugins/command_manager_startup.dll', ['examples/command_manager_startup.c'], ['-shared'])
    if args.animation_queue_capture_plugin:
        build('plugins/animation_queue_capture.dll', ['examples/animation_queue_capture.c','snow_animation_queue_probe.c','snow_animation_queue_trace.c','snow_animation_queue.c'], ['-shared'])
    if args.delegate_capture_plugin:
        build('plugins/delegate_capture.dll', ['examples/delegate_capture.c','snow_delegate_probe.c','snow_delegate_trace.c','snow_update_snapshot.c','snow_motion_observation.c'], ['-shared'])
    if args.finalizer_capture_plugin:
        build('plugins/finalizer_capture.dll', ['examples/finalizer_capture.c','snow_finalizer_probe.c','snow_delegate_trace.c'], ['-shared'])
    if args.scheduler_phase_capture_plugin:
        build('plugins/scheduler_phase_capture.dll', ['examples/scheduler_phase_capture.c','snow_delegate_probe.c','snow_finalizer_probe.c','snow_delegate_trace.c','snow_update_snapshot.c','snow_motion_observation.c'], ['-shared'])
    if args.capture_plugin:
        build('plugins/update_capture.dll', ['examples/update_capture.c','steep_adapter.c','snow_update_probe.c','snow_update_trace.c','snow_update_snapshot.c','snow_entry_attribution.c','snow_batch_frame.c','snow_entry_thunk.S','snow_motion_observation.c'], ['-shared'])
    (out/'build.json').write_text(json.dumps({'adapter':args.adapter,'game_launched':False},indent=2)+'\n')
    print(json.dumps({'ok':True,'adapter':args.adapter,'output':str(out),'game_launched':False}))

if __name__ == '__main__':
    main()
