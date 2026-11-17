#!/usr/bin/env python3
"""Checks that the SH-101 reference model computes what it claims to (not yet that it matches a 101: that is the
TAL fit's job). Exit 0 = all passed.

    python3 ref_test.py
"""
import sys

import numpy as np

from sh101ref import Model, params

FS = 44100.0
fails = []


def check(ok, what):
    print(f"  [{'pass' if ok else 'FAIL'}] {what}")
    ok or fails.append(what)


def sine_gain(m, f, fc, k, amp, secs=1.0):
    """steady-state gain and phase-locked amplitude of a sine through the model"""
    n = int(FS * secs)
    t = np.arange(n) / FS
    y = m.run(amp * np.sin(2 * np.pi * f * t), fc, k)
    a = n // 2
    w = np.hanning(n - a)
    z = np.sum(y[a:] * w * np.exp(-2j * np.pi * f * t[a:])) * 2 / np.sum(w)
    return abs(z) / amp


def ladder_h(f, fc, k):
    s = 1j * f / fc
    return abs(1 / ((1 + s) ** 4 + k))


# ---- 1. small-signal response against the analog transfer function ---------------------------------
print("1. small signal (drive 1e-4, no clipping, no forward copy) against 1/((1+s/w)^4 + k)")
lin = dict(drive=1e-4, clip=1e3, fwd=0.0, noise_floor=0.0, cap=[1, 1, 1, 1])   # equal poles: the textbook case
worst = 0
for k in (0.0, 2.0, 3.5):
    for f in (50, 300, 1000, 2000, 5000, 15000):
        m = Model(params(**lin))
        g = sine_gain(m, f, 1000.0, k, 1.0)
        ex = 20 * np.log10(ladder_h(f, 1000.0, k))
        if ex > -60:                                       # below that the bilinear map's warp (0.6% at 15 kHz) shows
            worst = max(worst, abs(20 * np.log10(g) - ex))
print(f"     worst error above -60 dB: {worst:.4f} dB (k 0, 2, 3.5; 50 Hz .. 15 kHz)")
check(worst < 0.05, "matches the analog 4-pole within 0.05 dB wherever it is above -60 dB")

m = Model(params(drive=1e-4, clip=1e3, fwd=0.5, noise_floor=0.0, cap=[1, 1, 1, 1]))
dc = sine_gain(m, 20, 1000.0, 3.0, 1.0)
check(abs(dc / ((1 + 0.5 * 3) / (1 + 3)) - 1) < 0.002, f"forward copy: low-frequency gain (1 + f k)/(1 + k) = 0.625 (got {dc:.4f})")

# ---- 2. the solver converges everywhere ---------------------------------------------------------------
print("2. solver: full-scale square, drive 1.0 (hard saturation), k 4.4, cutoff jumping")
m = Model(params(drive=1.0))
n = int(FS * 0.5)
sq = np.where(np.sin(2 * np.pi * 110 * np.arange(n) / FS) >= 0, 1.0, -1.0)
for i, fc in enumerate((40, 200, 1000, 5000, 18000, 60)):
    m.run(sq[i * n // 6:(i + 1) * n // 6], fc, 4.4)
st = m.stats()
print(f"     mean {st['mean_iter']:.2f} iterations, worst {st['worst_iter']:.0f}, worst residual {st['worst_resid']:.1e}")
check(st["worst_resid"] < 1e-12 and st["worst_iter"] < 30, "every sample solved to < 1e-12")

# ---- 3. oversampling has converged ----------------------------------------------------------------------
print("3. oversampling: a driven saw (drive 0.6, k 3.2) at 4x, 8x, 16x")
n = int(FS * 1.0)
t = np.arange(n) / FS
saw = 2 * ((110 * t) % 1.0) - 1
outs = {}
for os_ in (4, 8, 16):
    m = Model(params(drive=0.6, os=os_, noise_floor=0.0))
    y = m.run(saw, 1500.0, 3.2)
    outs[os_] = y[m.latency:]
L = min(len(v) for v in outs.values())
d8 = 10 * np.log10(np.sum(outs[16][:L] ** 2) / np.sum((outs[16][:L] - outs[8][:L]) ** 2))
d4 = 10 * np.log10(np.sum(outs[16][:L] ** 2) / np.sum((outs[16][:L] - outs[4][:L]) ** 2))
print(f"     against 16x: 8x {d8:.1f} dB, 4x {d4:.1f} dB")
check(d8 > 60, "8x within 60 dB of 16x (the default is converged)")

# ---- 4. self-oscillation -----------------------------------------------------------------------------------
print("4. self-oscillation from the noise floor, cutoff 500 Hz (schematic diodes, equal poles)")
rows = []
for k in (3.9, 4.05, 4.2, 4.4):
    m = Model(params(noise_floor=1e-6, cap=[1, 1, 1, 1]))
    y = m.run(np.zeros(int(FS * 3)), 500.0, k)
    seg = y[-int(FS):]
    r = np.sqrt(np.mean(seg ** 2))
    f0 = None
    if r > 1e-3:
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 1 << 20))
        i = np.argmax(sp)
        a, b, c = np.log(sp[i - 1:i + 2])
        f0 = (i + 0.5 * (a - c) / (a - 2 * b + c)) * FS / (1 << 20)
    rows.append((k, r, f0))
    print(f"     k {k:.2f}: rms {r:.4f}" + (f", {f0:.2f} Hz" if f0 else ""))
check(rows[0][1] < 1e-3 and all(r[1] > 1e-3 for r in rows[1:]), "silent below k = 4, sings above it")
check(rows[-1][1] > rows[1][1], "louder the further past the onset")
# The oscillation drives stage 1 hard enough to flatten the pitch a little (a physical effect, sized by the
# diode level, which the T1 captures will fit). In the small-amplitude limit it must sing exactly at the cutoff:
m = Model(params(clip=0.005, cap=[1, 1, 1, 1]))
seg = m.run(np.zeros(int(FS * 4)), 500.0, 4.05)[-int(FS):]
sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 1 << 20))
i = np.argmax(sp)
a, b, c = np.log(sp[i - 1:i + 2])
f0 = (i + 0.5 * (a - c) / (a - 2 * b + c)) * FS / (1 << 20)
print(f"     small-amplitude limit (clip 0.005): {f0:.3f} Hz")
check(abs(1200 * np.log2(f0 / 500.0)) < 1, "in the small-amplitude limit it sings within 1 cent of the cutoff")

# ---- 5. where the diodes sit changes how the oscillation grows ---------------------------------------
print("5. clip before / after the pot: self-oscillation level against k")
for place, name in ((0, "before pot"), (1, "after pot")):
    lv = []
    for k in (4.1, 4.4, 5.0):
        m = Model(params(clip_place=place, cap=[1, 1, 1, 1]))
        y = m.run(np.zeros(int(FS * 2)), 500.0, k)
        lv.append(np.sqrt(np.mean(y[-int(FS):] ** 2)))
    print(f"     {name}: " + ", ".join(f"k {k}: {v:.3f}" for k, v in zip((4.1, 4.4, 5.0), lv)))

print("all passed" if not fails else f"FAILED: {len(fails)}")
sys.exit(1 if fails else 0)
