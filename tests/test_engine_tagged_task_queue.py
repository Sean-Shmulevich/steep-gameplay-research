import unittest

from engine.tagged_task_queue import pop_decision


class TaggedTaskQueueTests(unittest.TestCase):
    def decide(self, **changes):
        observed = dict(queue_identity=0x100, head=0x200, tail=0x300,
                        head_next=0x300, rechecked_head=0x200,
                        next_payload='synthetic-task')
        observed.update(changes)
        return pop_decision(**observed)

    def test_changed_head_retries_before_empty_interpretation(self):
        self.assertEqual(self.decide(rechecked_head=0x400, head_next=0x100),
                         dict(action='retry'))
        self.assertEqual(self.decide(head_next=0x100), dict(action='empty'))

    def test_lagging_tail_uses_later_link_observation(self):
        helped = self.decide(tail=0x200, tail_next=0x400)
        self.assertEqual(helped, dict(action='help_tail', expected=0x200,
                                     desired=(1 << 48) | 0x400, after_cas='retry'))
        self.assertEqual(self.decide(tail=0x200, tail_next=0x100),
                         dict(action='retry'))

    def test_success_retires_old_dummy_and_copies_next_payload(self):
        result = self.decide()
        self.assertEqual(result['desired'], (1 << 48) | 0x300)
        self.assertEqual(result['on_success'],
                         dict(return_node=0x200, write_payload='synthetic-task'))
        self.assertEqual(result['on_failure'], 'retry')
        self.assertIsNone(self.decide(next_payload=None)['on_success']['write_payload'])

    def test_tag_wrap_preserves_pointer(self):
        head = (0xffff << 48) | 0x200
        result = self.decide(head=head, rechecked_head=head)
        self.assertEqual(result['desired'], 0x300)
        self.assertEqual(result['on_success']['return_node'], 0x200)

    def test_rejects_missing_observation_and_invalid_words(self):
        for changes in (dict(tail=0x200), dict(head=True),
                        dict(queue_identity=1 << 48), dict(head_next=-1)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.decide(**changes)
