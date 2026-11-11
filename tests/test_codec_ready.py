import unittest
from unittest.mock import Mock

from deploy.check_codec_ready import check_codec


class CodecReadyTests(unittest.TestCase):
    def backend(self, inputs=2, outputs=2):
        backend = Mock()
        backend.query_devices.return_value = [
            {'name': 'HDMI', 'max_input_channels': 0, 'max_output_channels': 2},
            {'name': 'RPi Codec Zero', 'max_input_channels': inputs,
             'max_output_channels': outputs},
        ]
        return backend

    def test_waits_for_both_directions(self):
        for inputs, outputs in ((0, 2), (2, 0)):
            backend = self.backend(inputs, outputs)
            with self.assertRaises(RuntimeError):
                check_codec(backend)
            backend.Stream.assert_not_called()

    def test_busy_device_is_not_ready(self):
        backend = self.backend()
        backend.Stream.side_effect = RuntimeError('Device busy')
        with self.assertRaisesRegex(RuntimeError, 'Device busy'):
            check_codec(backend)

    def test_probe_uses_codec_and_releases_it_without_playing(self):
        backend = self.backend()
        check_codec(backend)
        backend.Stream.assert_called_once_with(
            device=(1, 1), samplerate=96000, blocksize=512,
            channels=(1, 2), dtype='float32',
        )
        backend.Stream.return_value.close.assert_called_once()
        backend.Stream.return_value.start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
