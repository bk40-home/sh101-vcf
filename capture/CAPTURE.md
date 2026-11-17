# SH-101 filter capture: TAL-BassLine-101 in Ableton

The goal is 41 short WAVs that measure the filter: its cutoff taper, where it starts to sing, its response
against resonance, how it drives, and its keyboard tracking. You make one Live set with one track per take,
then do a single export.

## Files

| File | What it is |
|:---|:---|
| `midi/hold4.mid` | MIDI 48 held 4 s (6 s clip). Ableton shows MIDI 48 as **C2** |
| `midi/hold20.mid` | MIDI 48 held 20 s (22 s clip), for the noise takes |
| `midi/saw_c2.mid` | MIDI 36 held 4 s (6 s clip). Ableton shows it as **C1** |
| `midi/track.mid` | MIDI 24, 36, 48, 60, 72, 84, each 2 s with 0.5 s gaps (16 s clip) |
| `analyse.py` | Measures the WAVs: `python3 analyse.py <folder> [outdir]` |
| `takes.py` | The take list that every other file reads |
| `tests/synth_takes.py` | Self-test of the analysis on synthetic takes with known answers |

## 1. Set up the first track

1. Start a new Live set. Set **120 BPM** and **44.1 kHz** (Preferences → Audio → Sample Rate).
2. Create a MIDI track and load **TAL-BassLine-101**. Load its init/default patch, then make sure these are set:

| Control | Setting |
|:---|:---|
| VCO range | 8' |
| Source mixer: Pulse / Saw / Sub / Noise | 0 / 0 / 0 / 0, unless the take says otherwise |
| VCF Env / Mod / Kybd | 0 / 0 / 0, unless the take says otherwise |
| VCA | GATE |
| Envelope A / D / S / R | 0 / 0 / 10 / 0 |
| Portamento, LFO, arpeggiator, sequencer, bend | off or 0 |
| Velocity to VCF or VCA | off |
| TAL's effects (chorus, delay, etc.) | off |
| Quality or oversampling, if TAL offers it | highest |

3. **Exact values.** Click the device's **Configure** button, then move Freq, Res, Saw, Noise and Kybd so they
   appear in Ableton's device view. You can then type values instead of dragging. Slider position 5 is 50%
   there; if Ableton shows the value another way, note how.
4. **Level.** Set TAL's volume so the T0 take (below) peaks around **−6 dBFS**. Never change it after that.
   Keep the track fader at 0 dB, put no other devices on any track, and keep the master clean at 0 dB.

## 2. One track per take

In **Arrangement view**, drag the take's clip to **bar 1 (1.1.1)**. Duplicate the track (Ctrl/Cmd+D) for each
take, rename the track to the **take id exactly**, and change only what that take lists. Slider positions are
on TAL's 0–10 scale.

| Take ids | Clip | Settings (everything else as in step 1) |
|:---|:---|:---|
| `T0_open` | hold4 | Saw 10, Cutoff 10, Res 0 |
| `T1_cut00` … `T1_cut10` (11 tracks) | hold4 | Res 10, Cutoff = the number (`T1_cut05` = 5) |
| `T2_res0700` … `T2_res1000` (13 tracks) | hold4 | Cutoff 5, Res = the number ÷ 100 (`T2_res0725` = 7.25). Steps of 0.25 from 7 to 10 |
| `T3_open` | hold20 | Noise 10, Cutoff 10, Res 0 |
| `T3_res0000`, `_0250`, `_0500`, `_0750`, `_0900`, `_1000` | hold20 | Noise 10, Cutoff 5, Res = the number ÷ 100 |
| `T4_r0_lvl02`, `_lvl05`, `_lvl08`, `_lvl10` | saw_c2 | Cutoff 5, Res 0, Saw = 2 / 5 / 8 / 10 |
| `T4_r7_lvl02`, `_lvl05`, `_lvl08`, `_lvl10` | saw_c2 | Cutoff 5, Res 7, Saw = 2 / 5 / 8 / 10 |
| `T5_track` | track | Cutoff 3, Res 10, Kybd 10 |

**If the filter doesn't sing.** T1, T2 at high resonance and T5 have every source at 0 and rely on
self-oscillation. If such a track stays silent, raise Noise to the smallest value that starts it. Add `_n` to
that track's name (for example `T1_cut00_n`) so the analysis knows. Don't do this on the T2 tracks below the
point where it starts on its own.

## Quickest: the one-track set (recommended)

`sh101_capture.als` holds the whole capture on **one track**. It was made by `make_capture_set.py` from your
`clean.als`, so TAL-BassLine-101 is already loaded with its controls exposed.
- All 41 takes play back to back in the Arrangement, with 2 s gaps between them.
- TAL's Cutoff, Resonance, Saw, Noise and Keyboard are automated for each take.
- Everything else (envelope, VCA, bender, velocity, range, volume) is held fixed by automation too.
- The takes that need self-oscillation get a 0.1 s touch of noise at each note so the filter starts singing.

No knob setting, and the 8-track limit doesn't matter.

1. Open `sh101_capture.als`. Play it for a few seconds to check TAL sounds and the automation moves the knobs.
2. **File → Export Audio/Video**: Rendered Track **Main**, Render Start **1.1.1**, Render Length
   **226.0.0**, 44100 / 24-bit WAV, Normalize **off**. That's about 7.5 minutes of audio.
3. Split it into takes and check for the demo's noise bursts:

```sh
python3 split_takes.py <export>.wav sh101_capture.timeline.json takes
python3 analyse.py takes
```

`split_takes.py` lists any take the demo's burst landed in, with the bar to re-export from and how long.
Export just that range, save it as `<take id>.wav` into `takes`, and run `analyse.py` again.

Using another TAL set: expose the same controls with Configure, then run
`python3 make_capture_set.py your.als out.als`.

## Live Lite (8 tracks per set), by hand

Do the takes in **6 sets** of up to 8 tracks, exporting each set with the settings below.

| Set | Tracks |
|:---|:---|
| 1 | `T0_open`, `T1_cut00` … `T1_cut06` |
| 2 | `T1_cut07` … `T1_cut10`, `T5_track`, `T3_open`, `T3_res0000`, `T3_res0250` |
| 3 | `T3_res0500`, `_0750`, `_0900`, `_1000`, `T4_r0_lvl02`, `_lvl05`, `_lvl08`, `_lvl10` |
| 4 | `T4_r7_lvl02`, `_lvl05`, `_lvl08`, `_lvl10`, `T2_res0700`, `_0725`, `_0750`, `_0775` |
| 5 | `T2_res0800` … `T2_res0975` (8 tracks) |
| 6 | `T2_res1000` |

**The level must not change between sets.** Once TAL's volume is set in set 1, save that track's TAL state
as a preset and start every other set from it. Put all the exported WAVs in one folder, or in one folder per
set; `analyse.py` searches subfolders too.

## 3. Export

**File → Export Audio/Video:**

| Setting | Value |
|:---|:---|
| Rendered Track | **All Individual Tracks** |
| Render Start / Length | 1.1.1 / **12.0.0** (24 s, longer than the longest clip) |
| Include Return and Master Effects | off |
| Render as Loop | off |
| Convert to Mono | either |
| Normalize | **off** |
| Create Analysis File | off |
| Sample Rate / Bit Depth | **44100 / 24** |
| Dither | none |
| Encode PCM / file type | on / WAV |

Send the WAVs, plus the TAL version and a screenshot of its panel on any one track. Ableton names each file
after its track, so the names can stay as they are.

## 4. What the analysis gives

`python3 analyse.py <folder>` writes `report.md`, `calib.json` and three plots:

- **T1:** singing pitch per cutoff position (the taper), with level and distortion of the self-oscillation.
- **T2:** the resonance at which it starts to sing, found from how the oscillation grows.
- **T3:** the −3 dB corner and slope at resonance 0, then for each resonance: bass loss, peak frequency and
  peak height. Also the ratio of singing pitch to corner (an ideal ladder gives 2.30).
- **T4:** output and harmonics against saw level, with and without resonance (how the filter saturates).
- **T5:** octaves per octave and the error at each note.

These are the numbers the SH-101 reference model is fitted to, and the FM-1 module is then tested against
them. The analysis checks itself with `python3 tests/synth_takes.py`: it builds the 41 takes from a known
filter and confirms every number comes back.
