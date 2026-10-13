"""Bounded, nonwrapping owned-runtime event trace; no wall-clock causality claim.

Sequence numbers describe serial reconstructed execution only. Capacity loss is
explicit and invalidates completeness. No original-process hooks or addresses.
"""
import copy
from .assets import canonical

class Trace:
    def __init__(self,capacity=4096):
        if type(capacity) is not int or not 1<=capacity<=1000000:
            raise ValueError('Trace capacity must be 1..1000000')
        self.capacity=capacity;self.records=[];self.attempted=0;self.dropped=0
    def emit(self,kind,**fields):
        if not isinstance(kind,str) or not kind:
            raise ValueError('Trace kind must be a nonempty string')
        record=dict(sequence=self.attempted,kind=kind,**copy.deepcopy(fields))
        canonical(record)
        self.attempted+=1
        if len(self.records)<self.capacity:self.records.append(record)
        else:self.dropped+=1
    def snapshot(self):
        return copy.deepcopy(dict(schema_version=1,capacity=self.capacity,records=self.records,
                                  attempted=self.attempted,dropped=self.dropped,complete=self.dropped==0,
                                  scope='serial reconstructed execution; not original game events'))
    def excerpt_since(self, first_sequence, *, limit=64):
        """Copy a bounded tail from one attempted interval, with explicit loss.

        This excerpt is not a restorable Trace envelope. Original sequence values
        are preserved; callers must label the execution/generation it came from.
        """
        if type(first_sequence) is not int or not 0<=first_sequence<=self.attempted:
            raise ValueError('Invalid excerpt start sequence')
        if type(limit) is not int or not 1<=limit<=4096:
            raise ValueError('Excerpt record limit must be 1..4096')
        retained=[r for r in self.records if r['sequence']>=first_sequence]
        attempted=self.attempted-first_sequence
        dropped=attempted-len(retained)
        omitted=max(0,len(retained)-limit)
        return copy.deepcopy(dict(schema_version=1,first_sequence=first_sequence,
            next_sequence=self.attempted,attempted=attempted,records=retained[-limit:],
            dropped_at_capture=dropped,omitted_by_excerpt=omitted,
            complete=dropped==0 and omitted==0,
            scope='attempted owned trace interval; not committed state or native events'))
    @classmethod
    def restore(cls,snapshot):
        canonical(snapshot)
        trace=cls(snapshot['capacity'])
        records=snapshot['records'];attempted=snapshot['attempted'];dropped=snapshot['dropped']
        if snapshot.get('schema_version')!=1 or not isinstance(records,list) or len(records)>trace.capacity:
            raise ValueError('Invalid trace snapshot')
        if type(attempted) is not int or type(dropped) is not int or dropped<0 or attempted!=len(records)+dropped:
            raise ValueError('Invalid trace accounting')
        if dropped and len(records)!=trace.capacity:
            raise ValueError('Dropped trace must have filled capacity')
        if type(snapshot.get('complete')) is not bool or snapshot.get('complete')!=(dropped==0) or any(not isinstance(row,dict) or type(row.get('sequence')) is not int or row.get('sequence')!=i or not isinstance(row.get('kind'),str) or not row['kind'] for i,row in enumerate(records)):
            raise ValueError('Invalid trace sequence/completeness')
        trace.records=copy.deepcopy(records);trace.attempted=attempted;trace.dropped=dropped
        return trace
