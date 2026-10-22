"""Offline animation-bank ownership inspection with explicit external services.

Evidence: CENTRAL_IMPULSE.md, Animation bank pool reuse/release and wrapper cleanup.
No native allocation, scheduling, game access or pointer lifetime guarantee.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from reference.animation_bank_pool import reuse_pose_bank, release_pose_bank, cleanup_pose_work_wrappers


class AnimationPoolSession:
    def __init__(self, banks, entries, *, copy_selected, clear_auxiliary, free_storage):
        if not isinstance(banks,dict) or not 1<=len(banks)<=256:
            raise ValueError('provide 1..256 named banks')
        if not isinstance(entries,list) or len(entries)>256:
            raise ValueError('at most 256 pool entries')
        # Bank names define identities; reuse a name in entries to model aliasing.
        self.banks={name:deepcopy(bank) for name,bank in banks.items()}
        for name,bank in self.banks.items():
            if not isinstance(name,str) or not name:raise ValueError('nonempty bank names required')
            for key,limit in (('flags',0xffffffff),('auxiliary_mask',65535),('auxiliary_count',65535)):
                self._uint(bank[key],limit,key)
        self.entries=[]
        for row in entries:
            for key in ('occupied_mask','initialized_mask','representation_word'):
                self._uint(row[key],65535,key)
            self.entries.append(dict(row,bank=self.banks[row['bank']]))
        self.copy_selected=copy_selected
        self.clear_auxiliary=clear_auxiliary
        self.free_storage=free_storage

    @staticmethod
    def _uint(value,limit,name):
        if type(value) is not int or not 0<=value<=limit:raise ValueError(name+' outside unsigned range')

    def name(self,bank):
        return next(name for name,value in self.banks.items() if value is bank)

    def snapshot(self):
        return deepcopy(dict(banks=self.banks,entries=[dict(e,bank=self.name(e['bank'])) for e in self.entries]))

    def acquire(self,request_mask,representation,mode,source):
        bank=reuse_pose_bank(self.entries,request_mask,representation,mode,source,self.copy_selected)
        return dict(status='reused',bank=self.name(bank)) if bank is not None else dict(status='allocation_required',bank=None)

    def release(self,name,request_mask):
        return release_pose_bank(self.entries,self.banks[name],request_mask,self.clear_auxiliary)

    def cleanup(self,output,input):
        def resolve(spec):
            self._uint(spec['flags'],255,'wrapper flags');self._uint(spec['index'],65535,'request mask')
            self._uint(spec['header'],0xffffffff,'wrapper header')
            return dict(deepcopy(spec),component=dict(pool=self.entries),
                primary=self.banks[spec['primary']] if spec['primary'] is not None else None,
                alternate=self.banks[spec['alternate']] if spec['alternate'] is not None else None)
        out,inp=resolve(output),resolve(input)
        cleanup_pose_work_wrappers(out,inp,
            lambda pool,bank,mask:release_pose_bank(pool,bank,mask,self.clear_auxiliary),self.free_storage)
        return [dict(primary=None,alternate=None,flags=w['flags'],storage=w['storage'],header=w['header'],index=w['index']) for w in (out,inp)]


def run(document):
    if document.get('schema')!='animation-pool-session-v1':raise ValueError('animation-pool-session-v1 schema required')
    policy=document.get('service_policy')
    if policy not in ('record_calls_without_pose_copy','copy_supplied_pose_bytes'):
        raise ValueError('explicit supported service policy required')
    operations=document['operations']
    if not isinstance(operations,list) or not 1<=len(operations)<=256:raise ValueError('provide 1..256 operations')
    events=[]
    def copy_selected(dst,src,mode,mask):
        executed=policy=='copy_supplied_pose_bytes'
        result=None
        if executed:
            from reference.animation_bank_copy import copy_pose_bank
            source=document['sources'][src]
            for bank in (source,dst):
                for key in ('data','parent_header'):
                    values=bank[key]
                    if not isinstance(values,list) or len(values)>1048576 or any(type(x) is not int or not 0<=x<=255 for x in values):
                        raise ValueError('bounded byte arrays required for supplied pose copy')
            result=copy_pose_bank(dst,source,mode,mask)
            dst['parent_header']=list(dst['parent_header'])
        events.append(dict(service='copy_selected',destination=session.name(dst),source=src,
            mode=mode,request_mask=mask,executed=executed,result=result))
    def clear_auxiliary(bank):events.append(dict(service='clear_auxiliary',bank=session.name(bank),executed=False))
    def free_storage(storage):events.append(dict(service='free_storage',storage=storage,executed=False))
    session=AnimationPoolSession(document['banks'],document['entries'],copy_selected=copy_selected,
        clear_auxiliary=clear_auxiliary,free_storage=free_storage)
    results=[]
    for op in operations:
        start=len(events)
        if op['op']=='acquire':result=session.acquire(op['request_mask'],op['representation'],op['mode'],op['source'])
        elif op['op']=='release':result=dict(matched=session.release(op['bank'],op['request_mask']))
        elif op['op']=='cleanup':result=session.cleanup(op['output'],op['input'])
        else:raise ValueError('unknown pool operation')
        results.append(dict(operation=op['op'],result=result,services=deepcopy(events[start:]),state=session.snapshot()))
    digest=hashlib.sha256(json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return dict(schema='animation-pool-session-result-v1',input_sha256=digest,operations=results,
        evidence='offline reconstructed ownership rules with caller-supplied synthetic state',
        limitations=[('pose copy only recorded' if policy=='record_calls_without_pose_copy' else 'pose copy executes on supplied bytes; no live memory access'),
                     'auxiliary clearing and storage free only recorded',
                     'allocation misses are explicit; no allocation substitute',
                     'not a game capture, scheduler or live lifetime guarantee'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:text=json.dumps(run(json.loads(args.input.read_text())),indent=2,allow_nan=False)+'\n'
    except (ValueError,TypeError,KeyError,OverflowError) as exc:parser.error(str(exc))
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__=='__main__':main()
