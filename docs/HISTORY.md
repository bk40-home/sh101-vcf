# sh101-vcf: history (2026-11-13 to 11-17)

How the filter came to be as it is: decisions, measurements, what was tried and dropped. The same record is kept in the claude.ai Project "M-Vsynth2" (claude/s1vave-ladder-filter-2026-11-16.md).

## 1. Why
S1Vave (AndrewGG88, an FM-1 firmware) imitates the SH-101 with an integer SVF cascade. Measured on the host, it has three problems:
- cutoff steps of up to 702 cents below 100 Hz;
- quiet signals at low cutoff freeze into DC;
- a note-on kick into the second SVF that can't start self-oscillation.

The aim became a *correct* SH-101 filter, built on existing FM-1 work (fm-106's IR3109, fmini-1) rather than a generic ladder; a first generic integer ladder was withdrawn. Key finding: the FM-1's AC791N has a single-precision FPU (`-mcpu=r3 -mfprev1`), so the filter can be float.

## 2. The circuit (service manual, p. 7 VCF board, p. 9 panel)
- **Stages:** IR3109 OTA stages, 68k/560 Ω inputs, C47/48/50/51 240p. Stage 1 sits 2.9% lower (R113 loads it).
- **Resonance:** VR18 (100k B) is fed from the filter output on connector 75; its wiper (76) feeds TR26 (phase splitter) → TR27 → C52 → R129 5.6k → D30/D31 (1S2473) → R113 15k → the stage-1 input.
- **Output:** R130 150k from connector 75 (the filter output) plus R132 150k from TR26's emitter (the wiper copy), into the BA662 VCA. So out = y4 (1 + 0.202 k), the 101's own level compensation.
- Crops: `schematic_*.png`.

## 3. The reference and the fit
- **Reference:** `model/sh101_ref.h` is double precision, 8× oversampled, with an exact Newton solve of the loop. Its tests pass against the analog 4-pole.
- **TAL capture:** TAL-BassLine-101 (demo) was captured in Ableton Live Lite: 41 takes, one Arrangement track with automation (`capture/`). Two takes had the demo's noise burst and were re-exported.
- **Fit:** `model/fit.py` fits in stages with the circuit kept as drawn and fwd held at the schematic's 0.202 (TAL implies 0.32).
  - fitted: drive 0.199, clip 0.514, knee 8.80, kmax 5.87, res_curve 1.149;
  - cutoff: 1.2464 octaves per slider unit, 268.4 Hz singing at FREQ 5.

## 4. The device module
**Solver history (FM-1 CPU, S1Vave, 8 voices, µs per half buffer, budget 5800):**

| Version | CPU (µs) | Result |
|:---|---:|:---|
| Semi-implicit, 2 passes (divisions) | 6500–7000 | Overloaded: distorted |
| Semi-implicit, 1 pass | 5509 | Fits, "coarse" |
| Division-free (fm-106 style, per-block reciprocals, diode table, tanh5 per stage) | 5000 | Fits. Also more accurate: pitch within 4.2 c of the reference, levels within 0.04 dB |

Float division is expensive on the AC79.

**Panel:**
- FREQ is the SH-101 slider: exponential, 7 Hz to 11.55 kHz.
- RES has a taper (`SH101_RES_TAPER`). In S1Vave, 8 voices singing from slider 7.2 overloaded the mix ("RES > 99 is a bit much"). M-Vsynth2 uses taper 2.0, so it sings from knob ~108.

## 5. M-Vsynth2 FILTER TYPE 5 (2026-11-17)
- **What it is:** M-Vsynth2's own type, not Synth1's. FPU flags and the CPU0 trap mask were added; CPU1 already masked its own.
- **Range:** the YAML's `hi: 5` is honoured by `gen_params.py` and `sy1.py`. Types 0–4 are bit-identical to before.
- **CPU:** SH101 39 against LP24 28 (DEBUG, 8-voice chord).
- **A/B against TAL on the FM-1** (`capture/make_capture_set.py --fm1`; the FM-1 driven by MIDI CC clip envelopes):
  - **Found and fixed:**
    - Synth1's filter envelope pulls the cutoff up to 2.1 knobs down even at AMOUNT 0 (INIT's SUSTAIN 21: about 2 semitones flat). The set now sends SUSTAIN 127.
    - KBDTRK 95, not 103 (103 read the wrong table row).
    - Synth2's per-voice output limiter rode the singing wave (9.4% THD at 17 Hz). Type 5 now skips it, as LPDL does.
  - **Result:**
    - corner 124/124 Hz;
    - slope −20.6/−20.6 dB/oct;
    - pitch within ±60 c from 20 Hz to 3.6 kHz;
    - THD 0.60% (TAL ~0.9%);
    - singing level 1 dB under TAL;
    - onset bracket identical.

## 6. Open: TAL's climb into self-oscillation (RES 7–8)
TAL climbs slowly: −26.5 dB at RES 7.25, −14 at 7.5, 0 at 8. It also keeps a broad resonance at RES 7 (a C2 saw loses 0.9–1.6 dB there, where we gain 0.5–1.9). The module goes from silent to full within about a quarter of a slider step.

`model/refit/sim.py` runs the module's takes and reproduces the FM-1 within 0.1–0.3 dB, so this is the model, not the port. Refits tried:

| Refit | Result |
|:---|:---|
| Diodes and drive only (`refit.py`) | Can't: TAL's loss at RES 7 hardly depends on level, so it is linear, not a diode effect |
| Loop curve and noise free as well (`refit2.py`) | The noise runs to its bound and the clean RES 2.5/5 resonance breaks |
| Loop gain from the clean points only (`refit3.py`: 4.727 (RES/10)^0.971, onset 8.42, close to the schematic's linear pot, 4.951 RES/10, onset 8.08), with TAL's 7.25–8 as ringing below onset | Needs input noise near −30 dB: audible hiss TAL doesn't have |

**Conclusion:** the circuit as drawn doesn't do what TAL does there. The fitted values stay (onset at TAL's 7.12). A real SH-101 through `capture/` would settle it.
