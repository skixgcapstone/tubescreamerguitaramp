# Tube Screamer Amplifier Control

Tkinter touchscreen control for the SKIXG hybrid tube guitar amplifier. The product interface uses fixed 1024x600 Home, Effects, and EQ/Waveforms pages. File playback remains available in a separate desktop development window and is not part of the Raspberry Pi product interface.

## macOS Setup

Clone the repository before following the setup instructions:

```bash
git clone https://github.com/skixgcapstone/tubescreamerguitaramp.git capstoneSoftwareDemo
cd capstoneSoftwareDemo
```

The deployment service templates expect the folder name `capstoneSoftwareDemo` under the target user's home directory. Edit their paths if you use another location.

Install the Homebrew Python/Tk versions that match each other, plus PortAudio and FFmpeg:

```bash
brew install python@3.14 python-tk@3.14 portaudio ffmpeg
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
python main.py
```

Verify Tkinter and audio devices with:

```bash
python -m tkinter
python -c "import sounddevice; print(sounddevice.query_devices())"
```

## Windows Setup

Install Python with Tcl/Tk and install FFmpeg so `ffmpeg.exe` and `ffprobe.exe` are on `PATH`.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python main.py
```

## Raspberry Pi OS Setup

```bash
sudo apt update
sudo apt install -y python3-tk python3-venv libportaudio2 portaudio19-dev ffmpeg
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
python main.py --fullscreen --live-input
```

For Codec Zero, see [the deployment notes](deploy/README.md) for the mixer profile and the PortAudio startup patch used on the demo Pi.

The app uses 96 kHz, 512-frame blocks and mono DSP duplicated to both output channels. PCM WAV files are decoded with Python and resampled to 96 kHz when needed. MP3 and M4A files are decoded by FFmpeg into a bounded queue.

Use headphones and low volume when testing live input to avoid acoustic feedback. Amplifier hardware may connect only through the protected line-level interface described in `docs/RASPBERRY_PI_INTEGRATION.md`.

## Touchscreen Controls

1. Open **Effects** from Home and tap a pad to enable or disable it.
2. Drag upward or downward on an effect pad to set its level; the selected value remains active until changed.
3. Select the information icon to adjust the effect's time, decay, rate, feedback, drive, or depth parameter.
4. Tap the looper's left half to capture, tap the right half to close and repeat it, and tap the left half again to stop. Loop playback replaces the current input.
5. Open **EQ + Waveforms** to adjust the five EQ bands while viewing input and output waveforms.
6. Open **System Status** for peak, RMS, dBFS, limiter, XRUN, callback, and latency data.

On a development computer, `python main.py` opens file and live-source controls in a separate window automatically and loads `Cliffs Of Dover (Instrumental).m4a` when it is present in the local Vantabeat library. Press `F12` to reopen that window if it is closed. The Raspberry Pi fullscreen/live-input launch does not open development controls or load a file. The generated waveform remains available when no audio stream is active.

## Resource Benchmark

```bash
python main.py \
  --benchmark-file sample.m4a \
  --benchmark-seconds 1800 \
  --benchmark-report reports/pi5-v2.csv \
  --benchmark-scenario worst
```

For a development-file benchmark, the selected file loops with worst-case effects. Raw measurements go to CSV and the summary/pass assessment goes to a JSON file with the same name. Software reports thermal and throttling indicators but marks electrical power measurement unavailable; watts require an external power meter.

Use `--benchmark-scenario idle`, `clean`, `worst`, or `live`. Clean and worst require `--benchmark-file`; live uses the default input/output devices.

## Verification

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the unit tests on Python 3.13 and 3.14. These tests do not verify physical audio wiring or touchscreen operation. Graphify is optional; if installed, run `graphify update .` to generate the local code graph.

To run the documentation builders, also install `requirements-docs.txt`. Generated documents, local audio, virtual environments, downloaded libraries, and internal legal drafts are excluded from Git. No project license has been selected yet.

## Project Map

| Path | Purpose |
| --- | --- |
| `main.py` | Application entry point |
| `touchscreen_ui.py` | Fixed-size Home, Effects, EQ/Waveforms, status, and development-tool windows |
| `audio_engine.py` | File/live stream lifecycle, bounded looper, callback, safe mute, and snapshots |
| `audio_sources.py` | Bounded WAV/FFmpeg decoding and live-input adapter |
| `dsp.py` | Stateful EQ, seven effects, and output limiter |
| `performance.py` | RAM, CPU, thermal, audio, CSV, and JSON benchmark reporting |
| `simulation.py` | Visual fallback when no real stream is active |
| `tests/` | DSP, source, engine, benchmark, and simulation tests |
| `docs/SOFTWARE_DOCUMENTATION_V2_8.md` | Living V2 requirements, architecture, verification, and risks |
| `docs/CAPSTONE_ALIGNMENT_REVIEW.md` | Cross-check against the current team hardware, scope, FBD, and test records |
| `deploy/` | Raspberry Pi launchers, service templates, and Codec Zero patch |
| `requirements-docs.txt` | Optional dependencies for documentation builders |
