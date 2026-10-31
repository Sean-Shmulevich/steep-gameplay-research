"""Body group reassignment before ordinary-group reactivation.

Evidence: docs/reconstruction/LINK_SOLVER.md, Body-event group transition.
"""
import struct


def transition_pose_body_group(context,body,*,context_token,body_token,metadata,
        predicate,remove_body,body_virtual8,obtain_group,reset_body,append_body,finalize):
    """Recover selection/control flow while exposing group operations as services.

    predicate(context_token,body_token)->raw byte; body_virtual8(body_token,1)
    returns a raw byte. remove/append/finalize receive appropriate object tokens.
    finalize(context_token,group_token) is always reached on normal return.
    """
    def meta():return metadata[struct.unpack_from('<Q',body,0x30)[0]]
    group=struct.unpack_from('<Q',body,0x10)[0]
    if meta()[0x52]&8:
        was_special=int(group==struct.unpack_from('<Q',context,0x410)[0])
        selected=predicate(context_token,body_token)&255
        if selected!=was_special:
            remove_body(context_token,body_token)
            if body_virtual8(body_token,1)&255:
                m=meta()
                if not struct.unpack_from('<H',m,0x50)[0]&0x8000:
                    target=struct.unpack_from('<Q',context,0x408)[0]
                elif m[0x52]&8 and predicate(context_token,body_token)&255:
                    target=struct.unpack_from('<Q',context,0x410)[0]
                else:
                    target=obtain_group(context_token)
                    if meta()[0x53]&15==2:reset_body(body_token)
                append_body(target,body_token)
            group=struct.unpack_from('<Q',body,0x10)[0]
    finalize(context_token,group)
