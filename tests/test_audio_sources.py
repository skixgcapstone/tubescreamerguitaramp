import shutil
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path
from subprocess import TimeoutExpired
from unittest.mock import patch

import numpy as np

from audio_sources import FileInputSource, _pcm_to_float


class FileInputSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "sample.wav"
        samples = (np.sin(np.linspace(0, 8, 2_048)) * 20_000).astype("<i2")
        with wave.open(str(self.path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(48_000)
            output.writeframes(samples.tobytes())

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_wav_streams_through_bounded_queue(self) -> None:
        source = FileInputSource(self.path, queue_blocks=2)
        source.start()

        block = source.read(512)
        source.stop()

        self.assertEqual(block.shape, (512,))
        self.assertGreater(float(np.max(np.abs(block))), 0)
        self.assertEqual(source.queue.maxsize, 2)

    def test_pause_returns_silence(self) -> None:
        source = FileInputSource(self.path)
        source.start()
        source.pause()

        np.testing.assert_array_equal(source.read(512), np.zeros(512, dtype=np.float32))
        source.resume()
        self.assertEqual(source.snapshot().state, "playing")
        source.stop()

    def test_eof_stops_source(self) -> None:
        source = FileInputSource(self.path)
        source.start()
        time.sleep(0.02)

        for _ in range(10):
            source.read(512)
            if source.snapshot().state == "stopped":
                break

        self.assertEqual(source.snapshot().state, "stopped")
        source.stop()

    def test_corrupt_wav_is_rejected(self) -> None:
        corrupt = Path(self.directory.name) / "corrupt.wav"
        corrupt.write_bytes(b"not a wave file")

        with self.assertRaises((EOFError, wave.Error)):
            FileInputSource(corrupt)

    def test_wav_sample_rate_is_converted_to_96_khz(self) -> None:
        wrong = Path(self.directory.name) / "wrong.wav"
        with wave.open(str(wrong), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(44_100)
            output.writeframes(b"\0" * 100)

        source = FileInputSource(wrong)
        source.start()
        time.sleep(0.02)
        block = source.read(109)
        source.stop()

        self.assertEqual(block.shape, (109,))

    def test_missing_ffmpeg_is_reported(self) -> None:
        compressed = Path(self.directory.name) / "sample.mp3"
        shutil.copyfile(self.path, compressed)

        with (
            patch("audio_sources.shutil.which", return_value=None),
            self.assertRaisesRegex(RuntimeError, "FFmpeg"),
        ):
            FileInputSource(compressed)

    def test_ffprobe_timeout_does_not_prevent_loading(self) -> None:
        compressed = Path(self.directory.name) / "sample.mp3"
        shutil.copyfile(self.path, compressed)

        with (
            patch("audio_sources.shutil.which", side_effect=lambda name: f"/usr/bin/{name}"),
            patch("audio_sources.subprocess.run", side_effect=TimeoutExpired("ffprobe", 5)),
        ):
            source = FileInputSource(compressed)

        self.assertEqual(source.duration_seconds, 0.0)

    def test_ffmpeg_timeout_is_killed_during_shutdown(self) -> None:
        compressed = Path(self.directory.name) / "sample.mp3"
        shutil.copyfile(self.path, compressed)

        class FakePipe:
            def read(self, _size):
                return b""

        class FakeProcess:
            stdout = FakePipe()

            def __init__(self):
                self.waits = 0
                self.killed = False

            def wait(self, timeout):
                self.waits += 1
                if self.waits == 1:
                    raise TimeoutExpired("ffmpeg", timeout)
                return 0

            def kill(self):
                self.killed = True

            def terminate(self):
                pass

        process = FakeProcess()
        source = FileInputSource.__new__(FileInputSource)
        source.path = compressed
        source.sample_rate = 96_000
        source.block_size = 512
        source.stop_event = threading.Event()
        source.process = None
        source._enqueue = lambda _item: None

        with (
            patch("audio_sources.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("audio_sources.subprocess.Popen", return_value=process),
        ):
            source._decode_ffmpeg()

        self.assertTrue(process.killed)

    def test_24_bit_pcm_conversion_preserves_sign(self) -> None:
        values = bytes((0, 0, 0, 255, 255, 127, 0, 0, 128))
        converted = _pcm_to_float(values, 3)

        self.assertAlmostEqual(float(converted[0]), 0)
        self.assertGreater(float(converted[1]), 0.99)
        self.assertEqual(float(converted[2]), -1)


if __name__ == "__main__":
    unittest.main()
