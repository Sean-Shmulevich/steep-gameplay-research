"""Exact contact-record sort policy; LINK_SOLVER.md, Contact record sort ordering."""
import struct


def compare_contact_details(first, second, key_width):
    if key_width not in (16,32):
        raise ValueError('Explicit 16 or 32 bit key width required')
    fmt='<H' if key_width==16 else '<I'
    a=struct.unpack_from(fmt,first,44)[0];b=struct.unpack_from(fmt,second,44)[0]
    difference=(a-b)&0xffffffff
    return difference if difference<0x80000000 else difference-0x100000000


def sort_contact_records(records, *, key_width):
    """Mutate record order using native partition and small-range swap policy.

    Whole48-byte records move. Equal-key order is not stable. The32-bit comparator
    uses wrapped signed subtraction, even where it is not a total ordering.
    """
    if key_width not in (16,32) or any(len(r)!=48 for r in records):
        raise ValueError('48-byte records and explicit key width required')
    def cmp(a,b):return compare_contact_details(records[a],records[b],key_width)
    def swap(a,b):records[a],records[b]=records[b],records[a]
    pending=[(0,len(records)-1)] if len(records)>1 else []
    while pending:
        low,high=pending.pop()
        while low<high:
            size=high-low+1
            if size<=8:
                while high>low:
                    maximum=low
                    for p in range(low+1,high+1):
                        if cmp(p,maximum)>0:maximum=p
                    swap(maximum,high);high-=1
                break
            middle=low+size//2
            if cmp(low,middle)>0:swap(low,middle)
            if cmp(low,high)>0:swap(low,high)
            if cmp(middle,high)>0:swap(middle,high)
            left,right=low,high
            while True:
                if left<middle:
                    left+=1
                    while left<middle and cmp(left,middle)<=0:left+=1
                if left>=middle:
                    left+=1
                    while left<=high and cmp(left,middle)<=0:left+=1
                while True:
                    previous_right=right
                    right-=1
                    if right<=middle or cmp(right,middle)<=0:break
                if right<left:break
                swap(left,right)
                if middle==right:middle=left
            end=previous_right
            if end>middle:
                end-=1
                while end>middle and cmp(end,middle)==0:end-=1
            if end<=middle:
                end-=1
                while end>low and cmp(end,middle)==0:end-=1
            if end-low>=high-left:
                if low<end:pending.append((low,end))
                if left>=high:break
                low=left
            else:
                if left<high:pending.append((left,high))
                if low>=end:break
                high=end
