#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
portaudio_dir="$project_dir/vendor/root/usr/lib/aarch64-linux-gnu"
codec_state="$HOME/Pi-Codec/Codec_Zero_AUXIN_record_and_HP_playback.state"

if [ -f "$codec_state" ] && arecord -l 2>/dev/null | grep -Eqi "codec zero|iqaudio codec|da7212"; then
    /usr/sbin/alsactl -I -f "$codec_state" restore Zero || \
        printf '%s\n' "Codec Zero was detected, but its AUX mixer state could not be restored." >&2
fi

if [ -d "$portaudio_dir" ]; then
    export LD_LIBRARY_PATH="$portaudio_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

exec "$project_dir/.venv/bin/python" "$project_dir/main.py" --fullscreen --live-input
