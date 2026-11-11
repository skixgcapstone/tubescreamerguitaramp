import unittest
import numpy as np
from dsp import DelayLine


class DelayEquivalenceTests(unittest.TestCase):
    def test_vector_chunks_match_sample_feedback_across_wraps_and_delay_changes(self):
        rng = np.random.default_rng(1111)
        for capacity in (1, 7, 97, 2851, 67200):
            actual = DelayLine(capacity)
            reference = np.zeros(capacity, dtype=np.float32)
            position = 0
            for number in range(30):
                offset = max(1, capacity // 2) if number % 2 else capacity
                block = rng.uniform(-.5, .5, 512).astype(np.float32)
                expected = block.copy()
                for index in range(block.size):
                    delayed = float(reference[(position-offset) % capacity])
                    sample = float(expected[index])
                    reference[position] = sample + delayed * .73
                    expected[index] = sample + delayed * .81
                    position = (position + 1) % capacity
                actual.process(block, .81, .73, offset)
                np.testing.assert_array_equal(block, expected)
                np.testing.assert_array_equal(actual.buffer, reference)
                self.assertEqual(actual.position, position)
