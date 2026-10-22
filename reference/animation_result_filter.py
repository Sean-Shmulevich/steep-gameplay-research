"""Recovered result-tree pruning over supplied 24-byte records.

Evidence: CENTRAL_IMPULSE.md, Result-tree weight filtering.
Record names and bounds guards are authored. No clip or blend meanings inferred.
"""
import struct
from reference.snow import f32


def filter_result_records(records, threshold):
    records=[bytes(record) for record in records]
    if len(records)>65535 or any(len(r)!=24 for r in records):
        raise ValueError('bounded 24-byte records required')
    threshold=f32(threshold);output=[]
    def visit(start,count,depth):
        if depth>128:raise ValueError('inspection recursion limit exceeded')
        i=start;end=start+count
        while i<end:
            record=records[i];span=struct.unpack_from('<H',record,20)[0]
            if not span or i+span>end:raise ValueError('record span outside supplied range')
            weight=struct.unpack_from('<f',record,16)[0]
            if weight>threshold:  # unordered comparisons reject NaNs
                base=len(output);output.append(record)
                if record[22] in (1,3,5,7):
                    if span<2:raise ValueError('group requires opening and closing records')
                    visit(i+1,span-2,depth+1)
                    if len(output)>base+1:
                        output.append(records[i+span-1])
                        head=bytearray(output[base]);struct.pack_into('<H',head,20,len(output)-base)
                        output[base]=bytes(head)
                    else:del output[base:]
            i+=span
    visit(0,len(records),0)
    return output
