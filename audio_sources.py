from __future__ import annotations

import queue
import shutil
import subprocess  # nosec B404
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

import numpy as np
from numpy.typing import NDArray

AudioBlock = NDArray[np.float32]
_EOF = object()
_MAX_FILE_BYTES = 4 * 1024**3


@dataclass(frozen=True)
class SourceSnapshot:
    name: str
    state: str
    position_seconds: float
    duration_seconds: float
    error: str
    underruns: int


class InputSource(Protocol):
    def start(self) -> None: ...

    def read(self, frames: int, live_block: AudioBlock | None = None) -> AudioBlock: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def stop(self) -> None: ...

    def snapshot(self) -> SourceSnapshot: ...


class FileInputSource:
    SUPPORTED_SUFFIXES: Final = frozenset((".wav", ".mp3", ".m4a"))

    def __init__(
        self,
        path: str | Path,
        sample_rate: int = 96_000,
        block_size: int = 512,
        loop: bool = False,
        queue_blocks: int = 16,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.loop = loop
        self.queue: queue.Queue[AudioBlock | object] = queue.Queue(queue_blocks)
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.process: subprocess.Popen[bytes] | None = None
        self.pending = np.empty(0, dtype=np.float32)
        self.state = "stopped"
        self.error = ""
        self.duration_seconds = 0.0
        self.source_sample_rate = sample_rate
        self.frames_read = 0
        self.underruns = 0
        self._validate()

    def _validate(self) -> None:
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        if self.path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            raise ValueError("supported audio formats are WAV, MP3, and M4A")
        if self.path.stat().st_size > _MAX_FILE_BYTES:
            raise ValueError("audio file exceeds the 4 GiB safety limit")
        if self.path.suffix.lower() == ".wav":
            with wave.open(str(self.path), "rb") as stream:
                if stream.getcomptype() != "NONE":
                    raise ValueError("compressed WAV files are not supported")
                if stream.getsampwidth() not in (1, 2, 3, 4):
                    raise ValueError("unsupported WAV sample width")
                if stream.getnchannels() < 1 or stream.getnchannels() > 8:
                    raise ValueError("WAV channel count must be between 1 and 8")
                self.source_sample_rate = stream.getframerate()
                self.duration_seconds = stream.getnframes() / stream.getframerate()
        else:
            if shutil.which("ffmpeg") is None:
                raise RuntimeError("FFmpeg is required for MP3 and M4A playback")
            self.duration_seconds = self._probe_duration()

    def _probe_duration(self) -> float:
        ffprobe = shutil.which("ffprobe")
        if ffprobe is None:
            return 0.0
        try:
            result = subprocess.run(  # nosec B603
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(self.path),
                ],
                capture_output=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return 0.0
        try:
            return max(0.0, float(result.stdout.decode().strip()))
        except ValueError:
            return 0.0

    def start(self) -> None:
        self.stop()
        self.stop_event.clear()
        self.ready_event.clear()
        self.pending = np.empty(0, dtype=np.float32)
        self.frames_read = 0
        self.underruns = 0
        self.error = ""
        self.state = "playing"
        self.thread = threading.Thread(
            target=self._decode, name="audio-decoder", daemon=True
        )
        self.thread.start()
        self.ready_event.wait(timeout=0.5)

    def _decode(self) -> None:
        try:
            while not self.stop_event.is_set():
                if self.path.suffix.lower() == ".wav":
                    self._decode_wav()
                else:
                    self._decode_ffmpeg()
                if not self.loop:
                    break
            self._enqueue(_EOF)
        except Exception as error:  # noqa: BLE001
            self.error = str(error)
            self.state = "error"
            self._enqueue(_EOF)

    def _decode_wav(self) -> None:
        with wave.open(str(self.path), "rb") as stream:
            channels = stream.getnchannels()
            width = stream.getsampwidth()
            read_size = max(
                1,
                round(self.block_size * self.source_sample_rate / self.sample_rate),
            )
            while not self.stop_event.is_set():
                data = stream.readframes(read_size)
                if not data:
                    return
                samples = _pcm_to_float(data, width)
                mono = samples.reshape(-1, channels).mean(axis=1).astype(np.float32)
                self._enqueue(
                    _resample(mono, self.source_sample_rate, self.sample_rate)
                )

    def _decode_ffmpeg(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError("FFmpeg is required for this audio format")
        process = subprocess.Popen(  # nosec B603
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(self.path),
                "-f",
                "f32le",
                "-ac",
                "1",
                "-ar",
                str(self.sample_rate),
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.process = process
        if process.stdout is None:
            raise RuntimeError("FFmpeg output pipe could not be opened")
        byte_count = self.block_size * np.dtype(np.float32).itemsize
        while not self.stop_event.is_set():
            data = process.stdout.read(byte_count)
            if not data:
                break
            block = np.frombuffer(data, dtype="<f4").astype(np.float32)
            self._enqueue(block)
        try:
            return_code = process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            return_code = process.wait(timeout=2)
        self.process = None
        if return_code and not self.stop_event.is_set():
            raise RuntimeError("FFmpeg could not decode the selected audio file")

    def _enqueue(self, item: AudioBlock | object) -> None:
        while not self.stop_event.is_set():
            try:
                self.queue.put(item, timeout=0.1)
                self.ready_event.set()
                return
            except queue.Full:
                continue

    def read(self, frames: int, live_block: AudioBlock | None = None) -> AudioBlock:
        del live_block
        if self.state == "paused":
            return np.zeros(frames, dtype=np.float32)
        output = np.zeros(frames, dtype=np.float32)
        written = 0
        while written < frames:
            if self.pending.size:
                take = min(frames - written, self.pending.size)
                output[written : written + take] = self.pending[:take]
                self.pending = self.pending[take:]
                written += take
                continue
            try:
                item = self.queue.get_nowait()
            except queue.Empty:
                self.underruns += 1
                break
            if item is _EOF:
                if self.state != "error":
                    self.state = "stopped"
                break
            self.pending = item
        self.frames_read += written
        return output

    def pause(self) -> None:
        if self.state == "playing":
            self.state = "paused"

    def resume(self) -> None:
        if self.state == "paused":
            self.state = "playing"

    def stop(self) -> None:
        self.stop_event.set()
        self.ready_event.set()
        if self.process is not None:
            self.process.terminate()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.thread = None
        self.process = None
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        self.state = "stopped"

    def snapshot(self) -> SourceSnapshot:
        return SourceSnapshot(
            name=self.path.name,
            state=self.state,
            position_seconds=self.frames_read / self.sample_rate,
            duration_seconds=self.duration_seconds,
            error=self.error,
            underruns=self.underruns,
        )


class DeviceInputSource:
    def __init__(self, sample_rate: int = 96_000) -> None:
        self.sample_rate = sample_rate
        self.state = "stopped"
        self.frames_read = 0

    def start(self) -> None:
        self.frames_read = 0
        self.state = "playing"

    def read(self, frames: int, live_block: AudioBlock | None = None) -> AudioBlock:
        if self.state != "playing" or live_block is None:
            return np.zeros(frames, dtype=np.float32)
        block = np.asarray(live_block, dtype=np.float32)
        mono = block.mean(axis=1) if block.ndim == 2 else block
        self.frames_read += min(frames, mono.size)
        output = np.zeros(frames, dtype=np.float32)
        output[: min(frames, mono.size)] = mono[:frames]
        return output

    def pause(self) -> None:
        if self.state == "playing":
            self.state = "paused"

    def resume(self) -> None:
        if self.state == "paused":
            self.state = "playing"

    def stop(self) -> None:
        self.state = "stopped"

    def snapshot(self) -> SourceSnapshot:
        return SourceSnapshot(
            name="Default live input",
            state=self.state,
            position_seconds=self.frames_read / self.sample_rate,
            duration_seconds=0.0,
            error="",
            underruns=0,
        )


def _pcm_to_float(data: bytes, sample_width: int) -> AudioBlock:
    if sample_width == 1:
        return (np.frombuffer(data, dtype=np.uint8).astype(np.float32) - 128) / 128
    if sample_width == 2:
        return np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768
    if sample_width == 3:
        packed = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3)
        values = (
            packed[:, 0].astype(np.int32)
            | (packed[:, 1].astype(np.int32) << 8)
            | (packed[:, 2].astype(np.int32) << 16)
        )
        values = np.where(values & 0x800000, values - 0x1000000, values)
        return values.astype(np.float32) / 8_388_608
    if sample_width == 4:
        return np.frombuffer(data, dtype="<i4").astype(np.float32) / 2_147_483_648
    raise ValueError("unsupported PCM sample width")


def _resample(block: AudioBlock, source_rate: int, target_rate: int) -> AudioBlock:
    if source_rate == target_rate or block.size < 2:
        return block
    output_size = max(1, round(block.size * target_rate / source_rate))
    source_positions = np.arange(block.size, dtype=np.float64)
    target_positions = np.linspace(0, block.size - 1, output_size)
    return np.interp(target_positions, source_positions, block).astype(np.float32)
