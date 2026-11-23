# Raspberry Pi application stress-test matrix

| Test record | Details |
| --- | --- |
| Project | Tube Screamer Guitar Amplifier |
| Test date | November 11, 2026 |
| Software revision | `42b85c80a154f7b07842c86a7a293acab0e0c001` |
| Target | Raspberry Pi 5, 8 GB RAM, microSD boot, Codec Zero, Touch Display 2 |
| Audio configuration | 96 kHz; 512 frames per callback; mono input and stereo output |
| Method | Programmatic Tk control and callback tests on the Pi, with real Codec Zero audio processing running concurrently; separate automated regression tests |
| Final hardware run | 1,317 actions over 179.0 seconds, including a 60-second all-effects phase |
| Test signal | Temporary 440 Hz WAV for file playback; Codec Zero input for live processing |
| Output condition | Physical outputs muted. Speaker sound quality was not evaluated. |
| Overall result | Functional checks passed within the tested scope. Callback timing remains an open performance issue. |

**Status:** PASS means the stated result was observed for this test. OPEN means the criterion was not met. NOT TESTED means no result is claimed. Action counts below overlap; they are coverage details, not separate totals to add together.

## Final results

| ID | Test / procedure | Expected result | Final observation | Status |
| --- | --- | --- | --- | --- |
| UI-01 | Open Effects and EQ + Waveforms, return Home, and repeat navigation during audio processing. | Pages change without an uncaught exception or audio fault. | Navigation bindings exercised; randomized sequence included 56 Effects, 58 EQ and 38 Home actions. No uncaught exceptions or recorded audio faults. | PASS |
| UI-02 | Tap each of the seven effect pads; drag levels to the ends of the control range. | Effect handlers accept repeated taps and clamp drag values without failing. | Each pad's touch binding exercised. Randomized pad routines covered delay 52 times, reverb 37, chorus 47, echo 52, distortion 46, phaser 50 and flanger 37. No handler exceptions. | PASS |
| UI-03 | Open the information/settings dialog for each effect, change its parameter, and close it. | Dialogs can be opened, adjusted and closed repeatedly. | All seven information and Close bindings exercised; parameter endpoints also exercised in randomized pad routines. No uncaught exceptions. | PASS |
| UI-04 | Open System Status and Development Audio Tools twice, close them, and reopen them. | Repeated opening and closing does not leave the app unusable. | 41 randomized window routines completed without an uncaught exception. | PASS |
| UI-05 | Change effect levels, master volume, bias and five EQ bands while live audio runs. | Control updates are accepted while audio continues processing. | 45 randomized control routines used low, intermediate and high values; no recorded audio faults. | PASS |
| FILE-01 | Cancel the Load Track dialog. | Canceling returns to the app without starting a load or raising an exception. | Canceled selection completed without an uncaught exception. | PASS |
| FILE-02 | Select a corrupt WAV and a missing file. | The app reports the load error instead of allowing an uncaught exception. | Both invalid selections were handled in the final Pi run. Empty-WAV handling was additionally covered by regression testing. | PASS |
| FILE-03 | Load a valid WAV after an invalid WAV. | The error clears and a valid source can be loaded. | Regression test confirmed the error cleared and source state became `loaded`; valid WAV selection also completed on the Pi. | PASS |
| AUDIO-01 | Press Play before loading a file; repeat Pause and Stop in different states. | Invalid Play is reported; repeated actions do not crash the app. | Initial Play, Pause and Stop bindings exercised; invalid Play produced a handled message. No uncaught exceptions. | PASS |
| AUDIO-02 | Execute all ordered pairs of Load, Play, Pause, Stop, Live Input Toggle, Loop Toggle and Close Loop. | Every tested transition either completes or reports a handled error, without an audio fault. | All 49 pairs completed: 98 actions, with each action appearing 14 times. No uncaught exceptions or recorded audio faults. | PASS |
| LOOP-01 | Toggle and close loops repeatedly while the real audio callback runs. | Loop state changes do not cause a callback exception. | 65 loop-toggle and 54 close-loop actions were included across the randomized and ordered-pair tests. No recorded audio faults. | PASS |
| LOOP-02 | Change loop state concurrently with a separate processing thread. | Processing returns finite, correctly sized blocks and does not divide by zero. | Regression test completed 1,000 cycles. A separate aggressive scheduling check completed 1,574 cycles without error after the fix. | PASS |
| LOOP-03 | Process a block while a UI loop operation holds the loop lock. | The callback returns immediately rather than waiting for the UI. | Regression test confirmed input passes through unchanged when the lock is unavailable. | PASS |
| LOOP-04 | Record beyond the maximum loop length, then close the loop. | Recording storage stops growing at 30 seconds and the captured loop can play. | Recording reached exactly 2,880,000 samples; maximum was also 2,880,000. Closing changed the loop state to `looping`. | PASS |
| STRESS-01 | Run randomized navigation, controls, dialogs and looper actions alongside real audio processing. | No uncaught UI exceptions or recorded audio faults. | Final run totaled 1,317 actions; exception and audio-fault lists were both empty. | PASS |
| PERF-01 | Run all seven effects and boosted EQ for 60 seconds while changing pages. | Audio keeps advancing without capture overruns or playback underruns. | Audio position reached 60.101 seconds. Capture overruns: 0. Playback underruns: 0. | PASS |
| PERF-02 | Check the callback deadline during the all-effects phase. | Every callback completes within the 5.33 ms block interval. | 199 deadline misses remained. Final sampled callback time was 3.947 ms. This single sampled time is not a maximum or average. No buffer overruns or underruns were recorded in this phase. | OPEN |
| DSP-01 | Compare optimized delay processing against the original sample-by-sample calculation. | Outputs and feedback state remain equivalent through wraparound and delay changes. | Exact array comparisons passed for five buffer capacities, 30 blocks per capacity, including delays shorter than a block. | PASS |
| DSP-02 | Apply alternating extreme parameters with all seven effects enabled and nonzero test input. | Output remains finite and within the limiter bound. | 200 blocks passed; output remained finite and within the ±0.95 limit, allowing floating-point tolerance. | PASS |
| SYS-01 | Observe temperature and firmware throttling during testing. | No thermal or power throttling is reported during observations. | Sampled temperatures remained below 70°C; observed firmware throttling value was `0x0`. This was sampled monitoring, not a continuous temperature log. | PASS |
| REG-01 | Run the automated regression suite after the fixes. | All tests pass locally, on the Pi and in CI. | 37 tests passed locally and on the Pi. GitHub Actions completed successfully. | PASS |
| RESTORE-01 | End testing and restore the normal app service. | The normal app resumes live audio with Codec Zero. | Service reported `active`; ALSA capture and playback both reported `RUNNING`. Screenshot showed the fullscreen app with `AUDIO: PLAYING`. Deployed source hashes matched the committed files. | PASS |

## Errors found and disposition

| Issue | Observed failure | Change made | Final disposition |
| --- | --- | --- | --- |
| E-01 — Invalid WAV handling | A corrupt WAV raised an exception outside the UI's error handler. An empty WAV could also escape that handler. | Added handling for WAV-format and end-of-file errors, including a message for an empty/incomplete file. | Fixed in the tested cases. Invalid-file recovery regression passed. |
| E-02 — Concurrent loop changes | An aggressive concurrency test reproduced division by zero when loop state changed during processing. | Protected shared loop operations with a lock. The audio callback uses a nonblocking attempt and passes input through if the lock is busy. | Fixed in the tested cases. Concurrency regression and final Pi run completed without this fault. |
| E-03 — DSP processing time | All effects together took roughly 6–7 ms per block, exceeding the 5.33 ms interval. The initial sustained phase recorded 56 underruns and 56 overruns. | Replaced per-sample delay work with bounded vector operations; reduced scalar-conversion overhead and cached EQ coefficients during each block. | Improved. Final sustained phase had zero underruns/overruns and advanced for the full 60 seconds. The remaining 199 deadline misses keep strict timing compliance open. |

**Short error summary:** Testing found three problems: invalid WAV files could escape the error handler, rapid loop changes could cause a division-by-zero error, and running all effects together could exceed the audio processing deadline. File-error handling and loop synchronization were corrected, and the DSP was optimized. The final run had no uncaught exceptions, audio faults, or buffer underruns/overruns. Callback deadline misses still occurred under maximum load, so timing remains a follow-up item.

## Coverage limits

| Check | Status | Reason |
| --- | --- | --- |
| Every possible action order | NOT TESTED | The run covered randomized sequences and all 49 ordered pairs of seven audio actions, not every possible sequence. |
| Physical touch and simultaneous multitouch | NOT TESTED | Tk bindings and handlers were exercised programmatically. Physical finger input was not used. |
| Audible output and speaker quality | NOT TESTED | Outputs were muted during the stress test. |
| Power loss, cable removal and hardware reconnection | NOT TESTED | Hardware remained connected during these tests. |
| Long-duration operation | NOT TESTED | The final hardware run lasted approximately three minutes. It was not an hours-long soak test. |
| CLI benchmark modes and keyboard shortcuts | NOT TESTED | These were not explicitly exercised by the hardware stress harness. |

## Evidence

- [Final raw results](../../reports/pi-stress-final.json)
- [Initial raw results](../../reports/pi-stress-before.json)
- [Intermediate results after file/loop fixes](../../reports/pi-stress-ui-fixed.json)
- [Hardware test harness](../../reports/pi-stress-harness.py)
- [Restored app screenshot](../../reports/stress-restored.png)
- [Source revision](https://github.com/skixgcapstone/tubescreamerguitaramp/commit/42b85c80a154f7b07842c86a7a293acab0e0c001)
- [Successful CI run](https://github.com/skixgcapstone/tubescreamerguitaramp/actions/runs/43083628849)

The raw reports and screenshot are local files in the ignored `reports/` directory. They are not included in the GitHub repository. The test date follows the development-session date; Pi wall-clock timestamps were not used to establish the calendar date. Run duration comes from the recorded start/end interval.
