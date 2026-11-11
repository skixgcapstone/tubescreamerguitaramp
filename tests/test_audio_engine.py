import unittest

import numpy as np

from audio_engine import AudioEngine, LoopRecorder
from audio_sources import SourceSnapshot
from simulation import ControlState


class FakeSource:
    def __init__(self, fail: bool = False) -> None:
        self.state = "stopped"
        self.fail = fail
        self.stopped = False

    def start(self) -> None:
        self.state = "playing"

    def read(self, frames: int, live_block=None):
        if self.fail:
            raise RuntimeError("source failure")
        return np.full(frames, 0.1, dtype=np.float32)

    def pause(self) -> None:
        self.state = "paused"

    def resume(self) -> None:
        self.state = "playing"

    def stop(self) -> None:
        self.state = "stopped"
        self.stopped = True

    def snapshot(self) -> SourceSnapshot:
        return SourceSnapshot("fake.wav", self.state, 1, 2, "", 0)


class FakeStream:
    def __init__(self, **kwargs) -> None:
        self.sample_rate = kwargs["samplerate"]
        self.callback = kwargs["callback"]
        self.device = kwargs.get("device")
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def close(self) -> None:
        self.closed = True

    def pump(self) -> np.ndarray:
        output = np.empty((512, 2), dtype=np.float32)
        self.callback(output, 512, None, None)
        return output


class FakeBackend:
    def __init__(self) -> None:
        self.stream: FakeStream | None = None

    def OutputStream(self, **kwargs) -> FakeStream:
        self.stream = FakeStream(**kwargs)
        return self.stream

    def Stream(self, **kwargs) -> FakeStream:
        self.stream = FakeStream(**kwargs)
        return self.stream


class FailingBackend:
    def OutputStream(self, **_kwargs) -> FakeStream:
        raise RuntimeError("device does not support 96 kHz")

    def Stream(self, **_kwargs) -> FakeStream:
        raise RuntimeError("device does not support 96 kHz")


class CodecZeroBackend(FakeBackend):
    def query_devices(self):
        return [
            {
                "name": "vc4-hdmi-0",
                "max_input_channels": 0,
                "max_output_channels": 8,
            },
            {
                "name": "IQaudIO CODEC",
                "max_input_channels": 2,
                "max_output_channels": 2,
            },
        ]


class CleanupFailStream(FakeStream):
    def stop(self) -> None:
        raise RuntimeError("stop failed")

    def close(self) -> None:
        raise RuntimeError("close failed")


class AudioEngineTests(unittest.TestCase):
    def test_looper_records_closes_repeats_and_stops(self) -> None:
        looper = LoopRecorder(sample_rate=10, maximum_seconds=1)
        source = np.array([0.1, 0.2, 0.3], dtype=np.float32)

        looper.start()
        np.testing.assert_array_equal(looper.process(source), source)
        looper.close()
        repeated = looper.process(np.full(3, 0.9, dtype=np.float32))

        np.testing.assert_array_equal(repeated, source)
        self.assertEqual(looper.state, "looping")
        looper.stop()
        np.testing.assert_array_equal(
            looper.process(np.zeros(3, dtype=np.float32)),
            np.zeros(3, dtype=np.float32),
        )

    def test_file_playback_updates_real_snapshot(self) -> None:
        backend = FakeBackend()
        engine = AudioEngine(backend=backend)
        engine.source = FakeSource()

        engine.play()
        output = backend.stream.pump()

        self.assertTrue(np.any(output))
        self.assertEqual(engine.get_status().state, "playing")
        self.assertTrue(engine.get_status().output_waveform)
        engine.shutdown()

    def test_control_change_reaches_playback_callback(self) -> None:
        backend = FakeBackend()
        engine = AudioEngine(backend=backend)
        engine.source = FakeSource()
        engine.play()
        clean = backend.stream.pump()

        engine.update_controls(
            ControlState(0, 0, 100, 0, 100, 0, (0, 0, 0, 0, 0))
        )
        effected = backend.stream.pump()

        self.assertFalse(np.allclose(effected, clean))
        engine.shutdown()

    def test_callback_failure_mutes_output(self) -> None:
        backend = FakeBackend()
        engine = AudioEngine(backend=backend)
        engine.source = FakeSource(fail=True)
        engine.play()
        stream = backend.stream

        output = stream.pump()
        engine.service()

        np.testing.assert_array_equal(output, np.zeros((512, 2), dtype=np.float32))
        self.assertEqual(engine.get_status().state, "error")
        self.assertTrue(stream.closed)
        engine.shutdown()

    def test_starting_live_input_stops_file_source(self) -> None:
        backend = FakeBackend()
        engine = AudioEngine(backend=backend)
        source = FakeSource()
        engine.source = source

        engine.start_live_input()

        self.assertTrue(source.stopped)
        self.assertTrue(engine.live_mode)
        self.assertEqual(backend.stream.sample_rate, 96_000)
        engine.shutdown()

    def test_live_input_prefers_detected_codec_zero(self) -> None:
        backend = CodecZeroBackend()
        engine = AudioEngine(backend=backend)

        engine.start_live_input()

        self.assertEqual(backend.stream.device, (1, 1))
        engine.shutdown()

    def test_stream_open_failure_is_reported_without_leaving_source_running(self) -> None:
        engine = AudioEngine(backend=FailingBackend())
        source = FakeSource()
        engine.source = source

        with self.assertRaisesRegex(RuntimeError, "Audio device unavailable"):
            engine.play()

        self.assertTrue(source.stopped)
        self.assertEqual(engine.get_status().state, "error")
        self.assertFalse(engine.live_mode)

    def test_stream_cleanup_clears_reference_when_backend_cleanup_fails(self) -> None:
        engine = AudioEngine(backend=FakeBackend())
        engine.stream = CleanupFailStream(samplerate=96_000, callback=lambda *_args: None)

        engine.stop()

        self.assertIsNone(engine.stream)


if __name__ == "__main__":
    unittest.main()
