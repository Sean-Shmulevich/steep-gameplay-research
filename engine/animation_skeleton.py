"""Independent composition of recovered initial skeleton metadata operations.

Contract and evidence boundaries: docs/reconstruction/ANIMATION_SKELETON.md.
This is not the complete native assembly routine or an asset decoder.
"""
from reference.animation_metadata import (
    initialize_metadata_record, build_source_metadata, assign_hierarchy_ranks,
    resolve_authority_channels,
)


def assemble_initial_skeleton(*, source_records, backing_records, selector,
                              overrides, owner_visible, owner_value,
                              runtime_entries, owner_entries, preset_keys):
    """Return metadata and work indices usable by prepare_animation.

    All tables and storage are caller supplied. No merged-rig mapping, default
    allocation bytes, owner enum meaning or hierarchy prefix is inferred.
    Inputs are not mutated. Duplicate selected indices retain their order.
    """
    if len(source_records) != len(backing_records) or len(source_records) > 16383:
        raise ValueError('matching source/backing records within packed capacity required')
    initialized = [initialize_metadata_record(record) for record in backing_records]
    projected = build_source_metadata(source_records, selector,
                                      [record[10] for record in initialized])
    rows = projected['rows']
    ranked = assign_hierarchy_ranks([row['flags'] for row in rows],
                                   projected['keys'], overrides,
                                   owner_visible, owner_value)
    authority = resolve_authority_channels(ranked['flags'], runtime_entries,
                                          owner_entries, owner_visible,
                                          owner_value, preset_keys)
    for row, flag in zip(rows, authority['flags']):
        row['flags'] = flag
    metadata = [dict(parent=row['parent'], skip_span=row['skip_span'],
                     rank=(row['flags'] >> 4) & 7,
                     current_authoritative=bool(row['flags'] & 8)) for row in rows]
    return dict(rows=rows, metadata=metadata, indices=authority['selected'],
                preset=authority['preset'], default_rank=ranked['default'],
                evidence=dict(local_operations='recovered',
                              composition='independent_adapter',
                              native_full_assembly_validated=False,
                              live_validated=False))
