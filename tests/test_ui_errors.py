import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from audio_engine import AudioEngine
from touchscreen_ui import TubeScreamerApp


class AudioActionTests(unittest.TestCase):
    def test_invalid_wav_shows_error_and_valid_file_can_be_loaded_afterward(self):
        import wave
        for contents in (b'', b'not a wave file'):
            with self.subTest(contents=contents), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'test.wav'
                path.write_bytes(contents)
                engine = AudioEngine()
                app = SimpleNamespace(audio_error='')
                with patch('touchscreen_ui.logging.getLogger'):
                    TubeScreamerApp._audio_action(app, lambda: engine.load_file(path))
                self.assertTrue(app.audio_error)
                with wave.open(str(path), 'wb') as output:
                    output.setnchannels(1)
                    output.setsampwidth(2)
                    output.setframerate(96000)
                    output.writeframes(b'\0' * 1024)
                TubeScreamerApp._audio_action(app, lambda: engine.load_file(path))
                self.assertEqual(app.audio_error, '')
                self.assertEqual(engine.get_status().state, 'loaded')
                engine.shutdown()
