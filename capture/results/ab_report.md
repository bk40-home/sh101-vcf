# SH-101: TAL-BassLine-101 against the FM-1 (M-Vsynth2 FILTER TYPE 5)

Each capture's levels are re its own open saw (T0). The FM-1's RES is its real slider position (whole knob values, taper 2.0).

## T1: self-oscillation against FREQ (RES 10)

| FREQ | TAL Hz | FM-1 Hz | cents | TAL level | FM-1 level | TAL THD % | FM-1 THD % |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 7.2 | 16.6 | +1441 | +0.5 | +5.6 | 2.59 | 0.60 |
| 1 | 8.5 | 16.6 | +1151 | +4.8 | +5.6 | 1.11 | 0.60 |
| 2 | 20.2 | 19.1 | -99 | +6.3 | +5.6 | 0.99 | 0.60 |
| 3 | 47.9 | 46.3 | -58 | +6.6 | +5.6 | 0.98 | 0.60 |
| 4 | 113.4 | 112.1 | -19 | +6.8 | +5.6 | 0.81 | 0.60 |
| 5 | 268.4 | 271.5 | +20 | +6.6 | +5.6 | 0.95 | 0.60 |
| 6 | 635.7 | 613.9 | -60 | +6.6 | +5.6 | 0.94 | 0.59 |
| 7 | 1507.1 | 1485.3 | -25 | +6.6 | +5.6 | 0.93 | 0.54 |
| 8 | 3583.0 | 3592.8 | +5 | +6.4 | +5.4 | 0.91 | 0.27 |
| 9 | 8562.5 | 8129.0 | -90 | +6.1 | +4.6 | 0.74 | 0.00 |
| 10 | 11552.5 | 11025.0 | -81 | +4.9 | +5.5 | 0.00 | 0.00 |

## T2: where it starts to sing (FREQ 5)

TAL: silent at (7.0, 7.25); FM-1: (6.966333932667864, 7.231694463388928) (the last silent, the first singing RES)

| RES (TAL) | RES (FM-1, real) | TAL dB | FM-1 dB |
|---:|---:|---:|---:|
| 7.00 | 6.97 | -76.8 | -67.3 |
| 7.25 | 7.23 | -26.5 | -6.8 |
| 7.50 | 7.50 | -14.0 | +0.2 |
| 7.75 | 7.78 | -4.7 | +1.6 |
| 8.00 | 8.06 | +0.0 | +2.4 |
| 8.25 | 8.20 | +2.3 | +2.8 |
| 8.50 | 8.49 | +3.6 | +3.4 |
| 8.75 | 8.78 | +4.5 | +3.9 |
| 9.00 | 8.93 | +5.2 | +4.2 |
| 9.25 | 9.23 | +5.7 | +4.6 |
| 9.50 | 9.53 | +6.1 | +5.0 |
| 9.75 | 9.69 | +6.4 | +5.2 |
| 10.00 | 10.00 | +6.7 | +5.6 |

## T3: noise response at FREQ 5

| RES | TAL bass loss | FM-1 | TAL peak Hz | FM-1 | TAL peak dB | FM-1 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | - | - | - | - | - | - |
| 2.5 | -3.6 | -4.7 | 191 | 186 | +4.0 | +3.2 |
| 5 | -6.0 | -7.2 | 229 | 248 | +11.2 | +12.3 |
| 7.5 | -7.2 | -7.7 | 264 | 275 | +27.0 | +43.0 |
| 9 | -5.4 | -5.4 | 269 | 272 | +36.3 | +45.6 |
| 10 | -4.9 | -4.3 | 269 | 272 | +37.9 | +44.8 |

RES 0: corner TAL 124 Hz, FM-1 124 Hz; slope TAL -20.6, FM-1 -20.6 dB/oct

## T4: a saw at C2 through FREQ 5, RES 0 and 7 (the FM-1's level is MIX against a parked triangle)

| level | RES | TAL dB | FM-1 dB | TAL: RES costs | FM-1 |
|---:|---:|---:|---:|---:|---:|
| 2 | 0 | -37.7 | -38.0 | +0.00 | +0.00 |
| 5 | 0 | -29.8 | -30.0 | +0.00 | +0.00 |
| 8 | 0 | -25.7 | -25.8 | +0.00 | +0.00 |
| 10 | 0 | -23.8 | -23.9 | +0.00 | +0.00 |
| 2 | 7 | -38.6 | -37.6 | -0.89 | +0.45 |
| 5 | 7 | -30.9 | -29.5 | -1.10 | +0.45 |
| 8 | 7 | -27.1 | -24.9 | -1.41 | +0.89 |
| 10 | 7 | -25.4 | -22.0 | -1.62 | +1.88 |

## T5: keyboard tracking (FREQ 3, RES 10, KYBD full)

| note | TAL Hz | FM-1 Hz |
|---:|---:|---:|
| 24 | 12.0 | 16.6 |
| 36 | 23.9 | 22.1 |
| 48 | 47.9 | 46.3 |
| 60 | 95.8 | 96.7 |
| 72 | 191.7 | 201.7 |
| 84 | 383.5 | 421.1 |

Fit: TAL {'octaves_per_octave': 1.0004902131564142, 'max_dev_cents': 0.222809704361282, 'points': 6}; FM-1 {'octaves_per_octave': 0.970016628328298, 'max_dev_cents': 368.6546677888911, 'points': 6}

## FM-1 analysis warnings

- T1_cut00: sound starts 0.84 s after its note; read at the clip's own timing
- T1_cut01: sound starts 0.84 s after its note; read at the clip's own timing
- T1_cut02: sound starts 0.69 s after its note; read at the clip's own timing
- T1_cut03: sound starts 0.39 s after its note; read at the clip's own timing
- T2_res0725: sound starts 1.11 s after its note; read at the clip's own timing
- T2_res0750: sound starts 0.41 s after its note; read at the clip's own timing
- T2_res0775: sound starts 0.30 s after its note; read at the clip's own timing
- T2_res0800: sound starts 0.27 s after its note; read at the clip's own timing
- T2_res0825: sound starts 0.25 s after its note; read at the clip's own timing
- T2_res1000: sound starts 0.25 s after its note; read at the clip's own timing
- T3_res0750: sound starts 0.27 s after its note; read at the clip's own timing
- T3_res0900: sound starts 0.28 s after its note; read at the clip's own timing
- T3_res1000: sound starts 0.29 s after its note; read at the clip's own timing
- T5_track: sound starts 0.51 s after its note; read at the clip's own timing
