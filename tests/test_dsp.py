import math
import unittest

import numpy as np

from dsp import RealtimeDSP
from simulation import ControlState


class RealtimeDSPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dsp = RealtimeDSP()
        self.clean = ControlState(0, 0, 0, 0, 100, 0, (0, 0, 0, 0, 0))

    def test_silence_remains_silent(self) -> None:
        output = self.dsp.process(np.zeros(512, dtype=np.float32), self.clean)

        np.testing.assert_array_equal(output, np.zeros(512, dtype=np.float32))

    def test_zero_volume_mutes_output(self) -> None:
        muted = ControlState(100, 100, 100, 100, 0, 50, (12, 12, 12, 12, 12))
        output = self.dsp.process(np.ones(512, dtype=np.float32), muted)

        np.testing.assert_array_equal(output, np.zeros(512, dtype=np.float32))

    def test_limiter_bounds_worst_case_output(self) -> None:
        worst = ControlState(100, 100, 100, 100, 100, 50, (12, 12, 12, 12, 12))
        signal = np.full(512, 10, dtype=np.float32)

        output = self.dsp.process(signal, worst)

        self.assertLessEqual(float(np.max(np.abs(output))), 0.95)
        self.assertGreater(self.dsp.limited_samples, 0)

    def test_neutral_controls_pass_signal_unchanged(self) -> None:
        signal = np.linspace(-0.5, 0.5, 512, dtype=np.float32)
        output = self.dsp.process(signal, self.clean)

        np.testing.assert_allclose(output, signal, atol=1e-6)

    def test_effect_state_continues_across_blocks(self) -> None:
        controls = ControlState(100, 0, 0, 0, 100, 0, (0, 0, 0, 0, 0))
        impulse = np.zeros(512, dtype=np.float32)
        impulse[0] = 1
        self.dsp.process(impulse, controls)

        delay_blocks = math.ceil(
            self.dsp.sample_rate * 0.280 / self.dsp.block_size
        ) + 1
        blocks = [
            self.dsp.process(np.zeros(512, dtype=np.float32), controls)
            for _ in range(delay_blocks)
        ]

        self.assertTrue(any(np.any(block) for block in blocks))

    def test_each_effect_changes_a_sustained_signal(self) -> None:
        sample_count = self.dsp.sample_rate
        time = np.arange(sample_count, dtype=np.float32) / self.dsp.sample_rate
        signal = (0.2 * np.sin(2 * math.pi * 440 * time)).astype(np.float32)
        settings = (
            ControlState(100, 0, 0, 0, 100, 0, (0, 0, 0, 0, 0)),
            ControlState(0, 100, 0, 0, 100, 0, (0, 0, 0, 0, 0)),
            ControlState(0, 0, 100, 0, 100, 0, (0, 0, 0, 0, 0)),
            ControlState(0, 0, 0, 100, 100, 0, (0, 0, 0, 0, 0)),
            ControlState(0, 0, 0, 0, 100, 0, (0, 0, 0, 0, 0), distortion=100),
            ControlState(0, 0, 0, 0, 100, 0, (0, 0, 0, 0, 0), phaser=100),
            ControlState(0, 0, 0, 0, 100, 0, (0, 0, 0, 0, 0), flanger=100),
        )

        for controls in settings:
            with self.subTest(controls=controls):
                dsp = RealtimeDSP()
                blocks = np.array_split(signal, sample_count // dsp.block_size)
                output = np.concatenate([dsp.process(block, controls) for block in blocks])
                difference_rms = float(np.sqrt(np.mean((output - signal) ** 2)))
                self.assertGreater(difference_rms, 0.01)


if __name__ == "__main__":
    unittest.main()
