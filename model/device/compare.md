# obv_sh101.h against the reference model

| Check | Result | |
|:---|:---|:---|
| response cut 48 res 0 | worst 0.04 dB within 20 dB of the peak; stopband to -60 dB: -0.1 dB (1x rolls off harder near Nyquist) | pass |
| response cut 48 res 64 | worst 0.04 dB within 20 dB of the peak; stopband to -60 dB: -0.1 dB (1x rolls off harder near Nyquist) | pass |
| response cut 48 res 88 | worst 0.03 dB within 20 dB of the peak; stopband to -60 dB: -0.1 dB (1x rolls off harder near Nyquist) | pass |
| response cut 72 res 0 | worst 0.03 dB within 20 dB of the peak; stopband to -60 dB: -0.5 dB (1x rolls off harder near Nyquist) | pass |
| response cut 72 res 64 | worst 0.03 dB within 20 dB of the peak; stopband to -60 dB: -0.3 dB (1x rolls off harder near Nyquist) | pass |
| response cut 72 res 88 | worst 0.02 dB within 20 dB of the peak; stopband to -60 dB: -0.1 dB (1x rolls off harder near Nyquist) | pass |
| response cut 96 res 0 | worst 0.17 dB within 20 dB of the peak; stopband to -60 dB: -7.5 dB (1x rolls off harder near Nyquist) | pass |
| response cut 96 res 64 | worst 0.24 dB within 20 dB of the peak; stopband to -60 dB: -7.4 dB (1x rolls off harder near Nyquist) | pass |
| response cut 96 res 88 | worst 0.17 dB within 20 dB of the peak; stopband to -60 dB: -3.3 dB (1x rolls off harder near Nyquist) | pass |
| singing cut 36 | 63.9 Hz vs 63.9 Hz (+0.0 c), level +5.53 vs +5.52 dB, THD 0.60 vs 0.60 % | pass |
| singing level cut 36 | +0.01 dB | pass |
| singing cut 60 | 255.8 Hz vs 255.9 Hz (-0.6 c), level +5.52 vs +5.51 dB, THD 0.60 vs 0.60 % | pass |
| singing level cut 60 | +0.02 dB | pass |
| singing cut 84 | 1022.3 Hz vs 1023.3 Hz (-1.7 c), level +5.52 vs +5.50 dB, THD 0.58 vs 0.60 % | pass |
| singing level cut 84 | +0.02 dB | pass |
| singing cut 108 | 4083.7 Hz vs 4093.5 Hz (-4.2 c), level +5.47 vs +5.50 dB, THD 0.25 vs 0.59 % | pass |
| singing level cut 108 | -0.04 dB | pass |
| onset | device 91.75 vs reference 91.75 (slider 0..127) | pass |
| saw C2 level res 0 | -7.36 vs -7.36 dB | pass |
| saw C2 level res 88 | -5.24 vs -5.23 dB | pass |
| extremes finite and bounded | peak 3.14 (osc units) | pass |
| silence: no denormals | output rms -113 dB, smallest nonzero 1.5e-05 | pass |
| aliasing device 1x | non-harmonic energy -62 dB re the harmonics | info |
| aliasing reference 8x | non-harmonic energy -67 dB re the harmonics | info |
