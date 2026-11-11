# Capstone Design Alignment Review

**Project:** Tube Screamer Guitar Amplifier  
**Team:** SKIXG Engineering  
**Review date:** September 8, 2026  
**Software baseline:** Raspberry Pi 5, 8 GB; Raspberry Pi Codec Zero; 96 kHz live DSP

## 1. Review Basis

This review compares the software repository with the current team package at `/Users/gauravsdama/git/pallie/tamu courses/capstone/skixg_9_8_2026`. The primary team records were the Functional Specifications, Test Plan, updated Project Scope, current TAT presentation, PDR presentation, technical proposal, budget, schematic breakdown, and meeting notes. Example files and the AX84 theory document were treated as references rather than project requirements.

The software baseline follows the team's current Raspberry Pi 5/8 GB decision, while Codec Zero, the Waveshare 22676 touchscreen, mono line-level processing, physical tube-bias and master-volume controls, one enclosure, and one AC inlet remain unchanged. Earlier Raspberry Pi selections are retained below as discrepancies until the source records are revised.

## 2. Consistent Interfaces

| Topic | Team design | Software alignment |
| --- | --- | --- |
| Signal direction | Input, preamp, two tube stages, ADC, Pi effects, DAC, output | The documented and implemented live path follows this order. |
| Audio format | Monophonic product | DSP accepts one input channel and produces mono output duplicated at the codec boundary until one physical output channel is selected. |
| Digital effects | Delay, chorus, reverb, echo | All four are implemented as adjustable real-time stages. |
| Equalizer | Five adjustable bands | Five peaking filters are implemented at 100 Hz, 400 Hz, 1 kHz, 4 kHz, and 10 kHz. |
| Touchscreen | Raspberry Pi-controlled 7-inch display | Tkinter UI uses fixed 1024 x 600 Home, Effects, and EQ/Waveforms pages without scrolling. |
| Product input | Live analog audio | Codec live input is the product path. File playback is only a development fixture. |
| Product output | External line-level connection; no internal speaker | Software outputs through Codec Zero; documentation does not claim a speaker power stage. |
| Connectivity exclusions | No wireless control, MIDI, recording, or remote application | The product software requires no network and does not record audio. |
| Resource feasibility | Raspberry Pi target | CPU, RAM, temperature, throttling, callback, and stream stability are benchmarked. |

## 3. Items Requiring Team Reconciliation

| Priority | Topic | Current discrepancy | Required team action |
| --- | --- | --- | --- |
| Critical | Tube test stimulus | Test Plan applies 5 V at 100 kHz as a guitar-like input. This is outside the 20 Hz to 20 kHz product band and may exceed the approved input level. | Replace it with a level and frequency set derived from the approved input and tube-stage schematics. Begin at a current-limited safe level. |
| Critical | Tube supply | Updated Scope and Test Plan use 50 V; Functional Specifications describes approximately 233 V B+ from a 300 VCT transformer. | Hardware and test owners must approve one operating range and rewrite PR-01, GT-02 through GT-05, and FR-02 through FR-05 before powered testing. |
| Critical | Digital measurement method | Test Plan treats ADC output and Pi-to-DAC data as analog signals measurable in DC with an oscilloscope. | Use ALSA capture data/software analysis for samples and a logic analyzer only if I2S timing must be inspected. Use an oscilloscope at analog codec input/output nodes. |
| High | Raspberry Pi model | Earlier Functional Specifications identify Pi 4/2 GB, while the current team decision is Pi 5/8 GB. | Update the Functional Specifications, proposal, budget, BOM, FBD labels, and power calculations to Pi 5/8 GB. |
| High | Converter rate | Scope and proposal require 24-bit/196 kHz; Codec Zero supports up to 24-bit/96 kHz. | Approve 96 kHz with Codec Zero, or select hardware that satisfies a corrected 192 kHz requirement. |
| High | ADC/DAC architecture | Older FBDs show separate ADC and DAC blocks and SPI/I2S labels; the selected Codec Zero combines both functions and uses its HAT interface. | Revise the FBD to identify Codec Zero once, with ADC and DAC as internal logical functions and I2S/I2C reserved pins. |
| High | Output architecture | PDR shows a power output stage and transformer; TAT rev. 6 shows a voltage follower; Functional Specifications states AUX OUT can directly feed line output through an optional master pot. | Freeze one line-output schematic and use it in the FBD, schematic, BOM, and Test Plan. Do not describe a speaker-power stage unless it returns to scope. |
| High | Tube bypass | Scope and proposal require tube bypass, but the present software has no mode control and current hardware records define no bypass circuit. | Approve a fail-safe hardware bypass and its control interface, or formally remove the requirement from scope and acceptance documents. |
| Medium | Bias control | Scope says bias is manual-only; the POC has a Bias widget and older planning notes discuss Pi bias monitoring/control. | Keep physical bias independent of the Pi. Decide separately whether isolated read-only monitoring is required. Remove the POC widget from the deployed UI unless scope changes. |
| Medium | Volume control | Scope and Functional Specifications place master volume in hardware; the POC has a digital Volume control. | Hold digital gain at unity in the product profile and use the physical master control unless a separate digital trim is approved. |
| Medium | Presets | Scope excludes multiple saved presets; the POC has fixed factory preset buttons. | Treat current buttons as demonstrations and hide them in the product profile, or revise the scope to allow fixed non-user-saveable presets. |
| Medium | Universal input | Scope permits guitar or microphone, while the selected jack is mono TS and the analog interface is being designed for instrument input. | Define supported source level, impedance, connector, and conditioning for each input type. Until then, software documentation says guitar or separately approved source. |
| Medium | Output voltage | The requirement states +/-2 V line level without defining peak, peak-to-peak, RMS, load, frequency, or tolerance. | Add a complete measurement definition before writing acceptance limits or UI voltage displays. |
| Medium | THD requirement | THD below 5 percent may conflict with intentional tube distortion unless the operating point and test mode are defined. | Specify input level, frequency, gain setting, effects state, load, bandwidth, and whether the requirement applies to clean/bypass operation. |
| Low | Physical tube count | Records alternate between two stages and two complete dual-triode 12AX7 tubes. | State the number of gain stages, triode sections, physical tubes, and unused sections in the final schematic and BOM. |

## 4. Software Corrections Completed

- The live DSP neutral state now passes the input without adding a second software tube distortion. The physical tube stages provide the product's tube response.
- The Clean POC setting now disables all effects, sets EQ flat, sets bias to neutral, and sets digital level to unity.
- Product requirements no longer claim digital bias, software master volume, or preset storage.
- Raspberry Pi power instructions distinguish isolated USB-C bench bring-up from the final Mean Well 5 V one-inlet design.
- The software report identifies Codec Zero as one physical ADC/DAC board and treats older separate blocks as logical functions.
- The report records tube bypass, sample rate, output interface, mono channel selection, and team-document corrections as open work.

## 5. Release Gate

The software documentation is consistent with the confirmed baseline, but the full project package is not yet internally consistent. Before final system integration, the team must close the Critical and High items above, revise the owning documents, and review the final schematic, FBD, BOM, software report, and Test Plan together. A change to the codec, display, signal routing, physical controls, or sample-rate requirement requires another alignment review.
