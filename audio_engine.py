from __future__ import annotations

import math
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np
from numpy.typing import NDArray

from audio_sources import DeviceInputSource, FileInputSource, InputSource
from dsp import RealtimeDSP
from simulation import ControlState

AudioBlock = NDArray[np.float32]


class AudioStream(Protocol):
    def start(self) -> Any: ...

    def stop(self) -> Any: ...

    def close(self) -> Any: ...


class AudioBackend(Protocol):
    def OutputStream(self, **kwargs: Any) -> AudioStream: ...

    def Stream(self, **kwargs: Any) -> AudioStream: ...


def _preferred_codec_zero_device(
    backend: AudioBackend | Any, *, require_input: bool
) -> int | None:
    """Return a full-duplex Codec Zero device index when one is available."""
    query_devices = getattr(backend, "query_devices", None)
    if not callable(query_devices):
        return None
    try:
        devices = query_devices()
    except Exception:  # noqa: BLE001 - device enumeration must not block startup
        return None
    for index, device in enumerate(devices):
        name = str(device.get("name", "")).lower()
        codec_zero_names = ("codec zero", "iqaudio codec", "da7212")
        if not any(identifier in name for identifier in codec_zero_names):
            continue
        if int(device.get("max_output_channels", 0)) < 2:
            continue
        if require_input and int(device.get("max_input_channels", 0)) < 1:
            continue
        return index
    return None


@dataclass(frozen=True)
class AudioSnapshot:
    source_name: str = "Visual simulation"
    state: str = "simulation"
    position_seconds: float = 0.0
    duration_seconds: float = 0.0
    error: str = ""
    input_waveform: tuple[float, ...] = ()
    output_waveform: tuple[float, ...] = ()
    input_peak: float = 0.0
    output_peak: float = 0.0
    output_rms: float = 0.0
    output_dbfs: float = -60.0
    limited_samples: int = 0
    underruns: int = 0
    overruns: int = 0
    deadline_misses: int = 0
    callback_ms: float = 0.0
    latency_ms: float = 0.0


class LoopRecorder:
    def __init__(self, sample_rate: int, maximum_seconds: int = 30) -> None:
        self.sample_rate = sample_rate
        self.maximum_samples = sample_rate * maximum_seconds
        self.captured: list[AudioBlock] = []
        self.loop = np.empty(0, dtype=np.float32)
        self.position = 0
        self.sample_count = 0
        self.recording = False
        self.playing = False

    @property
    def state(self) -> str:
        if self.recording:
            return "recording"
        if self.playing:
            return "looping"
        return "off"

    def start(self) -> None:
        self.captured.clear()
        self.loop = np.empty(0, dtype=np.float32)
        self.position = 0
        self.sample_count = 0
        self.recording = True
        self.playing = False

    def close(self) -> None:
        if not self.recording or not self.captured:
            return
        self.recording = False
        self.loop = np.concatenate(self.captured)[: self.maximum_samples]
        self.captured.clear()
        self.position = 0
        self.playing = self.loop.size > 0

    def stop(self) -> None:
        self.captured.clear()
        self.loop = np.empty(0, dtype=np.float32)
        self.position = 0
        self.sample_count = 0
        self.recording = False
        self.playing = False

    def process(self, block: AudioBlock) -> AudioBlock:
        if self.recording and self.sample_count < self.maximum_samples:
            remaining = self.maximum_samples - self.sample_count
            captured = np.asarray(block[:remaining], dtype=np.float32).copy()
            self.captured.append(captured)
            self.sample_count += captured.size
        if not self.playing or not self.loop.size:
            return block
        end = self.position + block.size
        if end <= self.loop.size:
            output = self.loop[self.position:end].copy()
        elif block.size <= self.loop.size:
            split = self.loop.size - self.position
            output = np.concatenate((self.loop[self.position:], self.loop[: block.size - split]))
        else:
            indices = (np.arange(block.size) + self.position) % self.loop.size
            output = self.loop[indices].copy()
        self.position = end % self.loop.size
        return output


class AudioEngine:
    def __init__(
        self,
        sample_rate: int = 96_000,
        block_size: int = 512,
        backend: AudioBackend | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.backend = backend
        self.dsp = RealtimeDSP(sample_rate, block_size)
        self.looper = LoopRecorder(sample_rate)
        self.controls = ControlState(0, 0, 0, 0, 60, 0, (0, 0, 0, 0, 0))
        self.source: InputSource | None = None
        self.stream: AudioStream | None = None
        self.live_mode = False
        self.snapshot_value = AudioSnapshot()
        self.underruns = 0
        self.overruns = 0
        self.deadline_misses = 0
        self.faulted = False
        self.telemetry_interval_blocks = max(1, round(sample_rate / block_size / 30))
        self.telemetry_block = 0

    def load_file(self, path: str | Path, loop: bool = False) -> AudioSnapshot:
        self.stop()
        self.source = FileInputSource(path, self.sample_rate, self.block_size, loop)
        source = self.source.snapshot()
        self.snapshot_value = AudioSnapshot(
            source_name=source.name,
            state="loaded",
            duration_seconds=source.duration_seconds,
        )
        return self.snapshot_value

    def play(self) -> None:
        if self.source is None or isinstance(self.source, DeviceInputSource):
            raise RuntimeError("load an audio file before pressing Play")
        if self.source.snapshot().state == "paused":
            self.source.resume()
            return
        self._close_stream()
        self.dsp.reset()
        self._reset_counters()
        self.faulted = False
        self.source.start()
        self.live_mode = False
        backend = self._backend()
        stream_options: dict[str, Any] = {}
        output_device = _preferred_codec_zero_device(backend, require_input=False)
        if output_device is not None:
            stream_options["device"] = output_device
        self._start_stream(
            lambda: backend.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=2,
                dtype="float32",
                callback=self._output_callback,
                **stream_options,
            )
        )

    def pause(self) -> None:
        if self.source is not None:
            self.source.pause()

    def stop(self) -> None:
        self._close_stream()
        if self.source is not None:
            self.source.stop()
        self.live_mode = False
        self.looper.stop()
        self.faulted = False
        self.snapshot_value = AudioSnapshot(state="stopped")

    def start_live_input(self) -> None:
        self.stop()
        self.source = DeviceInputSource(self.sample_rate)
        self.source.start()
        self.dsp.reset()
        self._reset_counters()
        self.faulted = False
        self.live_mode = True
        backend = self._backend()
        stream_options: dict[str, Any] = {}
        duplex_device = _preferred_codec_zero_device(backend, require_input=True)
        if duplex_device is not None:
            stream_options["device"] = (duplex_device, duplex_device)
        self._start_stream(
            lambda: backend.Stream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=(1, 2),
                dtype="float32",
                callback=self._duplex_callback,
                **stream_options,
            )
        )

    def stop_live_input(self) -> None:
        if self.live_mode:
            self.stop()

    def update_controls(self, controls: ControlState) -> None:
        self.controls = controls

    def toggle_loop(self) -> None:
        if self.looper.state == "off":
            self.looper.start()
        else:
            self.looper.stop()

    def close_loop(self) -> None:
        self.looper.close()

    def get_status(self) -> AudioSnapshot:
        return self.snapshot_value

    def service(self) -> None:
        if self.stream is None:
            return
        source_state = (
            self.source.snapshot().state if self.source is not None else "stopped"
        )
        if self.faulted or source_state in ("error", "stopped"):
            self._close_stream()
            if self.source is not None:
                self.source.stop()
            self.live_mode = False

    def shutdown(self) -> None:
        self.stop()

    def _backend(self) -> AudioBackend:
        if self.backend is None:
            try:
                import sounddevice
            except ImportError as error:
                raise RuntimeError(
                    "audio support requires: python -m pip install -r requirements.txt"
                ) from error
            self.backend = sounddevice
        return self.backend

    def _start_stream(self, create_stream: Callable[[], AudioStream]) -> None:
        try:
            self.stream = create_stream()
            self.stream.start()
        except Exception as error:  # noqa: BLE001
            self._close_stream()
            if self.source is not None:
                self.source.stop()
            self.live_mode = False
            source_name = self.source.snapshot().name if self.source is not None else "Audio input"
            message = f"Audio device unavailable: {error}"
            self.snapshot_value = AudioSnapshot(source_name=source_name, state="error", error=message)
            raise RuntimeError(message) from error

    def _output_callback(
        self,
        outdata: AudioBlock,
        frames: int,
        _time_info: Any,
        status: Any,
    ) -> None:
        self._process(outdata, frames, status)

    def _duplex_callback(
        self,
        indata: AudioBlock,
        outdata: AudioBlock,
        frames: int,
        _time_info: Any,
        status: Any,
    ) -> None:
        self._process(outdata, frames, status, indata)

    def _process(
        self,
        outdata: AudioBlock,
        frames: int,
        status: Any,
        live_block: AudioBlock | None = None,
    ) -> None:
        started = time.perf_counter()
        try:
            if self.faulted:
                outdata.fill(0)
                return
            self._record_stream_status(status)
            if self.source is None:
                outdata.fill(0)
                return
            input_block = self.source.read(frames, live_block)
            looped_block = self.looper.process(input_block)
            output_block = self.dsp.process(looped_block, self.controls)
            outdata[:, 0] = output_block
            outdata[:, 1] = output_block
            source = self.source.snapshot()
            publish_telemetry = self.telemetry_block == 0 or source.state != "playing"
            self.telemetry_block = (self.telemetry_block + 1) % self.telemetry_interval_blocks
            if not publish_telemetry:
                elapsed_ms = (time.perf_counter() - started) * 1_000
                if elapsed_ms > frames / self.sample_rate * 1_000:
                    self.deadline_misses += 1
                return
            input_peak = float(np.max(np.abs(input_block), initial=0))
            output_peak = float(np.max(np.abs(output_block), initial=0))
            rms = float(np.sqrt(np.mean(output_block * output_block)))
            step = max(1, frames // 240)
            elapsed_ms = (time.perf_counter() - started) * 1_000
            if elapsed_ms > frames / self.sample_rate * 1_000:
                self.deadline_misses += 1
            self.snapshot_value = AudioSnapshot(
                source_name=source.name,
                state=source.state,
                position_seconds=source.position_seconds,
                duration_seconds=source.duration_seconds,
                error=source.error,
                input_waveform=tuple(float(value) for value in input_block[::step]),
                output_waveform=tuple(float(value) for value in output_block[::step]),
                input_peak=input_peak,
                output_peak=output_peak,
                output_rms=rms,
                output_dbfs=20 * math.log10(max(output_peak, 0.001)),
                limited_samples=self.dsp.limited_samples,
                underruns=self.underruns + source.underruns,
                overruns=self.overruns,
                deadline_misses=self.deadline_misses,
                callback_ms=elapsed_ms,
                latency_ms=frames / self.sample_rate * 1_000,
            )
        except Exception as error:  # noqa: BLE001
            outdata.fill(0)
            self.faulted = True
            previous = self.snapshot_value
            self.snapshot_value = AudioSnapshot(
                source_name=previous.source_name,
                state="error",
                error=str(error),
                underruns=self.underruns,
                overruns=self.overruns,
                deadline_misses=self.deadline_misses,
            )

    def _record_stream_status(self, status: Any) -> None:
        if not status:
            return
        if getattr(status, "input_overflow", False):
            self.overruns += 1
        if getattr(status, "output_underflow", False):
            self.underruns += 1

    def _reset_counters(self) -> None:
        self.underruns = 0
        self.overruns = 0
        self.deadline_misses = 0
        self.telemetry_block = 0

    def _close_stream(self) -> None:
        if self.stream is None:
            return
        stream = self.stream
        self.stream = None
        with suppress(Exception):
            stream.stop()
        with suppress(Exception):
            stream.close()
