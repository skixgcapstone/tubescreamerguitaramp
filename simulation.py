from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ControlState:
    delay: int
    reverb: int
    chorus: int
    echo: int
    volume: int
    bias: int
    eq: tuple[int, int, int, int, int]
    distortion: int = 0
    phaser: int = 0
    flanger: int = 0
    delay_time_ms: int = 280
    reverb_decay: int = 68
    chorus_rate: int = 8
    echo_feedback: int = 48
    distortion_drive: int = 60
    phaser_rate: int = 8
    flanger_depth: int = 60


@dataclass(frozen=True)
class SignalMetrics:
    input_peak_volts: float
    output_peak_volts: float
    output_rms_volts: float
    signal_dbfs: float
    clipping_percent: float
    bias_offset_volts: float
    dsp_load_percent: int
    latency_ms: int


@dataclass(frozen=True)
class SimulationFrame:
    raw: tuple[float, ...]
    processed: tuple[float, ...]
    metrics: SignalMetrics


def simulate_signal(
    controls: ControlState,
    phase: float,
    sample_count: int = 240,
) -> SimulationFrame:
    if sample_count < 2:
        raise ValueError("sample_count must be at least 2")

    raw = tuple(
        0.72 * math.sin((index / (sample_count - 1)) * math.tau * 2.6 + phase)
        + 0.08 * math.sin((index / (sample_count - 1)) * math.tau * 7.1 + phase * 0.6)
        for index in range(sample_count)
    )
    shaped = _apply_eq(raw, controls.eq)
    shaped = _apply_chorus(shaped, controls.chorus)
    shaped = _apply_taps(shaped, ((15, controls.delay / 180.0),))
    shaped = _apply_taps(
        shaped,
        ((31, controls.echo / 210.0), (62, controls.echo / 420.0)),
    )
    reverb_taps = tuple(
        (offset, controls.reverb / divisor)
        for offset, divisor in ((8, 420), (19, 500), (37, 620))
    )
    shaped = _apply_taps(shaped, reverb_taps)
    distortion_mix = controls.distortion / 100.0
    drive = 1.0 + controls.distortion_drive / 12.0
    shaped = tuple(
        sample * (1 - distortion_mix)
        + math.tanh(sample * drive) / math.tanh(drive) * distortion_mix
        for sample in shaped
    )
    shaped = _apply_taps(shaped, ((5, controls.phaser / 240.0),))
    shaped = _apply_taps(shaped, ((2, -controls.flanger / 180.0),))

    gain = 0.25 + controls.volume / 75.0
    bias = controls.bias / 100.0
    processed = tuple(
        max(-1.35, min(1.35, math.tanh((sample * gain + bias) * 1.7) - bias * 0.32))
        for sample in shaped
    )
    peak = max(abs(sample) for sample in processed)
    rms = math.sqrt(sum(sample * sample for sample in processed) / sample_count)
    clipping = sum(abs(sample) >= 1.24 for sample in processed) / sample_count * 100
    active_effects = sum(
        value > 0
        for value in (
            controls.delay,
            controls.reverb,
            controls.chorus,
            controls.echo,
            controls.distortion,
            controls.phaser,
            controls.flanger,
        )
    )
    eq_load = sum(abs(value) for value in controls.eq) / 12.0
    metrics = SignalMetrics(
        input_peak_volts=max(abs(sample) for sample in raw) * 1.55,
        output_peak_volts=peak * 1.48,
        output_rms_volts=rms * 1.48,
        signal_dbfs=20 * math.log10(max(peak / 1.35, 0.001)),
        clipping_percent=clipping,
        bias_offset_volts=bias * 0.42,
        dsp_load_percent=min(96, round(13 + active_effects * 7 + eq_load * 3)),
        latency_ms=round(
            5 + controls.delay * 0.16 + controls.reverb * 0.05 + controls.echo * 0.09
        ),
    )
    return SimulationFrame(raw=raw, processed=processed, metrics=metrics)


def _apply_eq(
    signal: tuple[float, ...],
    eq: tuple[int, int, int, int, int],
) -> tuple[float, ...]:
    low, low_mid, mid, high_mid, high = (value / 12.0 for value in eq)
    result: list[float] = []
    previous = signal[0]
    for index, sample in enumerate(signal):
        smooth = previous * 0.72 + sample * 0.28
        detail = sample - smooth
        harmonic = math.sin(index * 0.31) * sample
        result.append(
            sample * (1 + mid * 0.18)
            + smooth * (low * 0.28 + low_mid * 0.14)
            + detail * (high * 0.24 + high_mid * 0.15)
            + harmonic * high_mid * 0.05
        )
        previous = smooth
    return tuple(result)


def _apply_chorus(signal: tuple[float, ...], amount: int) -> tuple[float, ...]:
    mix = amount / 170.0
    if mix == 0:
        return signal
    size = len(signal)
    return tuple(
        sample + signal[(index - 4 - round(3 * math.sin(index * 0.08))) % size] * mix
        for index, sample in enumerate(signal)
    )


def _apply_taps(
    signal: tuple[float, ...],
    taps: tuple[tuple[int, float], ...],
) -> tuple[float, ...]:
    if not any(gain for _offset, gain in taps):
        return signal
    size = len(signal)
    return tuple(
        sample + sum(signal[(index - offset) % size] * gain for offset, gain in taps)
        for index, sample in enumerate(signal)
    )
