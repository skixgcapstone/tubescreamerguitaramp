#!/bin/sh
# Stop only the temporary, isolated Cliffs of Dover playback and start live input.
set -eu
pidfile=/tmp/capstone-song-playback.pid
if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    case "$pid" in ''|*[!0-9]*) echo 'Invalid playback PID; refusing to stop it.' >&2; exit 1 ;; esac
    if [ -r "/proc/$pid/cmdline" ]; then
        command_line=$(tr '\0' ' ' < "/proc/$pid/cmdline")
        pgid=$(ps -o pgid= -p "$pid" | tr -d ' ')
        case "$command_line" in
            *cliffs-of-dover.m4a*)
                if [ "$pgid" != "$pid" ]; then
                    echo 'Playback is not in its own process group; refusing to stop it.' >&2
                    exit 1
                fi
                /bin/kill -TERM -- "-$pid"
                ;;
            *) echo 'PID belongs to another process; refusing to stop it.' >&2; exit 1 ;;
        esac
    fi
    rm -f "$pidfile"
fi
systemctl --user start tube-screamer.service
systemctl --user --no-pager is-active tube-screamer.service
