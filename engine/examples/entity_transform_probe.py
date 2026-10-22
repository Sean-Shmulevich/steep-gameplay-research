"""Synthetic notification-list replacement; no game assets or native access.

Run: python3 -m engine.examples.entity_transform_probe
"""
import json
from reference.entity_transform_update import TransformEntity, update_entity_transform


def run_probe():
    entity = TransformEntity(bytes(64), ['old-a', 'old-b'])
    events = []
    def record(phase, component, entity):
        events.append(dict(phase=phase, component=component,
            transform='old' if entity.transform == bytes(64) else 'new',
            lock_depth=entity.lock_depth))
    def notify(phase, component, entity):
        record(phase, component, entity)
        if phase == 'pre' and component == 'old-a':
            entity.components = ['replacement']
    update_entity_transform(entity, bytes([1])*64, thread_id=7, notify=notify,
        publish_cache=lambda e: record('cache', None, e))
    return dict(evidence='synthetic_reconstruction_example', events=events,
                final_components=entity.components, final_lock_depth=entity.lock_depth)


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
