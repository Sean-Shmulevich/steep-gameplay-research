"""Controller-facing body listener gates, metadata writes and ordered calls.

Evidence: docs/reconstruction/LINK_SOLVER.md, Controller body-event routing.
"""
import struct


def dispatch_pose_body_controller_event(body,event,*,body_token,metadata,owners,
                                        controllers,invoke):
    """Known listener routing; invoke(operation,*tokens) supplies callee effects.

    Operations: enter/leave(sync_token), group_transition(controller,body),
    refresh_body(body), body_virtual28(body), controller_virtuala8(object,bool),
    get_tree(provider)->tree, remove_tree(tree,body), provider_event4/5(provider,body),
    controller_event6/7/8/9(controller,body). No exception/locking policy is invented.
    """
    event &= 0xffffffff
    if 10<=event<=12:return
    def meta():return metadata[struct.unpack_from('<Q',body,0x30)[0]]
    owner=owners[struct.unpack_from('<Q',meta(),0x20)[0]]
    token=struct.unpack_from('<Q',owner,0x20)[0]
    if not token:return
    controller=controllers[token]
    invoke('enter',token+0x50)
    def priority():return bool(struct.unpack_from('<H',meta(),0x50)[0]&0x8000)
    def group():invoke('group_transition',token,body_token)
    def announce():
        # Metadata and controller's target are reloaded after preceding callbacks.
        target=struct.unpack_from('<Q',controller,0x28)[0]
        invoke('controller_virtuala8',target,int(not priority()))
    if event==0:
        m=meta()
        if not struct.unpack_from('<H',m,0x50)[0]&0x8000:
            stamp=struct.unpack_from('<I',controller,0x4c)[0]
            if struct.unpack_from('<I',m,0x1c)[0]!=stamp:
                struct.pack_into('<I',m,0x1c,stamp)
                invoke('refresh_body',body_token)
        elif m[0x53]&15==2:
            group();invoke('refresh_body',body_token)
        announce()
    elif event==1:
        if priority():
            if meta()[0x53]&15==2:group()
            else:invoke('body_virtual28',body_token)
        announce()
    elif event==2:group()
    elif event==3:
        if meta()[0x52]&8:
            tree=invoke('get_tree',struct.unpack_from('<Q',controller,0x20)[0])
            invoke('remove_tree',tree,body_token)
    elif event in (4,5):
        if not meta()[0x52]&1:
            invoke('provider_event'+str(event),struct.unpack_from('<Q',controller,0x20)[0],body_token)
    elif 6<=event<=9:invoke('controller_event'+str(event),token,body_token)
    invoke('leave',token+0x50)
