# Raspberry Pi Integration Guide

Last reviewed: 2026-09-08

This guide uses the team decision to target a Raspberry Pi 5 with 8 GB RAM. Earlier capstone records that identify a Raspberry Pi 4 remain historical and must be updated by their owners.

## Hardware Baseline

| Function | Selection | Status | Integration note |
| --- | --- | --- | --- |
| SBC | Raspberry Pi 5, 8 GB | Selected | Baseline for the touchscreen, 96 kHz block DSP, and resource testing. |
| Superseded SBC | Raspberry Pi 4 Model B, 2 GB | Superseded | Appears in earlier Functional Specifications and must not be used as the current software target. |
| Audio codec | Raspberry Pi Codec Zero, SC0366 | Locked | 24-bit/96 kHz DA7212 codec on the 40-pin GPIO header. |
| Touch display | Waveshare 22676 / 70H-1024600-IPS-CT-B | Locked | 7-inch, 1024x600, five-point capacitive touch; HDMI video and USB touch through its development adapter. |
| Instrument input | Switchcraft 12A mono TS switching/shorting jack | Locked | Connect only to the designed high-impedance input buffer. |
| Line output | Switchcraft #11 mono TS jack | Locked | Connect only after the Codec Zero output interface and level verification. |

## Required Approval: Sample Rate

The proposal specifies `24-bit, 196 kHz` ADC performance. Codec Zero is specified as `24-bit, 96 kHz`, so it cannot satisfy that requirement.

The software and Codec Zero operate at 24-bit/96 kHz. The team must revise the proposal requirement to 96 kHz, select an approved higher-rate converter, or confirm that 196 kHz was intended to be 192 kHz and select compatible hardware.

## Safety Boundary

Tube-amplifier circuitry is hazardous. The Raspberry Pi and Codec Zero are low-voltage electronics.

- Never connect GPIO, Codec Zero signal pins, or display ground directly to B+, tube plates/grids, negative bias, or speaker outputs.
- Never connect the tube stage directly to Codec Zero AUX IN. Use a reviewed line-level interface with AC coupling, attenuation, protection, known impedance, and filtering.
- Never use GPIO as a tube-bias source or to drive a relay coil directly.
- Bias hardware must reach a safe state without the Pi when power, software, or communication fails.
- Have the analog interface, chassis grounding, protective earth, fusing, isolation, and bias circuit reviewed before powered integration.

## Physical Connections

### Pi, Codec Zero, And Display

1. Power the Pi down before installing the Codec Zero on the 40-pin header with standoffs.
2. Do not add loose I2S wiring. Codec Zero already uses the Pi I2S and I2C signals.
3. Do not reuse GPIO23, GPIO24, or GPIO27: Codec Zero assigns them to its LEDs and button.
4. Connect the Waveshare panel to its supplied adapter using the supplied 40-pin FPC, observing pin-1 orientation.
5. Connect the adapter's `Display` port to a Raspberry Pi 5 micro-HDMI port using a micro-HDMI-to-HDMI cable or adapter.
6. Connect the adapter's `Touch` port to a Pi USB port. It carries touch data and may provide adapter power according to the supplied display documentation.
7. For isolated bench bring-up, use only the adapter's specified 5 V source. In the final enclosure, power the display from the reviewed 5 V digital distribution. Never connect it to the B+, heater, or other tube supply rails.

The Waveshare fallback display configuration is:

```ini
hdmi_group=2
hdmi_mode=87
hdmi_cvt 1024 600 60 6 0 0 0
hdmi_drive=1
```

Use `/boot/firmware/config.txt` on current Raspberry Pi OS or `/boot/config.txt` on older images.

### Audio Wiring

```text
Switchcraft 12A TS input
  -> high-impedance input buffer
  -> two Class A tube stages
  -> protected line-level interface
  -> Codec Zero AUX IN
  -> Raspberry Pi DSP
  -> Codec Zero AUX OUT
  -> output level / optional master-volume interface
  -> Switchcraft #11 TS output
  -> external powered speaker or next approved line-level stage
```

Codec Zero AUX I/O is stereo while the amplifier path is mono. Choose one codec channel or use a designed resistive summing stage; never short left and right codec outputs together. Confirm AUX IN/AUX OUT pins against the product brief and board silkscreen before wiring.

- Block DC before AUX IN and the output interface.
- Set the tube-to-codec interface to stay inside AUX IN limits at the maximum expected tube signal.
- Use shielding, a defined ground strategy, series resistance, clamps, and filtering on the analog interface.
- AUX OUT is line-level, not speaker-level. The board's 1.2 W mono speaker connection is not the chosen #11 output path.
- Keep low-level audio away from mains, heaters, B+, HDMI, and switching wiring.

### GPIO Reservation

| Pi physical pins | Function | Rule |
| --- | --- | --- |
| 3, 5 | Codec Zero I2C control | Reserved. |
| 12, 35, 38, 40 | Codec Zero I2S | Reserved. |
| 13 / GPIO27 | Codec Zero button | Do not use for amplifier hardware. |
| 16 / GPIO23, 18 / GPIO24 | Codec Zero LEDs | Do not use for amplifier hardware. |
| 11 / GPIO17 | Future control candidate | Only through an approved opto-isolated input or transistor driver. |
| 15 / GPIO22 | Future fault input candidate | Only through an opto-isolated, hardware-defined input. |

Bias-control pins are intentionally unassigned until the analog bias circuit is designed and reviewed.

## Pi OS And Codec Setup

Install current 64-bit Raspberry Pi OS Desktop. During isolated bring-up, use the official 27 W Raspberry Pi 5 USB-C supply and active cooling suitable for sustained DSP testing. The final one-inlet enclosure uses the project digital supply only after its 5 V capacity, conductor sizing, connectors, fusing, grounding, voltage drop, and combined Pi, codec, and display load have been approved.

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y \
  python3-tk python3-venv python3-pip \
  alsa-utils i2c-tools python3-gpiozero python3-lgpio \
  libportaudio2 portaudio19-dev ffmpeg git
sudo reboot
```

Create the V2 environment and install the application dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
```

Codec Zero should configure from its HAT EEPROM. With the board physically
installed, verify both the HAT identity and ALSA devices first:

```bash
grep -a . /proc/device-tree/hat/*
aplay -l
arecord -l
```

If the HAT is not detected after powering down and reseating it, suppress the
default HAT overlay and add the official Raspberry Pi Codec Zero overlay to the
active boot configuration, then reboot:

```ini
dtoverlay=
dtoverlay=rpi-codeczero
```

Do not enable another audio-HAT overlay. For the project's stereo AUX IN to
AUX OUT path, install Raspberry Pi's mixer-state files and restore the AUX
profile after each boot:

```bash
git clone https://github.com/raspberrypi/Pi-Codec.git ~/Pi-Codec
sudo alsactl restore -f ~/Pi-Codec/Codec_Zero_AUXIN_record_and_HP_playback.state
```

`deploy/run-pi.sh` performs that restore automatically when it detects the
Codec Zero. Test with isolated, line-level equipment before connecting tube hardware:

```bash
deploy/test-codec-zero.sh status
deploy/test-codec-zero.sh tone
deploy/test-codec-zero.sh capture

aplay -l
arecord -l
amixer scontrols
speaker-test -c 2 -t sine
arecord -f S32_LE -r 96000 -c 2 -d 5 capture.wav
aplay capture.wav
```

## Bias And Controls

The project scope assigns tube-bias adjustment to manual potentiometers. The app's Bias slider is a POC display control and does not affect live product audio or GPIO. No Pi bias-control connection is approved. If bias monitoring is later required, define an isolated measurement interface, safe range, calibration procedure, and fault behavior before assigning any pins.

## Deployment

```bash
cd /home/<desktop-user>/capstoneSoftwareDemo
python3 main.py --fullscreen --live-input
```

For autostart, update the user, working directory, X authority, and project path in [deploy/tube-screamer.service](../deploy/tube-screamer.service), then run:

```bash
sudo cp deploy/tube-screamer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tube-screamer.service
systemctl status tube-screamer.service
```

For a password-free per-user deployment at `/home/gaurav/capstoneSoftwareDemo`, use the bundled user service:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/tube-screamer-user.service ~/.config/systemd/user/tube-screamer.service
systemctl --user daemon-reload
systemctl --user enable --now tube-screamer.service
systemctl --user status tube-screamer.service
```

The corresponding `deploy/run-pi.sh` launcher also loads the project-local
PortAudio runtime when it is present under `vendor/root/usr/lib/aarch64-linux-gnu`.

## Bring-Up Checklist

- [ ] Update the proposal, budget, BOM, FBD labels, and power calculations to the Raspberry Pi 5/8 GB selection.
- [ ] Resolve the 196 kHz requirement versus Codec Zero's 96 kHz limit.
- [ ] Confirm mechanical fit of Pi, Codec Zero, display adapter, cables, and standoffs.
- [ ] Confirm 1024x600 display and aligned touch input.
- [ ] Confirm `python3 main.py --fullscreen --live-input` launches on the Pi.
- [ ] Confirm `aplay -l` and `arecord -l` list Codec Zero.
- [ ] Complete isolated 96 kHz codec playback and capture tests.
- [ ] Measure the tube-interface input and AUX OUT levels before connecting the jacks.
- [ ] Document the mono-channel/summing decision.
- [ ] Confirm that tube bypass is retained or formally removed; if retained, approve its fail-safe hardware and software interface.
- [ ] Verify that the final UI omits POC-only file, preset, Bias, and Volume controls unless the scope is revised.
- [ ] Review physical bias safety and test safe failure behavior independently of the Pi.
- [ ] Complete a sustained test without hum, clipping, XRUNs, or ground loops.

## Source Material

- Current SKIXG package: `/Users/gauravsdama/git/pallie/tamu courses/capstone/skixg_9_8_2026`
- Functional specifications: `Schematic Stuff/Functional Specifications.docx`
- Current test plan: `Test Plan/Test Plan - SKIXG.docx`
- Updated project scope: `419 Things /419 Assignments/UPDATED SKIXG Project Scope - Tube Screamer Amplifier.docx`
- TAT functional block diagram: `TAT/SKIXG TAT Meeting 1.pptx`
- Codec Zero product brief: https://datasheets.raspberrypi.com/audio/codec-zero-phat-product-brief.pdf
- Raspberry Pi overlay list: https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README
- Waveshare 70H-1024600 guide: https://www.waveshare.com/wiki/70H-1024600
- PiShop Waveshare 22676 listing: https://www.pishop.us/product/7inch-ips-integrated-touch-display-1024x600-thin-and-light/
