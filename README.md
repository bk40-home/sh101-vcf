# sh101-vcf

The Roland SH-101's VCF (IR3109) and its resonance circuit as one C header, `sh101_vcf.h`. It runs in single-precision float, with no libm and no division per sample. This repo also holds everything that shows it is right: a double-precision reference of the same circuit, the fit to TAL-BassLine-101, the Ableton capture kit, and the A/B against the FM-1.

Used by:
- **M-Vsynth2** as FILTER TYPE 5 (`firmware/src/sh101_vcf.h`);
- **S1Vave** (fork, as `obv_sh101.h`, which this header supersedes);
- later M-vance, Jteensy8000's VAFilterCore and our own synth.

GPL-3.0-only (see LICENSE). The structure follows fm-106's `fm106_vcf.h` (PatttF/fm-106, GPL-3.0); the circuit values come from the SH-101 service manual.

## The module

```c
#include "sh101_vcf.h"            /* override any fitted value or limit with a #define before the include */
sh101_init();                                           /* once: the diode and resonance tables */
sh101_coef(&c, sh101_knob_cut(knob_q16), sh101_panel_res(res_knob));   /* per control block (cached) */
y = sh101_process(&c, &s, x);                           /* per sample, float: 1.0 = a full-scale oscillator */
y = sh101_step(&c, &s, in);                             /* or int32: +-65536 = a full-scale oscillator */
```

**Panel:**
- **FREQ:** the SH-101 slider, exponential, 1.25 octaves per slider unit, 268 Hz singing at the middle. Limits `SH101_CUT_MIN_HZ`/`SH101_CUT_MAX_HZ` (7 Hz to 11.55 kHz).
- **RES:** slider 0..10, up to `SH101_RES_MAX`, curved by `SH101_RES_TAPER` (1.0 = the 101's linear slider; M-Vsynth2 uses 2.0, so it sings near the top of the knob).
- **Singing level:** `SH101_SING_TRIM` (1.0 = the circuit, +5.6 dB over a full oscillator) eases the output down above the onset. For polyphony use about 0.4 (−8 dB at full RES), as M-Vsynth2 does, or chords run into the output limiter.

**On the FM-1 (AC791N):**
- Build with `-mcpu=r3 -mfprev1 -ffp-contract=off` and mask the FP exception traps (`EMU_CON` bits 16–20) on each core.
- The output peaks near 1.5 × a full oscillator when singing, so leave headroom. Don't put it behind a fast per-voice limiter: that adds THD.
- **Cost:** M-Vsynth2 DEBUG, an 8-voice chord: SH101 39 against LP24 28.

## The layout

| Folder | What |
|:---|:---|
| `sh101_vcf.h` | The module |
| `docs/` | `HISTORY.md` (decisions, measurements, what was tried) and the schematic crops |
| `model/` | The reference: `sh101_ref.h` (double, 8× oversampled, Newton on the whole loop), `sh101ref.py`, `ref_test.py`; `fit.py` and `fit_circuit/` (the fitted values); `tal/` (TAL-BassLine-101's measurements); `device/compare.py` (the module against the reference); `refit/` (the module simulated against TAL, and the refits tried) |
| `capture/` | The Ableton kit: `make_capture_set.py` (the 41 takes as one Arrangement track, `--fm1` adds the FM-1), `split_takes.py`, `analyse.py`, `compare_ab.py`, `run_ab.ps1`; `CAPTURE.md`, `FM1.md`; `results/` (the last A/B) |

## Checks

```sh
cd model && python3 ref_test.py            # the reference against the analog 4-pole, its solver and oversampling
python3 device/compare.py                  # the module against the reference: response, pitch, level, onset, aliasing
cd ../capture && python3 tests/synth_takes.py   # the capture analysis on synthetic takes
```

All pass (2026-11-17):
- response within 0.25 dB;
- singing pitch within 4.2 cents up to 4 kHz;
- level within 0.04 dB;
- the same onset;
- aliasing −62 dB at 1×.

**On the FM-1 against TAL** (`capture/results/ab_report.md`):
- corner 124/124 Hz;
- slope −20.6/−20.6 dB/oct;
- self-oscillation within ±60 cents from 20 Hz to 3.6 kHz;
- THD 0.60% (TAL ~0.9%);
- singing level 1 dB under TAL's.

**Open:** TAL's slow climb into self-oscillation between RES 7.25 and 8. The circuit as drawn doesn't do it; see `docs/HISTORY.md`. A real SH-101 through the same kit would settle it.
