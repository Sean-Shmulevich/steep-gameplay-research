"""Read a call-scoped work packet through caller-supplied memory transport.

Evidence: CENTRAL_IMPULSE.md, Work-wrapper initialization contract.
Caller must locate the packet while its stack frame is alive and freshly verify
the component. This module neither attaches to a process nor pins that frame.
"""
import math
import struct
from .scheduler_observation import _address


def capture_pose_work_boundary(readv, registers, component, entity, skeleton_table, guards):
    """Adapt a signature-verified caller stop to the packet reader.

    RDI is the component and caller RSP+48 holds the packet at the inspected
    before/after work-call sites. The debugger caller must verify site bytes and
    stop context first. Unrelated components are filtered before memory access.
    No live registers or addresses are retained in the returned observation.
    """
    if type(registers.get('rdi')) is not int or type(registers.get('rsp')) is not int:
        raise ValueError('integer RDI and RSP required')
    _address(component,8)
    if registers['rdi'] != component:
        return None
    _address(registers['rsp'],68)
    return capture_pose_work_packet(readv,registers['rsp']+48,component,entity,skeleton_table,guards)


def capture_pose_work_packet(readv, packet, component, entity, skeleton_table, guards):
    for address, size in ((packet,20),(component,0x260),(entity,8),(skeleton_table,8)):
        _address(address,size)
    retained=list(guards)
    if not 1 <= len(retained) <= 16:
        raise ValueError('provide 1..16 fresh identity guards')
    for address,value in retained:
        if type(value) is not bytes or not 1 <= len(value) <= 256:
            raise ValueError('invalid identity guard')
        _address(address,len(value))
    def read(plan):
        result=list(readv(plan))
        if len(result)!=len(plan) or any(type(v) is not bytes or len(v)!=n for v,(_,n) in zip(result,plan)):
            raise ValueError('incomplete work-packet read')
        return result
    def check():
        if read([(a,len(v)) for a,v in retained]) != [v for _,v in retained]:
            raise ValueError('work-packet identity or state changed')
    def observe(address,size):
        _address(address,size)
        value=read([(address,size)])[0];retained.append((address,value));return value
    check()
    if struct.unpack('<Q',observe(component,8))[0]!=skeleton_table:
        raise ValueError('skeleton table mismatch')
    if struct.unpack('<Q',observe(component+0x10,8))[0]!=entity:
        raise ValueError('skeleton owner mismatch')
    current=struct.unpack('<Q',observe(component+0x258,8))[0]
    input_address,output_address,interval=struct.unpack('<QQf',observe(packet,20))
    if not math.isfinite(interval):
        raise ValueError('nonfinite work-packet time')
    if input_address==output_address:
        raise ValueError('work wrappers alias')
    def wrapper(address):
        _address(address,0x303)
        owner,primary,alternate,storage,header=struct.unpack('<4QI',observe(address,36))
        index,flags=struct.unpack('<HB',observe(address+0x300,3))
        if owner!=component:
            raise ValueError('work wrapper component mismatch')
        return dict(primary_present=bool(primary),alternate_present=bool(alternate),
                    primary_matches_current=bool(primary and primary==current),
                    banks_alias=bool(primary and primary==alternate),
                    own_inline_storage=storage==address+0x24,header=header,index=index,flags=flags)
    inp=wrapper(input_address);out=wrapper(output_address)
    check()
    initial=all(w['own_inline_storage'] and w['header']==32772 and
                w['index']==65535 and w['flags']&7==0 and not w['alternate_present']
                for w in (inp,out)) and not out['primary_present'] and (
                inp['primary_matches_current'] if current else not inp['primary_present'])
    return dict(schema='pose-work-packet-observation-v1',input=inp,output=out,
                packet_time=interval,current_present=bool(current),
                initialization_pattern_matches=initial,guards_matched=True,
                atomic_snapshot=False,lifetime_pinned=False,callback_execution_verified=False,
                writer_attribution_established=False,safe_native_call_established=False)
