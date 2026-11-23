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
# The official profile restores a quieter headphone/AUX output at each start.
# Use unity gain for the powered-speaker demo; this is not the speaker terminal.
# Override with CODEC_HEADPHONE_VOLUME (0..63) in the user service if needed.
codec_headphone_volume=${CODEC_HEADPHONE_VOLUME:-57}
case "$codec_headphone_volume" in
    ''|*[!0-9]*) printf 'Invalid CODEC_HEADPHONE_VOLUME: %s\n' "$codec_headphone_volume" >&2; exit 1 ;;
esac
if [ "$codec_headphone_volume" -gt 63 ]; then
    printf 'CODEC_HEADPHONE_VOLUME must be between 0 and 63.\n' >&2
    exit 1
fi
amixer -c Zero cset 'name=Headphone Volume' "$codec_headphone_volume,$codec_headphone_volume"
printf '%s\n' "Codec Zero ready; starting live audio."

exec "$project_dir/.venv/bin/python" "$project_dir/main.py" --fullscreen --live-input
