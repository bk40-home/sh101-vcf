# SH-101 model fitted to the capture

## Fitted parameters

| Parameter | Schematic | Fitted | Change |
|:---|---:|---:|---:|
| `drive` | 0.3 | 0.1992 | -34% |
| `clip` | 0.346 | 0.5145 | +49% |
| `clip_sharp` | 10.77 | 8.798 | -18% |
| `fwd` | 0.202 | 0.202 | +0% |
| `kmax` | 4.951 | 5.866 | +18% |
| `res_curve` | 1 | 1.149 | +15% |
| `cut_hz0` | 10 | 3.682 | -63% |
| `cut_oct` | 1.097 | 1.246 | +14% |

`render_takes.py` arguments: `--set drive=0.199182 --set clip=0.514473 --set clip_sharp=8.79775 --set fwd=0.202 --set kmax=5.86571 --set res_curve=1.14896 --set cut_hz0=3.68185 --set cut_oct=1.24641`

## A. Resonance and output compensation (linear, from T3 at RES 2.5 and 5, and the T2 onset)

| RES | k fitted | k from the fitted curve |
|---:|---:|---:|
| 2.5 | 1.231 | 1.193 |
| 5 | 2.412 | 2.645 |
| 7.125 | 4.001 | 3.974 |

Onset bracket from T2: (7.0, 7.25); the linear loop sings at k = 4.001 (the two stage-1 pole offset included).
Residuals of the linear fit (bass loss dB, peak dB, peak position x3 semitones): -1.28, -0.63, -2.46, -1.12, -0.72, +0.98
Corner at RES 0: TAL 124 Hz, linear model 117 Hz.

## B. Drive and diode level (self-oscillation at cutoff 5)

| RES | TAL level (dB re open saw) | Model |
|---:|---:|---:|
| 7 | -76.8 | -75.1 |
| 7.25 | -26.5 | -4.6 |
| 7.5 | -14.0 | 0.1 |
| 7.75 | -4.7 | 1.4 |
| 8 | 0.0 | 2.2 |
| 8.25 | 2.3 | 2.8 |
| 8.5 | 3.6 | 3.4 |
| 8.75 | 4.5 | 3.8 |
| 9 | 5.2 | 4.2 |
| 9.25 | 5.7 | 4.6 |
| 9.5 | 6.1 | 4.9 |
| 9.75 | 6.4 | 5.2 |
| 10 | 6.7 | 5.5 |

RES 10: THD TAL 0.95% / model 0.60%; pitch TAL 268.4 Hz / model 262.4 Hz.

## C. Cutoff taper (T1)

1.2464 octaves per slider unit over sliders 3-9 (worst 10 cents from a straight line). TAL stops singing lower than about 17 Hz (sliders 0-2, and C1/C2 in T5) and tops out at 11553 Hz (slider 10): rendered as limits, not part of the model.

## V. All 41 takes: TAL against the fitted model (same analyse.py)

| Measurement | TAL | Fitted model |
|:---|---:|---:|
| T3 corner at RES 0 (Hz) | 124 | 114 |
| T3 slope at RES 0 (dB/oct) | -20.6 | -20.2 |
| T3 RES 2.5: bass loss / peak (dB) | -3.6 / 4.0 | -5.2 / 3.9 |
| T3 RES 5: bass loss / peak (dB) | -6.0 / 11.2 | -7.9 / 13.1 |
| T3 RES 7.5: bass loss / peak (dB) | -7.2 / 27.0 | -7.5 / 45.8 |
| T3 RES 9: bass loss / peak (dB) | -5.4 / 36.3 | -5.6 / 48.3 |
| T3 RES 10: bass loss / peak (dB) | -4.9 / 37.9 | -4.1 / 47.4 |
| T2 onset bracket (silent, singing) | (7.0, 7.25) | (7.0, 7.25) |
| T2 level at RES 8 (dB) | 0.0 | 2.3 |
| T2 level at RES 9 (dB) | 5.2 | 4.3 |
| T2 level at RES 10 (dB) | 6.7 | 5.6 |
| T1 slider 3: Hz / THD % | 47.9 / 0.98 | 47.7 / 0.60 |
| T1 slider 5: Hz / THD % | 268.4 / 0.95 | 268.7 / 0.60 |
| T1 slider 7: Hz / THD % | 1507.1 / 0.93 | 1512.7 / 0.60 |
| T1 slider 9: Hz / THD % | 8562.5 / 0.74 | 8515.9 / 0.00 |
| T4 RES 7, saw 2: resonance's share (dB) | -0.89 | 1.40 |
| T4 RES 7, saw 10: resonance's share (dB) | -1.62 | 3.53 |
| T5 tracking, C3-C6 (oct/oct) | 1.001 | 1.000 |

## Notes and open items

- **fwd is held at the schematic value (0.202).** R130's top is connector pin 75, which is VR18's hot end (the filter output); the wiper leaves on pin 76. R132's lower end is TR26's emitter, an in-phase copy of the wiper. So out ∝ y4·(1 + r), and with k = 4.951·r that gives fwd = 0.202. TAL implies 0.32 (`fit.py --fit-fwd`). That's TAL's choice, not the circuit's, and accounts for the 1.6–1.9 dB of extra bass loss at RES 2.5 and 5.
- **The onset is too abrupt.** Both start singing between RES 7.0 and 7.25. TAL then takes until RES 8 to reach full level; the model takes about 0.25 of a step. Above RES 8 the levels agree within 1.2 dB, but the model's RES 7.5 noise peak is 46 dB against TAL's 27, and T4 at RES 7 rises instead of falling. With a plain diode limiter, level rises as √(k − k_crit), which is steep. TAL's slower rise could be its slider mapping near the top of the pot, or a softer limiter at small amplitude. A real unit would settle which.
- **THD is 0.6% against TAL's 0.95%.** At slider 9 the harmonics are above Nyquist, so the model reads 0.
- **Cutoff limits:** TAL stops singing below about 17 Hz and above 11.6 kHz. These are rendered as limits (`--cut-min/--cut-max`) and are not part of the filter.
