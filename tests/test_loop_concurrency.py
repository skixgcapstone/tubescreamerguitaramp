import threading
import unittest
import numpy as np
from audio_engine import LoopRecorder


class LoopConcurrencyTests(unittest.TestCase):
    def test_callback_passes_input_through_while_ui_holds_lock(self):
        recorder = LoopRecorder(96000)
        block = np.ones(512, dtype=np.float32)
        with recorder._lock:
            self.assertIs(recorder.process(block), block)

    def test_loop_changes_while_audio_is_processing(self):
        recorder = LoopRecorder(96000)
        done = threading.Event()
        errors = []
        block = np.ones(512, dtype=np.float32)
        def callback():
            try:
                while not done.is_set():
                    result = recorder.process(block)
                    if result.shape != block.shape or not np.isfinite(result).all():
                        raise AssertionError('invalid output block')
            except Exception as error:
                errors.append(error)
        worker = threading.Thread(target=callback)
        worker.start()
        try:
            for _ in range(1000):
                recorder.start()
                recorder.process(block)
                recorder.close()
                recorder.stop()
        finally:
            done.set()
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
