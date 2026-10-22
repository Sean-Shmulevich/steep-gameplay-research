"""Owner-transform preparation for guarded skeleton refresh.

Evidence: CENTRAL_IMPULSE.md, Owner transform supplies guarded-refresh bank parents.
Caller supplies the resolved owner matrix. No accessor call, refresh, lock,
world-space assertion or object lifetime guarantee is implemented here.
"""
from reference.ground_response_pose import entity_pose_transform


def prepare_skeleton_parent_transform(basis_rows, position):
    """Convert supplied owner basis and clear translation W, with native f32 order.

    This path does not use the entity's separate stored scalar. Matrix-to-quaternion
    branching is shared with entity_pose_transform; no normalization is added.
    """
    converted=entity_pose_transform(basis_rows,position,0.)
    return dict(parent_position=converted['position_scalar'],
                parent_rotation=converted['rotation'],rotation_branch=converted['branch'])


def prepare_reset_parent_transform(basis_rows, position):
    """Prepare the separate reset-parent path, which explicitly writes W=1.

    Evidence: CENTRAL_IMPULSE.md, Reset-parent writers explicitly use W one.
    Do not substitute this for the guarded-refresh W=0 preparation.
    """
    converted=entity_pose_transform(basis_rows,position,1.)
    return dict(parent_position=converted['position_scalar'],
                parent_rotation=converted['rotation'],rotation_branch=converted['branch'])


def reset_configured_parent_slots(basis_rows, position, slots, reset_parent):
    """Reset two ordered optional banks through a supplied reset service.

    Evidence: CENTRAL_IMPULSE.md, Supplied-matrix slot reset and caller order.
    None denotes a null native slot. Aliases are deliberately visited twice.
    reset_parent(bank, prepared_parent) must perform the bank reset; this wrapper
    does not invent record defaults, locking, allocation or scheduler timing.
    """
    if len(slots) != 2:
        raise ValueError('exactly two configured slots required')
    parent=prepare_reset_parent_transform(basis_rows,position)
    for bank in slots:
        if bank is not None:
            reset_parent(bank,parent)
    return parent


def publish_nonreset_owner_parent(basis_rows, position, bank, set_parent):
    """Publish owner-derived XYZ/W=1 and rotation without resetting bank records.

    Evidence: CENTRAL_IMPULSE.md, Non-reset writer also publishes W one.
    This is the local publication slice only. The caller must resolve the owner
    matrix and destination bank after the surrounding selection/preparation.
    set_parent(bank, prepared, False) is an explicit service, not a native call.
    """
    parent = prepare_reset_parent_transform(basis_rows, position)
    set_parent(bank, parent, False)
    return parent


def select_and_publish_owner_parent(state, *, acquire, prepare, resolve_owner,
                                    set_parent, process):
    """Reconstruct the alternate-bank wrapper with explicit service boundaries.

    Banks are mutable mappings with uint32 flags. state contains primary,
    alternate (or None), request_byte, and component with pool and flags16.
    Services may mutate state; reload points follow the inspected instructions.
    Evidence: CENTRAL_IMPULSE.md, Alternate-bank selection and publication gates.
    Acquisition is required to return a valid bank; null native results are not
    safely handled by the original path. No allocation or processing is invented.
    """
    created = False
    if state['primary']['flags'] & (1 << 26) and state['alternate'] is None:
        bank = acquire(state['component']['pool'], 0xffff, state['request_byte'] & 1)
        if bank is None:
            raise ValueError('acquisition must supply a valid alternate bank')
        bank['flags'] &= ~(1 << 26)
        state['alternate'] = bank
        created = True
    destination, source = state['primary'], state['alternate']
    if destination['flags'] & (1 << 26):
        destination, source = source, destination
    if not created and (source is None or not source['flags'] & (1 << 27)):
        return destination
    prepare(state, source)
    basis, position = resolve_owner(state['component'])
    publish_nonreset_owner_parent(basis, position, destination, set_parent)
    process(destination, source, (state['component']['flags16'] >> 3) & 7)
    return destination


def query_remapped_parent_bank(remap, index, state, *, select_bank, read_pose,
                               default_pair):
    """Query two stored pose lanes after potentially mutating bank selection.

    Evidence: CENTRAL_IMPULSE.md, Remapped pose queries can publish parent state.
    index and remap entries are uint16. 65535 returns caller-supplied defaults
    without touching state. Otherwise select_bank(state) runs before read_pose.
    The services and default payloads stay explicit; this is not a passive API.
    Bounds/type rejection is authored safety beyond native unchecked indexing.
    """
    if type(index) is not int or not 0 <= index <= 65535:
        raise ValueError('index must be uint16')
    if index == 65535:
        return default_pair
    mapped = remap[index]
    if type(mapped) is not int or not 0 <= mapped <= 65535:
        raise ValueError('mapped index must be uint16')
    if mapped == 65535:
        return default_pair
    return read_pose(select_bank(state), mapped)


def publish_pose_work_result(component, output_wrapper, current_snapshot, mode,
                             *, succeeded, select_bank, copy_selected, copy_primary):
    """Publish one successful work callback's output into its captured bank.

    Evidence: CENTRAL_IMPULSE.md, Stack work wrappers and output publication.
    Caller supplies the callback result and current bank captured before it ran.
    The primary bank is instead reloaded after copy_selected. Both copy routines
    remain explicit services; this does not reconstruct their internal semantics.
    """
    if not succeeded:
        return
    selected = select_bank(output_wrapper)
    copy_selected(current_snapshot, selected, mode, 65535)
    copy_primary(current_snapshot, component['primary'], mode)


def initialize_pose_work_descriptors(component, current_bank, input_flags, output_flags):
    """Describe fields initialized for the two call-scoped work wrappers.

    Evidence: CENTRAL_IMPULSE.md, Work-wrapper initialization contract.
    The upper five flag bits survive initialization; scratch bytes are untouched.
    Each native scratch pointer addresses its own inline storage. Python models
    that relationship by a label, not by inventing initialized scratch contents.
    The header is retained as an opaque encoded value pending field semantics.
    """
    for value in (input_flags, output_flags):
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('prior wrapper flags must be uint8')
    def descriptor(bank, flags):
        return dict(component=component, primary=bank, alternate=None,
                    storage='own_inline_scratch', header=32772,
                    index=65535, flags=flags & 248)
    return dict(input=descriptor(current_bank,input_flags),
                output=descriptor(None,output_flags))


def prepare_owner_scaled_bank(state, bank, get_owner_scalar):
    """Apply the owner's stored scalar once per wrapper preparation flag.

    Evidence: CENTRAL_IMPULSE.md, Owner-scalar bank preparation.
    Mutable eight-lane records retain aliasing. Only their first four lanes scale.
    Bank mappings supply primary_records/primary_count and secondary_records/
    secondary_count; caller must provide sufficient storage. No unit or body-size
    semantics are inferred from the scalar's storage location.
    """
    from reference.central_impulse import f32
    if state['request_byte'] & 2:
        return bank
    scalar=f32(get_owner_scalar())
    if not abs(f32(scalar-f32(1.))) <= f32(1e-5):
        if bank['primary_count']:
            for field,count in (('primary_records','primary_count'),
                                ('secondary_records','secondary_count')):
                for i in range(bank[count]):
                    record=bank[field][i]
                    for lane in range(4):
                        record[lane]=f32(f32(record[lane])*scalar)
    state['request_byte'] |= 2
    return bank


def remove_owner_bank_scale(state, bank, get_owner_scalar):
    """Apply current owner reciprocal and clear the wrapper preparation bit.

    Evidence: CENTRAL_IMPULSE.md, Reciprocal bank preparation and round trips.
    The current scalar is read anew; no earlier scalar is remembered. The shared
    scaling helper tests the reciprocal against one a second time. Record aliasing
    remains observable. This operation is not guaranteed to invert prior work.
    """
    import math
    from reference.central_impulse import f32
    if not state['request_byte'] & 2:
        return bank
    scalar=f32(get_owner_scalar())
    if not abs(f32(scalar-f32(1.))) <= f32(1e-5):
        reciprocal=f32(1./scalar) if scalar else math.copysign(math.inf,scalar)
        prepare_owner_scaled_bank({'request_byte':0},bank,lambda:reciprocal)
    state['request_byte'] &= ~2
    return bank


def select_converted_owner_bank(state, *, acquire, convert):
    """Select the opposite bank representation and consume source-ready flags.

    Evidence: CENTRAL_IMPULSE.md, Opposite bank selection and flag lifecycle.
    Conversion remains a supplied service. Unlike parent publication, acquisition
    uses state.index and does not clear the acquired bank's bit 26.
    """
    created=False
    if not state['primary']['flags'] & (1 << 26) and state['alternate'] is None:
        bank=acquire(state['component']['pool'],state['index'],state['request_byte'] & 1)
        if bank is None:
            raise ValueError('acquisition must supply a valid alternate bank')
        state['alternate']=bank
        created=True
    destination,source=state['primary'],state['alternate']
    if not destination['flags'] & (1 << 26):
        destination,source=source,destination
    mode=(state['component']['flags16'] >> 3) & 7
    if created or (source is not None and source['flags'] & (1 << 27)):
        convert(source,destination,mode)
        state['request_byte'] |= 2
        source['flags'] &= ~(1 << 27)
        destination['flags'] &= ~(1 << 27)
    return destination


def publish_volume_spawn_transform(state, prepare, publish):
    """Reconstruct the volume spawn publication gate with explicit services.

    state['publication_state'] models the native unsigned 32-bit word.
    prepare(state) may change it; publish(state) sees that change. Clear follows
    successful publication. This is not a general animation/physics tick hook.
    Evidence: CENTRAL_IMPULSE.md, Spawn-position caller identity and gate.
    """
    word=state['publication_state']
    if not isinstance(word,int) or not 0 <= word <= 0xffffffff:
        raise ValueError('publication_state must be uint32')
    if word == 0:
        prepare(state)
    publish(state)
    state['publication_state']=0


def publish_player_spawn_transform(state, owner, *, get_provider, get_context,
                                   configure, read_position, read_rotation, publish):
    """Player spawn wrapper with all unresolved virtual services explicit.

    Evidence: CENTRAL_IMPULSE.md, Player spawn provider refresh ordering.
    None is an absent provider. The owner is required by the native path; this
    API does not invent an owner-null fallback. Position uses the first three
    returned lanes; rotation copies four lanes without normalization.
    Publication still occurs when no provider exists.
    """
    from reference.central_impulse import f32
    provider=get_provider(owner)
    if provider is not None:
        context=get_context(owner)
        configure(provider,context,0)
        position=read_position(provider)
        state['position']=tuple(f32(position[i]) for i in range(3))+(0.,)
        rotation=read_rotation(provider)
        state['rotation']=tuple(f32(rotation[i]) for i in range(4))
    publish(state)


def resolve_spawn_position(position, parent_matrix=None):
    """Pre-publication position branch; parent availability is caller-resolved.

    Uses z*row2 + translation, then y*row1, then x*row0, rounded at each
    operation. Parent branch clears W; absent-parent branch copies all lanes.
    Evidence: CENTRAL_IMPULSE.md, Spawn parent coordinate conversion.
    """
    from reference.central_impulse import f32
    p=tuple(map(f32,position))
    if len(p)!=4:raise ValueError('four position lanes required')
    if parent_matrix is None:return p
    m=tuple(tuple(map(f32,row)) for row in parent_matrix)
    if len(m)!=4 or any(len(row)!=4 for row in m):raise ValueError('4x4 parent required')
    return tuple(f32(f32(f32(f32(p[2]*m[2][i])+m[3][i])+
                           f32(p[1]*m[1][i]))+f32(p[0]*m[0][i])) for i in range(3))+(0.,)


def resolve_spawn_rotation(rotation, parent_matrix=None, *, matrix_template=None):
    """Parent-relative rotation conversion, before publisher normalization.

    Default template matches the recovered identity initializer. Explicit templates
    permit other observed states; immutability in a running game is not assumed.
    Parentless branch copies the quaternion without normalization or template use.
    Evidence: CENTRAL_IMPULSE.md, Spawn parent coordinate conversion.
    """
    from reference.central_impulse import f32 as f
    q=tuple(map(f,rotation))
    if len(q)!=4:raise ValueError('four rotation lanes required')
    if parent_matrix is None:return q
    if matrix_template is None:
        matrix_template=tuple(tuple(float(i==j) for j in range(4)) for i in range(4))
    m=tuple(tuple(map(f,row)) for row in parent_matrix)
    local=[list(map(f,row)) for row in matrix_template]
    if len(m)!=4 or any(len(row)!=4 for row in m) or len(local)!=4 or any(len(row)!=4 for row in local):
        raise ValueError('4x4 parent and template required')
    x,y,z,w=q;xx=f(x*f(x+x));xy=f(y*f(x+x));xz=f(z*f(x+x));wx=f(w*f(x+x))
    yy=f(y*f(y+y));yz=f(z*f(y+y));wy=f(w*f(y+y));zz=f(z*f(z+z));wz=f(w*f(z+z))
    basis=((f(f(1.-yy)-zz),f(wz+xy),f(xz-wy)),
           (f(xy-wz),f(f(1.-xx)-zz),f(yz+wx)),
           (f(wy+xz),f(yz-wx),f(f(1.-xx)-yy)))
    for i in range(3):local[i][:3]=basis[i]
    composed=tuple(tuple(f(f(f(f(local[i][0]*m[0][j])+f(local[i][1]*m[1][j]))+
                           f(local[i][2]*m[2][j]))+f(local[i][3]*m[3][j])) for j in range(4)) for i in range(4))
    return entity_pose_transform(composed[:3],composed[3],0.)['rotation']


def build_spawn_publication_matrix(position, rotation, reciprocal_sqrt, *, matrix_template=None):
    """Final publication arithmetic with an explicit hardware-estimate service.

    Inputs are the already resolved position/quaternion. This function models
    one reciprocal-square-root refinement, not exact mathematical normalization.
    Finite nonzero quaternions are required by this authored numerical API.
    Evidence: CENTRAL_IMPULSE.md, Spawn publication matrix normalization.
    """
    import math
    from reference.central_impulse import f32 as f
    q=tuple(map(f,rotation));p=tuple(map(f,position))
    if len(q)!=4 or len(p)!=4 or not all(math.isfinite(v) for v in q+p):
        raise ValueError('finite four-lane position and rotation required')
    squares=tuple(f(v*v) for v in q)
    norm=f(f(squares[0]+squares[2])+f(squares[1]+squares[3]))
    if not math.isfinite(norm) or norm<=0:raise ValueError('positive finite squared norm required')
    estimate=f(reciprocal_sqrt(norm))
    if not math.isfinite(estimate) or estimate<=0:raise ValueError('positive finite reciprocal estimate required')
    factor=f(f(3.-f(f(estimate*norm)*estimate))*f(.5*estimate))
    x,y,z,w=normalized=tuple(f(factor*v) for v in q)
    xx=f(x*f(x+x));xy=f(y*f(x+x));xz=f(z*f(x+x));wx=f(w*f(x+x))
    yy=f(y*f(y+y));yz=f(z*f(y+y));wy=f(w*f(y+y));zz=f(z*f(z+z));wz=f(w*f(z+z))
    if matrix_template is None:matrix_template=tuple(tuple(float(i==j) for j in range(4)) for i in range(4))
    matrix=[list(map(f,row)) for row in matrix_template]
    if len(matrix)!=4 or any(len(row)!=4 for row in matrix):raise ValueError('4x4 template required')
    basis=((f(f(1.-yy)-zz),f(wz+xy),f(xz-wy)),
           (f(xy-wz),f(f(1.-xx)-zz),f(yz+wx)),
           (f(wy+xz),f(yz-wx),f(f(1.-xx)-yy)))
    for i in range(3):matrix[i][:3]=basis[i]
    matrix[3]=list(p[:3]) + [1.]
    return dict(matrix=tuple(tuple(row) for row in matrix),normalized_rotation=normalized,
                squared_norm=norm,reciprocal_estimate=estimate)


def publish_spawn_entity_transform(entity, transform, *, derived, propagate_linked=None,
                                   **base_services):
    """Join spawn packet flags to recovered base/derived entity dispatch.

    derived must be selected from evidence about the receiver, never guessed.
    Both packet matrix fields alias transform; flags are fixed at 31. The linked
    service runs after base update restores its incoming logical lock depth.
    Evidence: CENTRAL_IMPULSE.md, Spawn entity publication dispatch variants.
    """
    from reference.entity_transform_update import update_entity_transform
    if type(derived) is not bool:raise ValueError('explicit derived dispatch selection required')
    if derived and not callable(propagate_linked):
        raise NotImplementedError('derived entity requires linked-transform service')
    if 'flags' in base_services:raise ValueError('spawn publication flags are fixed at 31')
    update_entity_transform(entity,transform,flags=31,**base_services)
    if derived:
        propagate_linked(entity,transform,transform,31)


def propagate_linked_spawn_transforms(state, packet, *, resolve, target_flags,
                                      acquire_descriptor, descriptor_blocks,
                                      release_descriptor, dispatch):
    """Ordered linked-target propagation with live list/count reloads.

    state has links and local_transforms lists; packet has first, second and
    flags. acquire_descriptor returns (descriptor, cleanup_token). The predicate
    tests descriptor, while release receives cleanup_token, before dispatch.
    Services may replace state lists. This model retains Python objects, not
    native object lifetime. Service exceptions propagate with authored cleanup.
    Evidence: CENTRAL_IMPULSE.md, Linked spawn transform propagation loop.
    """
    from reference.transform_composition import compose_transform
    def count():
        links=state['links']
        if type(links) is not list or len(links)>65535:raise ValueError('uint16-sized links list required')
        return len(links)
    index=0
    while index<count():
        target=resolve(state['links'][index])
        if target is not None and not target_flags(target)&1:
            descriptor,cleanup=acquire_descriptor(target)
            try:
                blocked=descriptor_blocks(descriptor)
            finally:
                release_descriptor(cleanup)
            if not blocked:
                flags=packet['flags']
                if type(flags) is not int or not 0<=flags<=0xffffffff:raise ValueError('uint32 flags required')
                second=compose_transform(packet['second'],state['local_transforms'][index])
                first=compose_transform(packet['first'],state['local_transforms'][index])
                dispatch(target,dict(first=first,second=second,flags=flags))
        index+=1
    return True


def linked_spawn_descriptor_blocks(descriptor, visibility_mask):
    """Reuse recovered descriptor validity as this loop's skip predicate.

    descriptor contains mode/index and first/second target/status observations.
    visibility_mask() is called only for mode 1 or non-sentinel mode 2. Validity
    causes this linked pass to skip; it does not establish target lifetime.
    Evidence: CENTRAL_IMPULSE.md, Linked descriptor visibility and ownership join.
    """
    from reference.transform_accessor_unlink import descriptor_is_valid
    mode=descriptor['mode'];index=descriptor['index']
    selected=mode==1 or (mode==2 and index!=65535)
    return descriptor_is_valid(**descriptor,tls_mask=visibility_mask() if selected else 0)


def publish_spawn_pose(state, *, get_entity, read_parent, reciprocal_sqrt,
                       publish_entity, find_skeleton, reset_parent,
                       matrix_template=None):
    """Joined shared spawn publisher with explicit engine services.

    read_parent(state, phase) resolves separately for 'position' and 'rotation'.
    publish_entity(entity, matrix) completes before find_skeleton(entity), which
    returns None or a mapping with two 'slots'. Reset uses the same matrix.
    Evidence: CENTRAL_IMPULSE.md, Joined spawn publication service pipeline.
    No native object lifetime, scheduling or rollback guarantee is provided.
    """
    entity=get_entity(state)
    position=resolve_spawn_position(state['position'],read_parent(state,'position'))
    rotation=resolve_spawn_rotation(state['rotation'],read_parent(state,'rotation'),
                                    matrix_template=matrix_template)
    prepared=build_spawn_publication_matrix(position,rotation,reciprocal_sqrt,
                                             matrix_template=matrix_template)
    matrix=prepared['matrix']
    publish_entity(entity,matrix)
    skeleton=find_skeleton(entity)
    if skeleton is not None:
        reset_configured_parent_slots(matrix[:3],matrix[3],skeleton['slots'],reset_parent)
    return prepared


def reset_animation_bank_parent(bank, parent, reset, get_default_pose):
    """Copy parent and optionally reset active records using supplied defaults.

    bank has parent/default_pose bytes, records list, count and reset_word.
    get_default_pose abstracts the observed TLS initialization check and globals;
    it is queried for the bank default and for each record, not cached here.
    Evidence: CENTRAL_IMPULSE.md, Nonempty animation bank reset.
    Bytes/list storage and validation errors are authored reconstruction behavior.
    """
    if type(parent) is not bytes or len(parent)!=32:raise ValueError('32-byte parent required')
    if type(reset) is not bool:raise ValueError('boolean reset required')
    bank['parent']=parent
    if not reset:return
    def default():
        pose=get_default_pose()
        if type(pose) is not bytes or len(pose)!=32:raise ValueError('32-byte default pose required')
        return pose
    bank['default_pose']=default()
    i=0
    while True:
        count=bank['count']
        if type(count) is not int or not 0<=count<=65535:raise ValueError('uint16 count required')
        if i>=count:break
        pose=default()
        bank['records'][i]=pose
        i+=1
    bank['reset_word']=0


def publish_cached_parent_prefix(component, *, before_publish, set_parent):
    """Cached-parent prefix only; downstream animation processing is excluded.

    component has primary, current and cached_parent. before_publish is None or
    a supplied already-gated callback; callback selection/holder checks remain
    outside this model. Each bank and cached pose is read after the callback.
    Evidence: CENTRAL_IMPULSE.md, Cached parent callback publication boundary.
    """
    if component['primary'] is None:return False
    if before_publish is not None:before_publish(component)
    set_parent(component['primary'],component['cached_parent'],False)
    set_parent(component['current'],component['cached_parent'],False)
    return True


def cached_parent_callback_gate(*, primary_present, storage_word, tagged_context,
                                holder_status, holder_target):
    """Recovered callback eligibility; this path does not use a TLS mask.

    Numeric context/target values are supplied observations, not dereferenced
    pointers. A true result does not validate a function pointer or object life.
    Evidence: CENTRAL_IMPULSE.md, Cached parent callback gate.
    """
    if type(primary_present) is not bool:raise ValueError('boolean primary presence required')
    for value in (storage_word,tagged_context,holder_target):
        if type(value) is not int or not 0<=value<2**64:raise ValueError('uint64 registration fields required')
    if type(holder_status) is not int or not 0<=holder_status<2**32:raise ValueError('uint32 status required')
    context=tagged_context&0xfffffffffffffffc
    invoked=primary_present and bool(storage_word or context) and bool(holder_status&0x80000000) and bool(holder_target)
    return dict(invoked=invoked,forwarded_context=context if invoked else None)


def select_owner_scaled_bank(state, *, acquire, convert, get_owner_scalar):
    """Select relative representation, then conditionally apply owner scale.

    Evidence: CENTRAL_IMPULSE.md, Selection followed by owner scaling.
    Conversion may set request bit 1, suppressing the subsequent scalar read.
    Bank storage uses prepare_owner_scaled_bank's primary/secondary array schema;
    the supplied converter must update that same storage.
    """
    bank=select_converted_owner_bank(state,acquire=acquire,convert=convert)
    return prepare_owner_scaled_bank(state,bank,get_owner_scalar)
