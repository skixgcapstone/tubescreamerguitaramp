#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
state_file="$HOME/Pi-Codec/Codec_Zero_AUXIN_record_and_HP_playback.state"
test_wav="/tmp/capstone-codec-zero-tone.wav"
capture_wav="/tmp/capstone-codec-zero-capture.wav"
pcm_device="plughw:CARD=Zero,DEV=0"

if ! grep -Eqi "codec zero|iqaudio codec|da7212|\[Zero[[:space:]]*\]" /proc/asound/cards; then
    printf '%s\n' "Codec Zero is not detected. Power down, seat it on the full 40-pin header, and reboot." >&2
    exit 2
fi

if [ ! -f "$state_file" ]; then
    printf 'Missing official mixer state: %s\n' "$state_file" >&2
    exit 3
fi

printf '%s\n' "Detected ALSA cards:"
cat /proc/asound/cards
printf '%s\n' "Loading the official stereo AUX IN -> AUX OUT profile..."
/usr/sbin/alsactl -I -f "$state_file" restore Zero

case "${1:-status}" in
    status)
        printf '%s\n' "Codec Zero is detected and its AUX mixer profile loaded."
        ;;
    tone)
        printf '%s\n' "Generating a quiet 440 Hz stereo test tone..."
        "$project_dir/.venv/bin/python" - "$test_wav" <<'PY'
import math
import struct
import sys
import wave

path = sys.argv[1]
rate = 48_000
seconds = 2
amplitude = 0.05
with wave.open(path, "wb") as output:
    output.setnchannels(2)
    output.setsampwidth(2)
    output.setframerate(rate)
    for frame in range(rate * seconds):
        sample = int(32767 * amplitude * math.sin(2 * math.pi * 440 * frame / rate))
        output.writeframesraw(struct.pack("<hh", sample, sample))
PY
        printf '%s\n' "Playing the tone through Codec Zero AUX OUT..."
        aplay -D "$pcm_device" "$test_wav"
        ;;
    capture)
        printf '%s\n' "Recording five seconds from Codec Zero AUX IN..."
        arecord -D "$pcm_device" -f S32_LE -r 96000 -c 2 -d 5 "$capture_wav"
        printf '%s\n' "Playing the recording through Codec Zero AUX OUT..."
        aplay -D "$pcm_device" "$capture_wav"
        ;;
    *)
        printf 'Usage: %s [status|tone|capture]\n' "$0" >&2
        exit 64
        ;;
esac
