"""Caller-policy assembly of independently supplied base/addon rigs.

Research: docs/systems/animations/{skeleton,equipment,pose-assembly}/CLIENT_GUIDE.txt.
Those establish separate addon resources, hash-based channel identities and local
parent transforms, but NOT original duplicate/attachment merge semantics. Every
merge policy here is a designed adapter. No CRC spelling implies unique identity.

assemble(base, addons, policy=...) accepts animation.py rig dictionaries. Addons
are [{'id': 'gear', 'rig': rig}, ...]. Policy is REQUIRED and contains match_by
('name' or 'binding_hash'), duplicates ('error', 'reuse_identical', 'reuse_existing'),
and roots ('keep' or 'attach'). Attach mode additionally supplies attachments,
e.g. {'gear': {'name': 'hand'}} selecting a joint already assembled before gear.
Root local transforms are retained relative to their selected parent, NOT rebased
from model space. Only caller-supplied hash integers are used; none are generated.

Output contains rig, source_to_assembled, name_to_index, hash_to_indices and
ordered diagnostics. Error carries diagnostics. Inputs are never mutated.
"""
import copy
import math


class AssemblyError(ValueError):
    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = copy.deepcopy(diagnostics or [])


def _fail(message, diagnostics):
    raise AssemblyError(message, diagnostics)


def _validate(rig):
    bones = rig.get('bones')
    if not isinstance(bones, list) or not bones:
        raise AssemblyError('rig needs nonempty bones')
    for i, bone in enumerate(bones):
        if not isinstance(bone.get('name'), str) or not bone['name']:
            raise AssemblyError('bone needs a nonempty name')
        parent = bone.get('parent_index')
        if type(parent) is not int or parent < -1 or parent >= len(bones):
            raise AssemblyError('invalid parent index')
        h = bone.get('binding_hash')
        if h is not None and (type(h) is not int or not 0 <= h <= 0xffffffff):
            raise AssemblyError('binding_hash must be an unsigned 32-bit integer')
        pose = bone.get('local_bind', {})
        for field, size in [('translation', 3), ('quaternion_xyzw', 4)]:
            vec = pose.get(field)
            if not isinstance(vec, (tuple, list)) or len(vec) != size:
                raise AssemblyError('invalid local bind vector')
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in vec):
                raise AssemblyError('nonfinite local bind vector')
        if sum(v*v for v in pose['quaternion_xyzw']) < 1e-20:
            raise AssemblyError('zero bind quaternion')
    # Stable topological order: repeatedly emit available original indices.
    order, visited = [], set()
    while len(order) < len(bones):
        ready = [i for i,b in enumerate(bones) if i not in visited and
                 (b['parent_index'] == -1 or b['parent_index'] in visited)]
        if not ready:
            raise AssemblyError('cyclic skeleton hierarchy')
        order.extend(ready)
        visited.update(ready)
    return order


def _same_pose(a, b):
    if any(abs(x-y) > 1e-6 for x,y in zip(a['translation'], b['translation'])):
        return False
    qa, qb = a['quaternion_xyzw'], b['quaternion_xyzw']
    # Sign equivalence only; do not silently erase differences in stored lengths.
    return min(max(abs(x-y) for x,y in zip(qa,qb)),
               max(abs(x+y) for x,y in zip(qa,qb))) <= 1e-6


def assemble(base, addons, *, policy):
    """Assemble deterministically; explicit collision policy or a diagnostic error.

    reuse_identical requires parent and local-bind equivalence; reuse_existing
    discards the incoming duplicate's parent/bind under explicit caller authority,
    and records whether they differ. Aliased incoming names are retained in the
    source mapping and diagnostic, not silently inserted into the output rig.
    Source indices, not eventual hierarchy order, index source_to_assembled lists.
    """
    diagnostics = []
    if not isinstance(policy, dict):
        raise AssemblyError('explicit policy dictionary required')
    match = policy.get('match_by')
    duplicates = policy.get('duplicates')
    roots = policy.get('roots')
    if match not in ('name', 'binding_hash') or duplicates not in ('error', 'reuse_identical', 'reuse_existing') or roots not in ('keep', 'attach'):
        raise AssemblyError('explicit match_by, duplicates and roots policies required')
    if not isinstance(addons, list):
        raise AssemblyError('addons must be an ordered list')
    sources = [('base', base)]
    for addon in addons:
        label = addon.get('id')
        if not isinstance(label, str) or not label or label in [s[0] for s in sources]:
            raise AssemblyError('addon ids must be unique and cannot be base')
        sources.append((label, addon['rig']))
    # Validate every input before constructing results.
    orders = {label: _validate(rig) for label, rig in sources}
    output, mappings, lookup, names = [], {}, {}, {}
    for label, rig in sources:
        mapping = [None] * len(rig['bones'])
        mappings[label] = mapping
        attachment = -1
        if label != 'base' and roots == 'attach':
            selector = policy.get('attachments', {}).get(label)
            if not isinstance(selector, dict) or len(selector) != 1 or next(iter(selector)) not in ('name', 'binding_hash'):
                _fail('attach requires one explicit name/hash selector for ' + label, diagnostics)
            field, value = next(iter(selector.items()))
            matches = [i for i,b in enumerate(output) if b.get(field) == value]
            if len(matches) != 1:
                _fail('attachment selector must resolve exactly once: ' + label, diagnostics)
            attachment = matches[0]
        for index in orders[label]:
            incoming = rig['bones'][index]
            if match not in incoming or incoming[match] is None:
                _fail('missing matching identity: ' + match, diagnostics)
            key = incoming[match]
            source_parent = incoming['parent_index']
            parent = mapping[source_parent] if source_parent >= 0 else attachment
            if key in lookup:
                existing = lookup[key]
                target = output[existing]
                same = parent == target['parent_index'] and _same_pose(incoming['local_bind'], target['local_bind'])
                hash_disagrees = incoming.get('binding_hash') is not None and target.get('binding_hash') is not None and incoming['binding_hash'] != target['binding_hash']
                entry = dict(type='duplicate_identity', source=label, source_index=index,
                             assembled_index=existing, match_by=match, identity=key,
                             incoming_name=incoming['name'], retained_name=target['name'],
                             parent_and_bind_equivalent=same, hash_disagrees=hash_disagrees,
                             policy=duplicates)
                diagnostics.append(entry)
                # Duplicates within one source are malformed, not an addon policy.
                if existing in mapping:
                    _fail('duplicate identity within one source rig', diagnostics)
                if duplicates == 'error' or (duplicates == 'reuse_identical' and (not same or hash_disagrees)):
                    _fail('duplicate identity rejected by caller policy', diagnostics)
                mapping[index] = existing
                continue
            if incoming['name'] in names:
                diagnostics.append(dict(type='name_collision', source=label, source_index=index,
                                        name=incoming['name'], existing_index=names[incoming['name']]))
                _fail('distinct identities would produce duplicate output names', diagnostics)
            bone = copy.deepcopy(incoming)
            bone['parent_index'] = parent
            mapping[index] = len(output)
            lookup[key] = len(output)
            names[bone['name']] = len(output)
            output.append(bone)
            if source_parent == -1 and attachment >= 0:
                diagnostics.append(dict(type='root_attached', source=label, source_index=index,
                    parent_index=attachment, transform_policy='retain_local_relative_to_attachment'))
    # Cross-source hash aliases are observable even under name matching.
    hashes = {}
    for i, bone in enumerate(output):
        if bone.get('binding_hash') is not None:
            hashes.setdefault(str(bone['binding_hash']), []).append(i)
    for h, indices in hashes.items():
        if len(indices) > 1:
            diagnostics.append(dict(type='hash_collision', binding_hash=int(h), indices=indices,
                                    resolution='retained distinct names; hash lookup is ambiguous'))
    return dict(rig={'bones': output}, source_to_assembled=mappings,
                name_to_index=names, hash_to_indices=hashes, diagnostics=diagnostics,
                evidence='designed caller-policy assembly; original merge semantics unresolved')
