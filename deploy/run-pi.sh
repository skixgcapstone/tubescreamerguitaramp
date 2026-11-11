#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
portaudio_dir="$project_dir/vendor/root/usr/lib/aarch64-linux-gnu"
codec_state="$HOME/Pi-Codec/Codec_Zero_AUXIN_record_and_HP_playback.state"

if [ -d "$portaudio_dir" ]; then
    export LD_LIBRARY_PATH="$portaudio_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

attempt=0
until timeout 5 "$project_dir/.venv/bin/python" "$project_dir/deploy/check_codec_ready.py"; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        printf '%s\n' "Codec Zero did not become ready; exiting so the service can retry." >&2
        exit 1
    fi
    sleep 2
done

if [ ! -f "$codec_state" ]; then
    printf 'Missing Codec Zero mixer profile: %s\n' "$codec_state" >&2
    exit 1
fi
/usr/sbin/alsactl -I -f "$codec_state" restore Zero
printf '%s\n' "Codec Zero ready; starting live audio."

exec "$project_dir/.venv/bin/python" "$project_dir/main.py" --fullscreen --live-input
