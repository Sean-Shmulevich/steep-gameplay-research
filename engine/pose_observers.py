"""Serial pose observer dispatch with explicit callback services.

Evidence: CENTRAL_IMPULSE.md, Pose observer dispatch and deferred compaction.
Registry dictionaries have count and slots of 16-byte records. Callback token
is the first uint64; enabled is byte8. Storage and services remain caller-owned.
"""
import struct


def dispatch_pose_observers(body, value, *, get_registry, thread_state, invoke):
    """Normal-return ordering only; no concurrency, lifetime pin or rollback.

    Callbacks may replace the registry or change its count/records. Reentrant
    behavior is not made safe here: active is a byte, not a nesting depth.
    """
    if type(body) is not int or not 0<=body<=0xffffffffffffffff:
        raise ValueError('Raw uint64 body token required')
    if type(value) is not int or not 0<=value<=0xffffffff:
        raise ValueError('Raw uint32 value required')
    def check(registry):
        count=registry['count']
        if type(count) is not int or not 0<=count<0x80000000 or count>len(registry['slots']):
            raise ValueError('Retained bounded registry required')
        return registry
    def record(registry,index):
        entry=registry['slots'][index]
        if len(entry)!=16:raise ValueError('16-byte observer record required')
        return entry
    registry=check(get_registry());thread_state['active']=1
    index=0;called=[];removed=[]
    while index<registry['count']:
        entry=record(registry,index)
        if entry[8]:
            token=struct.unpack_from('<Q',entry)[0]
            invoke(token,body,value)
            called.append(token)
            registry=check(get_registry())
        index+=1
    thread_state['active']=0
    if thread_state['deferred_cleanup']:
        for index in range(registry['count']-1,-1,-1):
            if not record(registry,index)[8]:
                registry['count']-=1
                count=registry['count']
                # Native memmove shifts only the active suffix; inactive tail stays.
                registry['slots'][index:count]=registry['slots'][index+1:count+1]
                removed.append(index)
                registry=check(get_registry())
        thread_state['deferred_cleanup']=0
    return dict(called=called,removed_indices=removed)


def register_pose_observer(registry, token, *, padding, grow):
    """Append an enabled record, preserving supplied seven stack-padding bytes.

    Growth is supplied; duplicate/null tokens are not filtered by native code.
    No callable-token validation or module retention is implied.
    """
    if type(token) is not int or not 0<=token<=0xffffffffffffffff:
        raise ValueError('Raw uint64 callback token required')
    if len(padding)!=7:raise ValueError('Seven explicit padding bytes required')
    count,capacity=registry['count'],registry['capacity']
    if not 0<=count<=capacity<=0xffffffff:raise ValueError('Valid registry counts required')
    if count==capacity:
        grow(registry,8 if capacity==0 else (capacity*2)&0xffffffff)
    count=registry['count']
    if not 0<=count<len(registry['slots']):
        raise ValueError('Growth service must provide retained writable storage')
    registry['slots'][count]=struct.pack('<QB',token,1)+bytes(padding)
    registry['count']=(count+1)&0xffffffff


def unregister_pose_observer(registry, token, *, thread_state):
    """Remove the first matching token; retained membership is a precondition.

    A missing token raises before mutation as an authored guard. The inspected
    native function has no not-found guard and would use index uint32(-1).
    """
    if type(token) is not int or not 0<=token<=0xffffffffffffffff:
        raise ValueError('Raw uint64 callback token required')
    count=registry['count']
    if not 0<=count<0x80000000 or count>len(registry['slots']):
        raise ValueError('Retained bounded registry required')
    found=None
    for index in range(count):
        entry=registry['slots'][index]
        if len(entry)!=16:raise ValueError('16-byte observer record required')
        if struct.unpack_from('<Q',entry)[0]==token:
            found=index;break
    if found is None:raise ValueError('Callback membership required')
    if thread_state['active']:
        entry=registry['slots'][found]
        registry['slots'][found]=entry[:8]+b'\x00'+entry[9:]
        thread_state['deferred_cleanup']=1
    else:
        registry['count']=count-1
        registry['slots'][found:count-1]=registry['slots'][found+1:count]
    return found
