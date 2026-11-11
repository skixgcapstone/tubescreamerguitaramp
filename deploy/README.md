# Raspberry Pi deployment

Clone this repository into `~/capstoneSoftwareDemo` and follow the Raspberry Pi OS setup in the root README. The scripts use `.venv/bin/python` from that directory.

## Codec Zero mixer

Get the official mixer profiles:

```sh
git clone https://github.com/raspberrypi/Pi-Codec.git "$HOME/Pi-Codec"
```

`run-pi.sh` restores the AUX input / headphone playback profile to ALSA card `Zero`. This profile leaves the green speaker-terminal output muted. The passive-speaker demo used these additional settings, starting at low gain:

```sh
amixer -c Zero cset 'name=Lineout Gain Ramping Switch' on
amixer -c Zero cset 'name=Lineout Volume' 24
amixer -c Zero cset 'name=Lineout Switch' on
```

These speaker settings must be applied again after the launcher restores the AUX profile. The speaker terminals and AUX output are separate connections.

## PortAudio startup patch

The demo Pi timed out when starting a Codec Zero callback stream. `codec-zero-portaudio.patch` increases the ALSA thread startup wait from one to five seconds in PortAudio 19.7.0. This changes the startup timeout, not the audio block size or processing latency. The measured startup took about 2.05 seconds.

To reproduce the build on the Pi:

```sh
sudo apt install build-essential libasound2-dev curl
mkdir -p vendor/build
curl -fL https://files.portaudio.com/archives/pa_stable_v190700_20210406.tgz -o vendor/build/portaudio.tgz
tar -xzf vendor/build/portaudio.tgz -C vendor/build
cd vendor/build/portaudio
patch -p1 < ../../../deploy/codec-zero-portaudio.patch
./configure --with-alsa --without-jack --disable-static
make -j2
mkdir -p ../../root/usr/lib/aarch64-linux-gnu
cp -a lib/.libs/libportaudio.so* ../../root/usr/lib/aarch64-linux-gnu/
```

The launcher loads this project-local library when present. Downloaded sources and binaries stay under the ignored `vendor/` directory. PortAudio retains its own license in the source archive.

## Start at desktop login

```sh
mkdir -p ~/.config/systemd/user
cp deploy/tube-screamer-user.service ~/.config/systemd/user/tube-screamer.service
systemctl --user daemon-reload
systemctl --user enable --now tube-screamer.service
```

The service opens the app fullscreen with live input. Stop it with `systemctl --user stop tube-screamer.service` before running a separate audio test. The system service template is an alternative and requires editing its `User` and paths; do not enable both services.
