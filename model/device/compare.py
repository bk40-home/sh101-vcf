#!/usr/bin/env python3
"""Host test: the FM-1 module obv_sh101.h (float, 1x, semi-implicit) against the reference (double, 8x, Newton).

    python3 device/compare.py [--module /path/to/sh101_vcf.h]   -> pass/fail per check, device/compare.md

Both run the fitted parameters (fit_circuit/params.json). The device module's cut is where the filter sings
(S1Vave's Q8 semitones); the reference takes the pole frequency, so it gets that through the same 0.99298 ratio.
"""
import argparse
import ctypes
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from sh101ref import Model, params  # noqa: E402

FS = 44100.0
FIT = json.loads((HERE.parent / "fit_circuit" / "params.json").read_text())["fitted"]


def build(module):
    so = HERE / "libsh101dev.so"
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-ffp-contract=off", "-Wall", "-Wno-unused-function",
                    f"-I{Path(module).resolve().parent}", "-o", str(so), str(HERE / "sh101dev_lib.c")], check=True)
    L = ctypes.CDLL(str(so))
    D = ctypes.POINTER(ctypes.c_double)
    L.dev_run.argtypes = [D, D, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_int]
    L.dev_k.restype = ctypes.c_float
    return L


def dev(L, x, cut_q8, res_q8, seed=1):
    x = np.ascontiguousarray(x, float)
    y = np.zeros_like(x)
    D = ctypes.POINTER(ctypes.c_double)
    L.dev_run(x.ctypes.data_as(D), y.ctypes.data_as(D), len(x), int(cut_q8), int(res_q8), seed, 16)
    return y


def ref(L, x, cut_q8, res_q8):
    fc = 440 * 2 ** (((cut_q8 + 31) / 256 - 69) / 12)
    p = params(drive=FIT["drive"], clip=FIT["clip"], clip_sharp=FIT["clip_sharp"], fwd=FIT["fwd"],
               kmax=FIT["kmax"], res_curve=FIT["res_curve"], os=8, noise_floor=1e-4)
    m = Model(p, FS)
    y = m.run(np.asarray(x, float), fc, float(L.dev_k(int(res_q8))))
    lat = m.latency
    return np.concatenate([y[lat:], np.zeros(lat)])


def transfer(x, y, f):
    nf = 8192
    win = np.hanning(nf)
    X = Y = 0
    Sxy = Sxx = 0
    for i in range(0, len(x) - nf, nf // 2):
        X = np.fft.rfft(x[i:i + nf] * win); Y = np.fft.rfft(y[i:i + nf] * win)
        Sxy = Sxy + Y * np.conj(X); Sxx = Sxx + np.abs(X) ** 2
    H = np.abs(Sxy) / Sxx
    fr = np.fft.rfftfreq(nf, 1 / FS)
    return np.interp(f, fr, 20 * np.log10(H + 1e-12))


def sing(y):
    y = y[-int(FS * 0.6):]
    rms = np.sqrt(np.mean(y ** 2))
    sp = np.abs(np.fft.rfft(y * np.hanning(len(y)), 1 << 19))
    fr = np.fft.rfftfreq(1 << 19, 1 / FS)
    i = np.argmax(sp)
    h = [sp[np.argmin(abs(fr - n * fr[i]))] for n in range(1, 6) if n * fr[i] < FS / 2]
    thd = 100 * np.sqrt(np.sum(np.square(h[1:]))) / h[0] if len(h) > 1 else 0.0
    return fr[i], 20 * np.log10(max(rms, 1e-12) * np.sqrt(3)), thd       # level dB re a full saw's rms


def saw(f, n, amp=1.0):
    t = np.arange(n) / FS
    ph = (f * t) % 1.0
    return amp * (2 * ph - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", default=str(HERE.parents[1] / "sh101_vcf.h"), help="the module to test")
    a = ap.parse_args()
    L = build(a.module)
    rng = np.random.default_rng(3)
    rows, ok_all = [], True

    def check(name, val, lim, txt):
        nonlocal ok_all
        ok = val <= lim
        ok_all &= ok
        rows.append((name, txt, "pass" if ok else "FAIL"))
        print(f"{'pass' if ok else 'FAIL'}  {name}: {txt}")

    # 1. small-signal response, 20 Hz .. 12 kHz, at three resonances below onset
    f = np.geomspace(20, 12000, 60)
    x = rng.standard_normal(int(FS * 4)) * 0.05
    for cut in (48, 72, 96):
        for res in (0, 64, 88):
            hd, hr = transfer(x, dev(L, x, cut << 8, res << 8), f), transfer(x, ref(L, x, cut << 8, res << 8), f)
            band = (hr > hr.max() - 20) & (f < 8000)       # passband and resonance, below 8 kHz
            err = np.max(np.abs(hd - hr)[band])
            sb = (hr <= hr.max() - 20) & (hr > hr.max() - 60)
            check(f"response cut {cut} res {res}", err, 0.5,
                  f"worst {err:.2f} dB within 20 dB of the peak; stopband to -60 dB: {np.min((hd - hr)[sb]) if sb.any() else 0:+.1f} dB (1x rolls off harder near Nyquist)")

    # 2. self-oscillation from silence: pitch, level, THD
    for cut in (36, 60, 84, 108):
        z = np.zeros(int(FS * 2.5))
        fd, ld, td = sing(dev(L, z, cut << 8, 127 << 8)); fr_, lr, tr = sing(ref(L, z, cut << 8, 127 << 8))
        cents = 1200 * np.log2(fd / fr_)
        check(f"singing cut {cut}", abs(cents), 6 if cut < 100 else 10,
              f"{fd:.1f} Hz vs {fr_:.1f} Hz ({cents:+.1f} c), level {ld:+.2f} vs {lr:+.2f} dB, THD {td:.2f} vs {tr:.2f} %")
        check(f"singing level cut {cut}", abs(ld - lr), 0.5, f"{ld - lr:+.2f} dB")

    # 3. onset: the lowest res (1/4 steps of the 0..127 slider) that sings within 2.5 s
    def onset(fn):
        for r4 in range(4 * 85, 4 * 105):
            y = fn(np.zeros(int(FS * 2.5)), 60 << 8, r4 * 64)
            if np.sqrt(np.mean(y[-int(FS * 0.5):] ** 2)) > 0.05:
                return r4 / 4
        return None
    od, orf = onset(lambda x, c, r: dev(L, x, c, r)), onset(lambda x, c, r: ref(L, x, c, r))
    check("onset", abs(od - orf), 0.5, f"device {od} vs reference {orf} (slider 0..127)")

    # 4. a full saw at C2 through res 0 and res 88 (just below onset): the level resonance costs
    n = int(FS * 2)
    for res in (0, 88):
        x = saw(65.41, n)
        ld = 20 * np.log10(np.sqrt(np.mean(dev(L, x, 60 << 8, res << 8)[n // 2:] ** 2)))
        lr = 20 * np.log10(np.sqrt(np.mean(ref(L, x, 60 << 8, res << 8)[n // 2:] ** 2)))
        check(f"saw C2 level res {res}", abs(ld - lr), 0.5, f"{ld:+.2f} vs {lr:+.2f} dB")

    # 5. extremes: everything at full scale, cutoff and resonance at the top; then silence afterwards
    x = np.clip(saw(55.0, n, 1.0) + saw(110.3, n, 1.0) + np.sign(saw(82.4, n)) + rng.standard_normal(n), -1, 1)
    y = dev(L, np.concatenate([x, np.zeros(n)]), 136 << 8, 127 << 8)
    bad = not np.all(np.isfinite(y))
    check("extremes finite and bounded", float(bad) + (np.max(np.abs(y)) > 8), 0, f"peak {np.max(np.abs(y)):.2f} (osc units)")
    y = dev(L, np.zeros(int(FS * 4)), 0, 0)
    tiny = np.abs(y[y != 0])
    check("silence: no denormals", float(np.any(tiny < 1e-30)), 0,
          f"output rms {20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-20):.0f} dB, smallest nonzero {tiny.min() if len(tiny) else 0:.1e}")

    # 6. aliasing at 1x: a loud saw at A6 through an open filter, energy that is not a harmonic
    t = np.arange(int(FS * 1.0)) / FS
    x = sum(np.sin(2 * np.pi * 1760.0 * h * t) / h for h in range(1, 13)) * (2 / np.pi)     # band-limited saw
    for name, fn in (("device 1x", lambda: dev(L, x, 136 << 8, 0)), ("reference 8x", lambda: ref(L, x, 136 << 8, 0))):
        y = fn()[int(FS * 0.3):]
        sp = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
        fr = np.fft.rfftfreq(len(y), 1 / FS)
        harm = np.zeros_like(sp, bool)
        for h in range(1, 13):
            harm |= np.abs(fr - 1760.0 * h) < 6
        rows.append((f"aliasing {name}", f"non-harmonic energy {10 * np.log10(sp[~harm].sum() / sp[harm].sum()):.0f} dB re the harmonics", "info"))
        print("info ", rows[-1][0], rows[-1][1])

    md = ["# obv_sh101.h against the reference model", "", "| Check | Result | |", "|:---|:---|:---|"]
    md += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    (HERE / "compare.md").write_text("\n".join(md) + "\n")
    print("ALL PASS" if ok_all else "SOME FAILED")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
