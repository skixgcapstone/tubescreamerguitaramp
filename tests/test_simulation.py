import math
import unittest

from simulation import ControlState, simulate_signal


class SignalSimulationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clean = ControlState(0, 0, 0, 0, 60, 0, (0, 0, 0, 0, 0))

    def test_frame_has_requested_sample_count(self) -> None:
        frame = simulate_signal(self.clean, phase=0.0, sample_count=128)

        self.assertEqual(len(frame.raw), 128)
        self.assertEqual(len(frame.processed), 128)

    def test_simulation_is_deterministic(self) -> None:
        first = simulate_signal(self.clean, phase=1.25)
        second = simulate_signal(self.clean, phase=1.25)

        self.assertEqual(first, second)

    def test_effects_change_processed_signal(self) -> None:
        effected = ControlState(55, 70, 40, 60, 60, 12, (3, -2, 4, 1, 5))

        clean_frame = simulate_signal(self.clean, phase=0.5)
        effected_frame = simulate_signal(effected, phase=0.5)

        self.assertNotEqual(clean_frame.processed, effected_frame.processed)

    def test_output_and_metrics_remain_finite(self) -> None:
        controls = ControlState(100, 100, 100, 100, 100, 50, (12, 12, 12, 12, 12))
        frame = simulate_signal(controls, phase=2.0)

        self.assertTrue(all(math.isfinite(sample) for sample in frame.processed))
        self.assertLessEqual(max(abs(sample) for sample in frame.processed), 1.35)
        self.assertGreaterEqual(frame.metrics.clipping_percent, 0)
        self.assertLessEqual(frame.metrics.clipping_percent, 100)
        self.assertLessEqual(frame.metrics.dsp_load_percent, 96)

    def test_invalid_sample_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            simulate_signal(self.clean, phase=0.0, sample_count=1)


if __name__ == "__main__":
    unittest.main()
