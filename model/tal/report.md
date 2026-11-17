# SH-101 filter capture: measurements

Takes found: 41 of 41.

## T1 cutoff taper (resonance 10)

| Slider | Singing pitch (Hz) | Level (dB re open saw) | THD (%) |
|---:|---:|---:|---:|
| 0 | 18.1 | 0.5 | 1.50 |
| 1 | 17.1 | 4.8 | 2.32 |
| 2 | 20.2 | 6.3 | 0.99 |
| 3 | 47.9 | 6.6 | 0.98 |
| 4 | 113.4 | 6.8 | 0.81 |
| 5 | 268.4 | 6.6 | 0.95 |
| 6 | 635.7 | 6.6 | 0.94 |
| 7 | 1507.1 | 6.6 | 0.93 |
| 8 | 3583.0 | 6.4 | 0.91 |
| 9 | 8562.5 | 6.1 | 0.74 |
| 10 | 11552.5 | 4.9 | 0.00 |

Log-linear fit over the 11 takes below 15 kHz: 1.067 octaves per slider unit, 7.8 Hz at 0, worst deviation 1448 cents.

## T2 onset of self-oscillation (cutoff 5)

| Res | Level (dB re open saw) | Pitch (Hz) |
|---:|---:|---:|
| 7 | -76.8 | nan |
| 7.25 | -26.5 | 3355.6 |
| 7.5 | -14.0 | 12566.6 |
| 7.75 | -4.7 | 267.9 |
| 8 | 0.0 | 268.0 |
| 8.25 | 2.3 | 268.1 |
| 8.5 | 3.6 | 268.2 |
| 8.75 | 4.5 | 268.2 |
| 9 | 5.2 | 268.3 |
| 9.25 | 5.7 | 268.3 |
| 9.5 | 6.1 | 268.3 |
| 9.75 | 6.4 | 268.4 |
| 10 | 6.7 | 268.4 |

Onset: resonance **7.31**.

## T3 response against resonance (cutoff 5, noise)

| Res | Passband (dB) | Bass loss (dB) | Peak (Hz) | Peak over passband (dB) |
|---:|---:|---:|---:|---:|
| 0 | -0.7 | 0.0 | nan | nan |
| 2.5 | -4.3 | -3.6 | 191 | 4.0 |
| 5 | -6.7 | -6.0 | 229 | 11.2 |
| 7.5 | -7.9 | -7.2 | 264 | 27.0 |
| 9 | -6.1 | -5.4 | 269 | 36.3 |
| 10 | -5.6 | -4.9 | 269 | 37.9 |

Resonance 0: -3 dB corner 124 Hz, slope -20.6 dB/octave above it.
Singing pitch at the same cutoff (T1, slider 5): 268 Hz, **2.164 x the corner** (an ideal 4-pole ladder: 2.30).

## T4 drive (saw C2, cutoff 5)

| Res | Saw level | Output (dBFS rms) | Resonance's share (dB re res 0) |
|---:|---:|---:|---:|
| 0 | 2 | -37.7 | nan |
| 0 | 5 | -29.8 | nan |
| 0 | 8 | -25.7 | nan |
| 0 | 10 | -23.8 | nan |
| 7 | 2 | -38.6 | -0.9 |
| 7 | 5 | -30.9 | -1.1 |
| 7 | 8 | -27.1 | -1.4 |
| 7 | 10 | -25.4 | -1.6 |

The harmonic levels per take are in calib.json.

## T5 keyboard tracking (kybd 10, resonance 10)

0.857 octaves per octave, worst deviation 572.4 cents.

| Note | Hz | Cents from fit |
|---:|---:|---:|
| 24 | 24.0 | +572.4 |
| 36 | 23.9 | -457.9 |
| 48 | 47.9 | -286.2 |
| 60 | 95.8 | -114.4 |
| 72 | 191.7 | +57.1 |
| 84 | 383.5 | +229.0 |
