"""Probe in a fresh process so PortAudio does not cache the boot-time device list."""
import sys


def check_codec(backend):
    for index, device in enumerate(backend.query_devices()):
        name = device['name'].lower()
        if not any(label in name for label in ('codec zero', 'iqaudio codec')):
            continue
        if device['max_input_channels'] < 1 or device['max_output_channels'] < 2:
            continue
        stream = backend.Stream(
            device=(index, index), samplerate=96000, blocksize=512,
            channels=(1, 2), dtype='float32',
        )
        stream.close()
        return
    raise RuntimeError('Codec Zero capture/playback device is not ready')


if __name__ == '__main__':
    try:
        import sounddevice
        check_codec(sounddevice)
    except Exception as error:
        print(f'Waiting for Codec Zero: {error}', file=sys.stderr, flush=True)
        sys.exit(1)
