# Raspberry Pi headless harness

A small SSH client for the capstone Pi. It runs locally using Python 3 and OpenSSH; it does not install an agent or require a network listener on the Pi. It uses SSH keys and existing `known_hosts` verification. Never commit passwords or private keys.

## Connect

Power the Pi, connect it to the computer over Ethernet, and verify the adapter has a link. Set your Pi address and username with `--host` and `--user`, or with `PI_HOST` and `PI_USER`. The default host is `raspberrypi.local`. For an IPv6 link-local address, specify the local Ethernet interface:

```sh
python3 tools/pi_harness/pi.py --host fe80::1234 --interface en11 --user pi status
```

For another Pi use `--host`, `--user`, `--interface` as needed, and optionally `--host-key-alias`. Environment variables `PI_HOST`, `PI_USER`, `PI_INTERFACE`, and `PI_HOST_KEY_ALIAS` provide alternatives. A local, gitignored `.codex/pi-handoff/config.json` may supply `host`, `user`, `adapter_mac`, and `host_key_alias`; on macOS the harness can locate that adapter by MAC. SSH authentication and host keys must already be configured; this tool will not automatically trust an unknown host. Use an explicit IPv6 scope interface for link-local addresses. `No route to host` or an inactive link indicates a physical/network issue, not an audio or GUI diagnosis.

## Inspect and operate

```sh
python3 tools/pi_harness/pi.py status
python3 tools/pi_harness/pi.py screen /tmp/pi-screen.png
python3 tools/pi_harness/pi.py logs --lines 50
python3 tools/pi_harness/pi.py desktop
python3 tools/pi_harness/pi.py service status
python3 tools/pi_harness/pi.py service restart
python3 tools/pi_harness/pi.py exec uname -a
python3 tools/pi_harness/pi.py exec sh -c 'journalctl _SYSTEMD_USER_UNIT=tube-screamer.service _UID=$(id -u) -n 50 --no-pager'
python3 tools/pi_harness/pi.py meter --interrupt-app --seconds 5
```

`status` reports display connector and requested backlight state, detected sound cards, user service, throttling and kernel errors. A DSI `connected` or a backlight brightness value is not proof the panel, cable, or power is physically working. `vcgencmd get_throttled` reports Pi undervoltage flags, not the voltage at the display connector.

`screen` captures the running Wayland desktop using `grim`, or an X11 session with `scrot`. It requires a running graphical session and one of those tools. On Raspberry Pi OS, `sudo apt install grim` is the usual Wayland setup; install only when appropriate. A screenshot shows the compositor's image, not proof that the physical display works. `desktop` starts the Pi’s installed WayVNC bound to Pi localhost and forwards it to local `127.0.0.1:5905` over SSH; open `vnc://127.0.0.1:5905` in a compatible viewer. It requires WayVNC and an active Wayland compositor, stops on disconnect or Ctrl-C, and does not create a persistent service. This setup can offer no VNC authentication: SSH protects the connection in transit, but any local user on either machine may be able to reach their loopback port while it runs. Use only on trusted machines; do not expose the port to the network. macOS Screen Sharing may prompt for a password even if the server advertises no authentication. 

`meter` temporarily stops the project service if it is active, captures up to 30 seconds from Codec Zero AUX input, prints per-channel digital peak, RMS and fraction at or above 98% full scale, then restarts the service if it was originally running. It requires `arecord`, the Zero device, and an unused device after stopping the service. It interrupts live audio, resets app state, and the launcher restores its mixer profile (including +6 dB Mixin PGA on this Pi). Digital levels do not measure voltage at a pin. If an SSH session or remote process is forcibly killed during capture, check and restore with `service status` and `service start`.

## Project-specific notes

- The intended signal path is generator or guitar → tube PCB J1 → PCB J3 → codec P1 AUX IN → DSP → P2 AUX OUT → PCB J4 / RV7 / J6 → powered speaker. The green codec terminal is a separate speaker output. See `docs/hardware/tube-pcb/` for the provided schematic and photos.
- Codec input signal and audio ground must be verified on the physical pads. Do not connect the powered speaker output to the line input. Scope/DC checks and hardware condition cannot be verified from SSH.
- The launcher waits for Codec Zero and restores the official AUX-input/headphone-output mixer profile on every start; manual mixer changes do not persist. `deploy/README.md` documents the optional speaker output and PortAudio patch.
- Capture and playback may be exclusive: stop the application deliberately for standalone ALSA measurements, and restore the original service state. Avoid independent recordings during a live test unless interruption is intended.
- A headless harness cannot repair a loose cable, missing display supply, broken screen, or determine analog wiring from software alone. Physical measurements and safe access remain necessary.
