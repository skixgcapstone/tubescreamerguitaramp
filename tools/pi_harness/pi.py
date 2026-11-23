#!/usr/bin/env python3
"""Small SSH-based Raspberry Pi diagnostics and desktop capture harness."""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / '.codex/pi-handoff/config.json'

def load_defaults():
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text())
        if not isinstance(data, dict):
            raise ValueError('expected a JSON object')
        return data
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Cannot read {CONFIG_PATH}: {exc}') from exc

STATUS = r'''set +e
printf '\n== Host and power ==\n'; hostname; uptime; command -v vcgencmd >/dev/null && vcgencmd get_throttled
printf '\n== Display connectors ==\n'; for f in /sys/class/drm/card*-*/status; do [ -r "$f" ] && printf '%s: %s\n' "$f" "$(cat "$f")"; done
printf '\n== Backlight requested settings ==\n'; for f in /sys/class/backlight/*/{brightness,actual_brightness,max_brightness,bl_power}; do [ -r "$f" ] && printf '%s: %s\n' "$f" "$(cat "$f")"; done
printf '\n== Audio devices ==\n'; cat /proc/asound/cards; command -v arecord >/dev/null && arecord -l
printf '\n== Application ==\n'; systemctl --user status tube-screamer.service --no-pager -l | head -22
printf '\n== Recent kernel diagnostics ==\n'; journalctl -k -b --no-pager | grep -Ei 'undervoltage|under.voltage|Goodix.*(error|fail)|dsi.*(error|fail)' | tail -20
true'''

SCREEN = r'''set -eu
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if command -v grim >/dev/null 2>&1; then
  for sock in "$XDG_RUNTIME_DIR"/wayland-[0-9]*; do
    [ -S "$sock" ] || continue
    export WAYLAND_DISPLAY="${sock##*/}"
    exec grim -t png -
  done
fi
if command -v scrot >/dev/null 2>&1; then export DISPLAY=:0; export XAUTHORITY="$HOME/.Xauthority"; exec scrot -o -; fi
printf '%s\n' 'No supported screenshot tool found. Install grim on the Pi for a Wayland desktop.' >&2
exit 2'''

METER = r'''import array, math, subprocess, sys
seconds = int(sys.argv[1]); service = 'tube-screamer.service'
def run(*args, **kw): return subprocess.run(args, **kw)
active = run('systemctl','--user','is-active','--quiet',service).returncode == 0
try:
    if active: run('systemctl','--user','stop',service,check=True)
    raw = subprocess.check_output(['arecord','-q','-D','hw:Zero,0','-f','S32_LE','-r','96000','-c','2','-d',str(seconds),'-t','raw'], timeout=seconds+12)
    data=array.array('i'); data.frombytes(raw)
    if sys.byteorder != 'little': data.byteswap()
    if len(data) < 2: raise RuntimeError('No samples captured')
    for channel in (0,1):
        samples=data[channel::2]; count=len(samples); scale=2147483648
        peak=max(abs(x) for x in samples)/scale
        rms=math.sqrt(sum((x/scale)**2 for x in samples)/count)
        clip=sum(abs(x)/scale >= .98 for x in samples)/count
        print(('left','right')[channel], 'peak', round(peak,6), 'rms', round(rms,6), 'clipped_fraction', round(clip,6))
finally:
    if active: run('systemctl','--user','start',service,check=True)
'''

def interface_for_mac(mac):
    try:
        result = subprocess.run(['networksetup','-listallhardwareports'], capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    for block in result.stdout.split('\n\n'):
        if mac.lower() in block.lower():
            match = re.search(r'^Device: (\S+)', block, re.M)
            if match: return match.group(1)
    return None

def main():
    defaults=load_defaults()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default=os.environ.get('PI_HOST', defaults.get('host', 'raspberrypi.local')), help='Pi IP address or hostname')
    parser.add_argument('--user', default=os.environ.get('PI_USER', defaults.get('user', os.environ.get('USER', 'pi'))))
    parser.add_argument('--interface', default=os.environ.get('PI_INTERFACE'), help='interface for link-local IPv6, e.g. en11')
    parser.add_argument('--host-key-alias', default=os.environ.get('PI_HOST_KEY_ALIAS', defaults.get('host_key_alias')), help='existing SSH known_hosts alias')
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('status',help='Read display, power, audio, and app status')
    p=sub.add_parser('screen',help='Capture the Pi desktop as a PNG')
    p.add_argument('output',type=Path)
    p=sub.add_parser('exec',help='Run an explicit shell command on the Pi')
    p.add_argument('command',nargs=argparse.REMAINDER)
    p=sub.add_parser('service',help='Control the project user service')
    p.add_argument('operation',choices=['status','start','stop','restart'])
    p=sub.add_parser('logs',help='Read recent project service logs')
    p.add_argument('--lines',type=int,default=100,choices=range(1,1001),metavar='1-1000')
    p=sub.add_parser('desktop',help='Run a temporary SSH-tunneled interactive desktop')
    p.add_argument('--port',type=int,default=5905)
    p=sub.add_parser('meter',help='Briefly capture input; interrupts active app')
    p.add_argument('--seconds',type=int,default=5,choices=range(1,31),metavar='1-30')
    p.add_argument('--interrupt-app',action='store_true',required=True,help='acknowledge stopping and restoring active app')
    args=parser.parse_args()
    host=args.host
    if host.startswith('fe80:') and '%' not in host:
        iface=args.interface or (interface_for_mac(defaults['adapter_mac']) if defaults.get('adapter_mac') else None)
        if not iface: parser.error('Link-local address needs --interface or PI_INTERFACE')
        host += '%' + iface
    ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=6']
    alias=args.host_key_alias
    if alias: ssh+=['-o',f'HostKeyAlias={alias}']
    ssh.append(f'{args.user}@{host}')
    if args.action=='status': command=STATUS
    elif args.action=='screen': command=SCREEN
    elif args.action=='service': command='systemctl --user '+args.operation+' tube-screamer.service'+(' --no-pager -l' if args.operation=='status' else '')
    elif args.action=='logs': command='journalctl _SYSTEMD_USER_UNIT=tube-screamer.service _UID=$(id -u) --no-pager -n '+str(args.lines)
    elif args.action=='desktop':
        if not 1024 <= args.port <= 65535: parser.error('desktop port must be 1024–65535')
        ssh[-1:-1]=['-o','ExitOnForwardFailure=yes','-L',f'127.0.0.1:{args.port}:127.0.0.1:{args.port}']
        command='export XDG_RUNTIME_DIR=/run/user/$(id -u); export WAYLAND_DISPLAY=wayland-0; exec wayvnc -e 127.0.0.1 '+str(args.port)
        print(f'Open vnc://127.0.0.1:{args.port} locally. Press Ctrl-C here to stop.',flush=True)
    elif args.action=='meter': command='python3 -c '+shlex.quote(METER)+' '+str(args.seconds)
    else:
        if not args.command: parser.error('exec requires a command')
        command=shlex.join(args.command)
    if args.action=='screen':
        completed=subprocess.run(ssh+[command],capture_output=True)
        if completed.returncode:
            sys.stderr.buffer.write(completed.stderr); return completed.returncode
        if not completed.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
            print('Capture did not return a PNG; no file written.',file=sys.stderr); return 1
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_bytes(completed.stdout)
        print(f'Saved {args.output}')
        return 0
    return subprocess.run(ssh+[command]).returncode

if __name__=='__main__': sys.exit(main())
