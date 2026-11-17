# A/B: TAL-BassLine-101 against the FM-1 (M-Vsynth2 FILTER TYPE 5)

`sh101_ab.als` (`make_capture_set.py <your TAL set>.als sh101_ab.als --fm1`) is your `clean.als` with two parts:
- **Track 1:** TAL, as before: the 41 takes, automated.
- **Track 2, "FM-1 SH101":** the same notes, with the same panel settings sent to the FM-1 as MIDI CC envelopes in its clip.

The same `analyse.py` measures both recordings, and `compare_ab.py` puts them side by side.

## Set up (once)

1. **FM-1:** flash the M-Vsynth2 build with type 5, plug it in by USB, and load the **INIT** patch. Every setting the test needs is sent by CC at the start, including FILTER TYPE = SH101.
2. **Open `sh101_ab.als`.** On track 2 (FM-1 SH101), set **MIDI To** to the FM-1 (channel 1).
3. **Check the CC lanes** (30 s). Click the FM-1 clip, open its **Envelopes** tab, choose **MIDI Ctrl**. The automated controllers (red LEDs) should be **49, 50, 51**, plus 17, 24, 25, 27, 28, 33, 53 and the others.
   - If they read two lower (47, 48, 49, …), tell me and I'll rebuild with the right offset.
4. **Track 3** (audio): set **Audio From** to the FM-1's USB audio, monitor **In** or **Auto**, and arm it.

## Record and export

1. Go to the **Arrangement**, put the cursor at **1.1.1**, press **Record**, and let it run to the end (bar 227, 7.5 minutes). TAL plays on track 1 at the same time; that doesn't matter.
2. **Export the TAL track** as before (solo track 1, 226 bars from 1.1.1) → `tal_ab.wav`.
3. **Export the FM-1 recording** (solo track 3, the same 226 bars from 1.1.1) → `fm1_ab.wav`.

## Measure and compare

`run_ab.ps1` does all of it (TAL is measured once, then reused): `.\run_ab.ps1 -Fm1 "<the FM-1 export>.wav"`. By hand,
from the folder with the scripts, in PowerShell:

```powershell
py split_takes.py tal_ab.wav sh101_ab.timeline.json tal
py analyse.py tal tal\analysis
py split_takes.py fm1_ab.wav sh101_ab.timeline.json fm1
py analyse.py fm1 fm1\analysis
py compare_ab.py tal\analysis\calib.json fm1\analysis\calib.json sh101_ab.timeline.json ab_report.md
```

Send me `ab_report.md`, plus both `calib.json` files if you can. Also give each recording a listen: the singing FREQ sweep (T1) and the noise takes (T3) are where the two filters' character shows.

## How the FM-1 is set per take

| Takes | TAL | FM-1 |
|:---|:---|:---|
| FREQ | slider 0..10 | knob 12.7 × slider (type 5's FREQ is the SH-101 slider) |
| RES | slider 0..10 | knob 127 √(slider/10), type 5's taper. The knobs are whole numbers, so the timeline holds the real slider value (T2 compares on that) |
| Keyboard (T5) | 10 | KBDTRK 95 (1.0009 oct/oct) |
| Saw (T0, T4) | Saw slider | OSC1 SAW. Level by MIX against an OSC2 triangle parked at note 117 (~6.6 kHz; the filter, near 270 Hz in T4, all but removes it) |
| Noise (T3) | Noise slider 10 | MIX 127, OSC2 NOISE |
| No source (T1, T2, T5) | everything at 0, plus TAL's noise kick | MIX 127, OSC2 SAW with TRACK on, PITCH +60, KEY SHIFT +24: above note 127 the oscillator is muted, so the filter starts from its own noise, as the 101 does. T5's C1 and C2 stay below 127 and leak a quiet saw (TAL bottoms out there anyway) |
| Fixed | VCA gate, env 0 | AMP ENV A 0, S 127, R 0; FILTER AMOUNT 0; SAT 0; LFO depths 0; delay, chorus, effect, unison off |

The FM-1 goes through M-Vsynth2's output bus: its TONE one-pole is at INIT (64), and so is the output limiter. TAL goes through its own output. Neither should matter for pitch, onset or the shape of the response, but keep it in mind for absolute levels; the comparisons are relative to each capture's own T0.
