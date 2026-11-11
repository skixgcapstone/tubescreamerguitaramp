from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from simulation import ControlState

AudioBlock = NDArray[np.float32]


class Biquad:
    def __init__(self, sample_rate: int, frequency: float) -> None:
        self.sample_rate = sample_rate
        self.frequency = frequency
        self.b0 = 1.0
        self.b1 = self.b2 = self.a1 = self.a2 = 0.0
        self.z1 = self.z2 = 0.0
        self.active = False

    def configure(self, gain_db: float, quality: float = 0.9) -> None:
        was_active = self.active
        self.active = abs(gain_db) > 1e-9
        if self.active and not was_active:
            self.reset()
        amplitude = 10 ** (gain_db / 40)
        omega = 2 * math.pi * self.frequency / self.sample_rate
        alpha = math.sin(omega) / (2 * quality)
        a0 = 1 + alpha / amplitude
        self.b0 = (1 + alpha * amplitude) / a0
        self.b1 = (-2 * math.cos(omega)) / a0
        self.b2 = (1 - alpha * amplitude) / a0
        self.a1 = self.b1
        self.a2 = (1 - alpha / amplitude) / a0

    def reset(self) -> None:
        self.z1 = self.z2 = 0.0

    def process(self, block: AudioBlock) -> None:
        if not self.active:
            return
        b0, b1, b2, a1, a2 = self.b0, self.b1, self.b2, self.a1, self.a2
        z1, z2 = self.z1, self.z2
        for index in range(block.size):
            sample = float(block[index])
            output = b0 * sample + z1
            z1 = b1 * sample - a1 * output + z2
            z2 = b2 * sample - a2 * output
            block[index] = output
        self.z1, self.z2 = z1, z2


class DelayLine:
    def __init__(self, delay_samples: int) -> None:
        self.buffer = np.zeros(delay_samples, dtype=np.float32)
        self.position = 0

    def reset(self) -> None:
        self.buffer.fill(0)
        self.position = 0

    def process(
        self,
        block: AudioBlock,
        wet: float,
        feedback: float,
        delay_samples: int | None = None,
    ) -> None:
        if wet <= 0:
            return
        offset = self.buffer.size if delay_samples is None else max(1, min(self.buffer.size, delay_samples))
        index = 0
        while index < block.size:
            read = (self.position - offset) % self.buffer.size
            # Stop at wrap boundaries and before feedback can depend on this chunk.
            count = min(block.size - index, offset,
                        self.buffer.size - self.position, self.buffer.size - read)
            delayed = self.buffer[read:read + count].astype(np.float64)
            samples = block[index:index + count].astype(np.float64)
            self.buffer[self.position:self.position + count] = samples + delayed * feedback
            block[index:index + count] = samples + delayed * wet
            self.position = (self.position + count) % self.buffer.size
            index += count


class Chorus:
    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate
        self.buffer = np.zeros(round(sample_rate * 0.04), dtype=np.float32)
        self.position = 0
        self.phase = 0.0

    def reset(self) -> None:
        self.buffer.fill(0)
        self.position = 0
        self.phase = 0.0

    def process(self, block: AudioBlock, wet: float, rate_hz: float) -> None:
        if wet <= 0:
            return
        for index in range(block.size):
            delay = (0.018 + 0.004 * math.sin(self.phase)) * self.sample_rate
            read = (self.position - delay) % self.buffer.size
            low = int(read)
            fraction = read - low
            high = (low + 1) % self.buffer.size
            delayed = float(self.buffer[low]) * (1 - fraction) + float(self.buffer[high]) * fraction
            sample = float(block[index])
            self.buffer[self.position] = sample
            block[index] = sample * (1 - wet * 0.35) + delayed * wet * 0.55
            self.position = (self.position + 1) % self.buffer.size
            self.phase = (self.phase + 2 * math.pi * rate_hz / self.sample_rate) % (
                2 * math.pi
            )


class Reverb:
    def __init__(self, sample_rate: int) -> None:
        self.combs = tuple(
            DelayLine(max(1, round(sample_rate * seconds)))
            for seconds in (0.0297, 0.0371, 0.0411)
        )

    def reset(self) -> None:
        for comb in self.combs:
            comb.reset()

    def process(self, block: AudioBlock, wet: float, decay: float) -> None:
        if wet <= 0:
            return
        dry = block.copy()
        total = np.zeros_like(block)
        for comb in self.combs:
            branch = dry.copy()
            comb.process(branch, 1.0, decay)
            total += branch - dry
        block[:] = dry * (1 - wet * 0.3) + total * (wet / len(self.combs))


class Phaser:
    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate
        self.states = np.zeros(4, dtype=np.float32)
        self.phase = 0.0

    def reset(self) -> None:
        self.states.fill(0)
        self.phase = 0.0

    def process(self, block: AudioBlock, wet: float, rate_hz: float) -> None:
        if wet <= 0:
            return
        dry = block.copy()
        for index in range(block.size):
            sweep = (math.sin(self.phase) + 1) * 0.5
            frequency = 180 + 1_600 * sweep
            tangent = math.tan(math.pi * frequency / self.sample_rate)
            coefficient = (1 - tangent) / (1 + tangent)
            sample = float(block[index])
            for stage in range(self.states.size):
                output = -coefficient * sample + float(self.states[stage])
                self.states[stage] = sample + coefficient * output
                sample = output
            block[index] = float(dry[index]) * (1 - wet * 0.45) + sample * wet * 0.55
            self.phase = (self.phase + 2 * math.pi * rate_hz / self.sample_rate) % (2 * math.pi)


class Flanger:
    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate
        self.buffer = np.zeros(round(sample_rate * 0.012), dtype=np.float32)
        self.position = 0
        self.phase = 0.0

    def reset(self) -> None:
        self.buffer.fill(0)
        self.position = 0
        self.phase = 0.0

    def process(self, block: AudioBlock, wet: float, depth: float) -> None:
        if wet <= 0:
            return
        for index in range(block.size):
            delay_seconds = 0.001 + 0.006 * depth * (math.sin(self.phase) + 1) * 0.5
            read = (self.position - delay_seconds * self.sample_rate) % self.buffer.size
            low = int(read)
            fraction = read - low
            delayed = float(self.buffer[low]) * (1 - fraction) + float(self.buffer[(low + 1) % self.buffer.size]) * fraction
            sample = float(block[index])
            self.buffer[self.position] = sample + delayed * 0.35
            block[index] = sample * (1 - wet * 0.35) + delayed * wet * 0.65
            self.position = (self.position + 1) % self.buffer.size
            self.phase = (self.phase + 2 * math.pi * 0.25 / self.sample_rate) % (2 * math.pi)


def apply_distortion(block: AudioBlock, wet: float, drive: float) -> None:
    if wet <= 0:
        return
    dry = block.copy()
    gain = 1.0 + drive * 9.0
    shaped = np.tanh(block * gain) / math.tanh(gain)
    block[:] = dry * (1 - wet) + shaped * wet


class RealtimeDSP:
    EQ_FREQUENCIES = (100.0, 400.0, 1_000.0, 4_000.0, 10_000.0)

    def __init__(self, sample_rate: int = 96_000, block_size: int = 512) -> None:
        if sample_rate <= 20_000 or block_size <= 0:
            raise ValueError("invalid audio configuration")
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.eq = tuple(
            Biquad(sample_rate, frequency) for frequency in self.EQ_FREQUENCIES
        )
        self.chorus = Chorus(sample_rate)
        self.delay = DelayLine(round(sample_rate * 0.700))
        self.echo = DelayLine(round(sample_rate * 0.420))
        self.reverb = Reverb(sample_rate)
        self.phaser = Phaser(sample_rate)
        self.flanger = Flanger(sample_rate)
        self.controls: ControlState | None = None
        self.limited_samples = 0

    def reset(self) -> None:
        for stage in (*self.eq, self.chorus, self.delay, self.echo, self.reverb, self.phaser, self.flanger):
            stage.reset()
        self.limited_samples = 0

    def update_controls(self, controls: ControlState) -> None:
        if controls == self.controls:
            return
        for stage, gain_db in zip(self.eq, controls.eq, strict=True):
            stage.configure(max(-12, min(12, gain_db)))
        self.controls = controls

    def process(self, input_block: AudioBlock, controls: ControlState) -> AudioBlock:
        if input_block.ndim != 1:
            raise ValueError("DSP input must be mono")
        self.update_controls(controls)
        output = np.asarray(input_block, dtype=np.float32).copy()
        for stage in self.eq:
            stage.process(output)
        apply_distortion(
            output,
            max(0, min(100, controls.distortion)) / 100,
            max(0, min(100, controls.distortion_drive)) / 100,
        )
        self.chorus.process(
            output,
            max(0, min(100, controls.chorus)) / 100,
            max(1, min(30, controls.chorus_rate)) / 10,
        )
        self.phaser.process(
            output,
            max(0, min(100, controls.phaser)) / 100,
            max(1, min(30, controls.phaser_rate)) / 10,
        )
        self.flanger.process(
            output,
            max(0, min(100, controls.flanger)) / 100,
            max(0, min(100, controls.flanger_depth)) / 100,
        )
        self.delay.process(
            output,
            max(0, min(100, controls.delay)) / 100,
            0.34,
            round(self.sample_rate * max(80, min(700, controls.delay_time_ms)) / 1_000),
        )
        self.echo.process(
            output,
            max(0, min(100, controls.echo)) / 100,
            max(0, min(80, controls.echo_feedback)) / 100,
        )
        self.reverb.process(
            output,
            max(0, min(100, controls.reverb)) / 100,
            max(10, min(95, controls.reverb_decay)) / 100,
        )
        output *= max(0, min(100, controls.volume)) / 100
        self.limited_samples += int(np.count_nonzero(np.abs(output) > 0.95))
        np.clip(output, -0.95, 0.95, out=output)
        return output
