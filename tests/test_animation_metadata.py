import json
from pathlib import Path
import unittest
from reference.animation_metadata import assign_hierarchy_ranks


class MetadataTests(unittest.TestCase):
    def test_original_rank_producer(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/hierarchy_rank_validation.json').read_text())
        for sample in receipt['samples']:
            args=dict(sample['inputs']);args['overrides']={int(k):v for k,v in args['overrides'].items()}
            result=assign_hierarchy_ranks(**args)
            self.assertEqual(result,sample['result'])
            for before,after in zip(args['flags'],result['flags']):
                self.assertEqual(before&0x8f,after&0x8f)

    def test_original_authority_selection(self):
        from reference.animation_metadata import choose_authority_preset,mark_authority_channels
        import zlib
        root=Path(__file__).resolve().parents[1]/'native/snow_host'
        presets=json.loads((root/'authority_channel_identifiers.json').read_text())['presets']
        for rows in presets.values():
            for row in rows:
                if row['name'] is not None:self.assertEqual(zlib.crc32(row['name'].encode())&0xffffffff,row['key'])
        receipt=json.loads((root/'authority_channels_validation.json').read_text())
        for sample in receipt['samples']:
            preset=choose_authority_preset(*[sample[k] for k in ('owner_visible','owner_value','toe_present','alternate_value')])
            self.assertEqual(preset,sample['preset'])
            keys=[r['key'] for r in presets[preset]] if preset else []
            result=mark_authority_channels(sample['flags'],keys,lambda key:sample['lookup'].get(str(key),65535))
            self.assertEqual(result,sample['result'])

    def test_connected_lookup_and_selection(self):
        from reference.animation_metadata import resolve_authority_channels
        root=Path(__file__).resolve().parents[1]/'native/snow_host'
        presets=json.loads((root/'authority_channel_identifiers.json').read_text())['presets']
        keys={k:[r['key'] for r in rows] for k,rows in presets.items()}
        receipt=json.loads((root/'authority_lookup_validation.json').read_text())
        for sample in receipt['samples']:
            result=resolve_authority_channels(sample['flags'],sample['runtime_entries'],
                sample['owner_entries'],sample['owner_visible'],sample['owner_value'],keys)
            self.assertEqual(result,sample['result'])

    def test_original_source_projection(self):
        from reference.animation_metadata import build_source_metadata
        root=Path(__file__).resolve().parents[1]/'native/snow_host'
        receipt=json.loads((root/'source_metadata_validation.json').read_text())
        for sample in receipt['samples']:
            self.assertEqual(build_source_metadata(**sample['inputs']),sample['result'])

    def test_original_in_capacity_initialization(self):
        from reference.animation_metadata import resize_metadata_in_capacity
        root=Path(__file__).resolve().parents[1]/'native/snow_host'
        receipt=json.loads((root/'metadata_initialization_validation.json').read_text())
        for sample in receipt['samples']:
            result=resize_metadata_in_capacity(sample['before'],sample['old_count'],sample['new_count'])
            self.assertEqual(result['count'],sample['new_count'])
            self.assertEqual([list(r) for r in result['records']],sample['after'])
