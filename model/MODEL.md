# SH-101 VCF reference model (step 2)

This is the "truth" the FM-1 filter module will be tested against. It solves the circuit exactly every sample,
8× oversampled, in double precision. It runs on the host only and has no CPU limits.

Its structure and most of its constants are now read from the **SH-101 service manual's circuit diagram**
(Nov 1982, page 7, the VCF block around IC14 IR3109, TR26/TR27 and D30/D31, with VR18 RES on the control
board). Two things are still open:
- the level the sources reach the filter at (`drive`);
- the cutoff slider's taper.

The TAL captures fit those two and check everything else.

## Files

| File | What it is |
|:---|:---|
| `sh101_ref.h` | The model (C, double). Header only |
| `sh101_ref_lib.c`, `sh101ref.py` | Shared library and its Python face (`Model`, `params`). The library builds itself on first import |
| `ref_test.py` | Checks that the model computes what it claims to |
| `render_takes.py` | Renders the capture kit's 41 takes through the model, for `analyse.py` |
| `schematic_*.png` | The crops of the service manual this file reads from, so the reading can be checked |

```sh
python3 ref_test.py                                    # about 10 s
python3 render_takes.py build/model [--set drive=0.4 ...]
python3 ../capture/analyse.py build/model build/model/analysis
```

## From the schematic

| Part | Value | What it does |
|:---|:---|:---|
| IC14 IR3109, stage inputs R114/R117/R118/R119/R121/R124/R122 | 68k | Each stage's input node sums the previous output and its own output through 68k |
| R115, R116, R120, R123 | 560 Ω to the bias rail | Each input node's divider. The OTA sees about 1/123 of the input |
| C47, C48, C50, C51 | **240p**, all four | Stage capacitors. All equal on this sheet |
| VR18 (RES) | **100k B**, a potentiometer: filter output on top, wiper to TR26's base, bottom to ground | The resonance amount r = position/10, linear |
| TR26 | Emitter R131 10k to ground; collector R136 15k to the decoupled supply (R135 1k, C54 10µ) | **Phase splitter**: the emitter carries +r·y4, the collector −1.5·r·y4 |
| TR27 | Emitter follower from TR26's collector (its emitter resistor is unlabelled; 33k per OpenMusicLabs) | Drives the feedback network |
| C52 → R129 | 10µ, **5.6k** | From TR27 to the diode node |
| D30, D31 | **1S2473** pair, back to back, to the bias rail | Clip the feedback |
| R113 | **15k** | Diode node → stage 1's input node (pin 2) |
| R130, R132 | **150k each**, into the VCA (BA662) input | Output = filter output + TR26's emitter, equal weights |
| R109–R112 | 150k / 680k / 470k / 820k via C45 to pin 2 | The source mixer feeding the filter |

**What follows from these values:**
- **Stage scale.** The OTA's tanh(Vd/2Vt) through the 68k/560 divider gives a linear range
  **Vs = 2·Vt·68k·(1/560 + 2/68k) = 6.38 V**. Model units are this Vs.
- **Stage 1 is slightly different.** Its input node also carries R113 15k, so its pole sits
  1/560+1/68k+1/15k over 1/560+2/68k = **2.9% lower** (`cap[0] = 1.0286`).
- **Loop gain.** k = (TR26 gain 15k/10k) × (no-diode divider 15k/(5.6k+15k)) × (injection weight 68k/15k)
  × r = **4.951·r**. That puts the start of self-oscillation at **RES 8.08**, small-signal.
- **The diodes sit after the pot.** VR18 sets TR26's drive, and the clipping comes later, so the feedback is
  clipped at a fixed level whatever the resonance (`clip_place = 1`).
- **Diode constants.** The 1S2473 is treated like a 1N4148 (Is 2.52 nA, n 1.752). Its equation behind
  5.6k/15k, scaled to stage units, gives vd = 0.0322 and c = 1.46e-5, so **clip = 0.346, clip_sharp = 10.77**.
- **Output, unclipped.** The output is y4 + r·y4 = **y4·(1 + k/4.951)**, with the emitter copy taken before
  the diodes (`fwd = 0.202`, `fwd_from = wiper`). Small-signal bass loss is (1 + 0.202k)/(1 + k):
  **−7.3 dB at RES 5, −9.5 dB at RES 10**, against −10.9 and −15.5 dB for a plain ladder.

**Not on the sheet, or not read:**
- The source levels, and which mixer resistor is which source. This is `drive`, fitted from T4.
- The CV and expo scaling of the cutoff: VR17 FREQ 100k B through R184–R187 into IC18, with the VR8 "VCF
  WIDTH" trim. This is `cut_hz0` and `cut_oct`, fitted from T1.
- The 1S2473's exact constants (1N4148 values are used).

**Corrections to earlier assumptions:**
- A forum post said one of the four capacitors differs; on this sheet all four are 240p.
- The earlier default (diodes before the pot, output copy taken after the diodes) was wrong on both counts.

## Equations

Each oversampled sample is solved by trapezoidal integration, with each stage pre-warped:

    y_i = s_i + g_i·tanh(x_i − y_i),   g_i = tan(π·fc/cap_i / fs_os),   x_1 = u,  x_i = y_(i−1)
    the 101:  v + c·sinh(v/vd) = k·y4,   u = x − v,   out = y4·(1 + fwd·k)
    then s_i ← 2·y_i − s_i

- **Solver.** Newton on all five unknowns (y1..y4, v) together, from the last sample's solution, stopping at
  a step below 1e-13.
- **Input level.** The input enters as x = drive·input plus a noise floor (1e-4, about −80 dB), and the
  output is divided by drive.
- **Resampling.** Kaiser-windowed sinc, 96 taps per phase.
- **Other layouts kept as options.** Diodes before the pot (`clip_place = 0`) and an output copy taken after
  the diodes (`fwd_from = 0`).

## Parameters

| Name | Default | Source | Still to check or fit with |
|:---|:---|:---|:---|
| `cap` | 1.0286, 1, 1, 1 | Schematic (240p ×4, R113 on stage 1) | T3 corner and slope |
| `kmax`, `res_curve` | 4.951, 1 | Schematic (TR26 15k/10k, R129 5.6k, R113 15k; VR18 100k B) | T2 onset (predicts 8.08), T3 peaks |
| `clip_place` | 1 (after the pot) | Schematic | T2 level growth |
| `clip`, `clip_sharp` | 0.346, 10.77 | Schematic (1S2473 ≈ 1N4148, 5.6k/15k) | T1 level and THD |
| `fwd`, `fwd_from` | 0.202, wiper | Schematic (R130 = R132 = 150k from TR26's emitter) | T3 bass loss |
| `drive` | 0.3 | **Estimate** | T4 |
| `cut_hz0`, `cut_oct` | 10 Hz, 1.097 | **Estimate** (10 Hz–20 kHz) | T1 |
| `kybd_oct` | 1 | Spec (1:1 at KYBD 10) | T5 |
| `noise_floor` | 1e-4 | Estimate | T1 start-up |
| `os`, `tol`, `max_iter` | 8, 1e-13, 60 | Numerics | — |

## What `ref_test.py` shows

| Check | Result |
|:---|:---|
| Small signal against the analog 4-pole, equal poles, k 0/2/3.5, 50 Hz–15 kHz, above −60 dB | Within **0.028 dB** |
| Forward copy, (1+f·k)/(1+k) | 0.6255 against 0.625 |
| Solver on a full-scale square, drive 1.0, k 4.4, cutoff jumping | Every sample solved to below **1e-12**; mean 3.0 iterations, worst 13 |
| Oversampling, driven saw at k 3.2 | 8× matches 16× within **90 dB** (4×: 76 dB) |
| Self-oscillation with the schematic diodes | Silent at k 3.9; sings at 4.05, 4.2 and 4.4, 4–10 cents flat |
| Pitch in the small-amplitude limit | **500.005 Hz** for a 500 Hz cutoff |
| Diode placement | After the pot (the 101): level 0.25 → 0.41 for k 4.1 → 5.0, nearly flat. Before the pot: 1.0 → 2.1 |

## Schematic model through the capture kit

These come from `build/model/analysis/report.md`. They're the model's predictions for the TAL captures.

| Take | Prediction |
|:---|:---|
| T1 | **Clean self-oscillation**: 0.42% THD at −3.0 dB re the open saw, the same at every cutoff. Taper 1.094 octaves per slider unit (the estimate) |
| T2 | Silent at RES 8.0, singing at 8.25. **Onset 8.13** (small-signal prediction 8.08) |
| T3 | Bass loss −5.5 / −7.9 / −8.2 dB at RES 2.5 / 5 / 7.5. RES 9 and 10 are already self-oscillating, so their noise response reads differently |
| T4 | Resonance 7 lowers the level by 4.0–4.2 dB at every saw level (with drive 0.3 the stages stay fairly linear) |
| T5 | 1.000 octaves per octave |

`analyse.py` changed again, and the self-test still passes. A filter whose feedback is diode-limited jumps
straight to full level once it starts. That breaks the "power grows linearly" extrapolation, so the onset is
now kept inside the measured bracket: last silent step, first singing step.

## Next

1. **Step 6, when the TAL bounces arrive.** Fit `drive` and the cutoff taper, then compare everything else as
   a check of the schematic reading. If the onset, bass loss or oscillation level disagree, the schematic
   values tell us which part to look at.
2. **Step 3.** The FM-1 module `obv_sh101.h` (float, on fm-106's IR3109 stages), tested against this model.

## Sources

- **Roland SH-101 service notes** (Nov 1982): circuit diagram p. 7 (all values above) and parts list
  (IR3109, BA662A, 1S2473).
- **Electric Druid**, "Roland filter designs with the IR3109 or AS3109": phase splitter, output-side
  compensation, clipping diodes; R19 (TR27's emitter resistor) 33k per OpenMusicLabs.
- **Ultramaster KR-106** (GPL-3.0): IR3109 stage law. **Mz101** (AGPL-3.0): same structure, cross-check only,
  no code taken.
