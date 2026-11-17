#!/usr/bin/env python3
"""Self-test of analyse.py: synthetic takes with KNOWN answers, written as Ableton would export them
(24-bit stereo, "<n>-<track>.wav", a little latency), then analysed and checked.

    python3 tests/synth_takes.py        (exit 0 = analyse.py recovers every truth within tolerance)
"""
import shutil
import sys
import tempfile
import wave
from math import comb
from pathlib import Path

import numpy as np
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyse                                                   # noqa: E402
from takes import BEAT, CLIPS, TAKES                             # noqa: E402

FS = 44100
LAT = 0.023                                                      # plug-in latency the analysis must find
rng = np.random.default_rng(1)


def sing_hz(slider):                                             # truth: cutoff taper
    return min(25.0 * 2 ** (1.05 * slider), 18000.0)


def k_of(res):                                                   # truth: ladder k against the resonance slider
    return 4 * res / 10 * 0.97


ONSET = 9.2                                                      # truth: T2 onset
TRACK = 0.98                                                     # truth: octaves per octave


def ladder(x, w_hz, k):
    """Linear ideal ladder 1/((1+s/w)^4 + k), bilinear with prewarp at w."""
    wa = 2 * FS * np.tan(np.pi * w_hz / FS)
    a = [comb(4, i) / wa ** i for i in range(4, -1, -1)]
    a[-1] += k
    b, a = signal.bilinear([1.0], a, FS)
    return signal.lfilter(b, a, x)


def saw(f, n, amp):
    t = np.arange(n) / FS
    y = np.zeros(n)
    for h in range(1, int(0.45 * FS / f) + 1):
        y += np.sin(2 * np.pi * h * f * t) / h
    return amp * 2 / np.pi * y


def gate(clip, body):
    """Silence, then body under the clip's first note (+ latency), then silence to the clip's end."""
    n = int(CLIPS[clip]["beats"] * BEAT * FS)
    out = np.zeros(n)
    note, start, length = CLIPS[clip]["notes"][0]
    a = int((start * BEAT + LAT) * FS)
    m = min(int(length * BEAT * FS), n - a)
    out[a:a + m] = body[:m]
    return out


def take(t):
    clip, s, n = t["clip"], t["settings"], int(22 * FS)
    tt = np.arange(n) / FS
    if t["test"] == "T0":
        return gate(clip, saw(440 * 2 ** ((48 - 69) / 12), n, 0.5))
    if t["test"] == "T1":
        f = sing_hz(s["Cutoff"])
        return gate(clip, 0.25 * np.sin(2 * np.pi * f * tt) + 0.0025 * np.sin(4 * np.pi * f * tt))
    if t["test"] == "T2":
        r = s["Res"]
        a = 0.25 * np.sqrt((r - ONSET) / (10 - ONSET)) if r > ONSET else 0.0   # Hopf: power grows linearly
        return gate(clip, a * np.sin(2 * np.pi * sing_hz(5) * tt) + 1e-6 * rng.standard_normal(n))
    if t["test"] == "T3":
        x = 0.12 * rng.standard_normal(n)
        return gate(clip, x if t["id"] == "T3_open" else ladder(x, sing_hz(5), k_of(s["Res"])))
    if t["test"] == "T4":
        x = np.tanh(2 * saw(440 * 2 ** ((36 - 69) / 12), n, 0.5 * s["Saw"] / 10)) / 2
        return gate(clip, ladder(x, sing_hz(5), k_of(s["Res"])))
    if t["test"] == "T5":
        out = np.zeros(int(CLIPS[clip]["beats"] * BEAT * FS))
        for note, start, length in CLIPS[clip]["notes"]:
            f = sing_hz(3) * 2 ** ((note - 48) / 12 * TRACK)
            a = int((start * BEAT + LAT) * FS)
            m = int(length * BEAT * FS)
            out[a:a + m] = 0.25 * np.sin(2 * np.pi * f * np.arange(m) / FS)
        return out
    raise ValueError(t)


def write24(path, x):
    v = np.clip(np.round(x * (1 << 23)), -(1 << 23), (1 << 23) - 1).astype(np.int32)
    st = np.repeat(v, 2)                                          # stereo
    b = np.stack([(st & 255), (st >> 8) & 255, (st >> 16) & 255], axis=1).astype(np.uint8).tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(3); w.setframerate(FS); w.writeframes(b)


def main():
    tmp = Path(tempfile.mkdtemp())
    for i, t in enumerate(TAKES, 1):
        write24(tmp / f"{i}-{t['id']}.wav", take(t))
    res = analyse.main(tmp, tmp / "analysis")
    fails = []

    def check(ok, what):
        print(f"  [{'pass' if ok else 'FAIL'}] {what}")
        ok or fails.append(what)

    print("self-test against the synthetic truth:")
    worst = max(abs(1200 * np.log2(r["hz"] / sing_hz(r["slider"]))) for r in res["T1"]["rows"])
    check(len(res["T1"]["rows"]) == 11 and worst < 1, f"T1 singing pitch per slider within 1 cent (worst {worst:.3f})")
    thd = res["T1"]["rows"][5]["thd_pct"]
    check(abs(thd - 1.0) < 0.05, f"T1 THD 1% (got {thd:.3f}%)")
    on = res["T2"]["onset_res"]
    check(on is not None and abs(on - ONSET) < 0.05, f"T2 onset {ONSET} within 0.05 (got {on})")
    t3 = res["T3"]["takes"]
    r0 = t3[0]
    corner = sing_hz(5) * np.sqrt(2 ** 0.25 - 1)                  # -3 dB of four coincident poles
    check(abs(r0["corner_hz"] / corner - 1) < 0.04, f"T3 corner {corner:.0f} Hz within 4% (got {r0['corner_hz']:.0f})")
    fa, fb = r0["slope_between_hz"]                               # the ideal ladder's own slope over the same octave
    ex_slope = -40 * (np.log10(1 + (fb / sing_hz(5)) ** 2) - np.log10(1 + (fa / sing_hz(5)) ** 2))
    check(abs(r0["slope_db_per_oct"] - ex_slope) < 0.5, f"T3 slope {ex_slope:.1f} dB/oct within 0.5 (got {r0['slope_db_per_oct']:.1f})")
    bl = max(abs(r["bass_loss_db"] + 20 * np.log10(1 + k_of(r["res"]))) for r in t3[1:])
    check(bl < 0.5, f"T3 bass loss = -20log(1+k) within 0.5 dB (worst {bl:.3f})")
    pk = [r for r in t3 if r["res"] == 10][0]
    check(abs(pk["peak_hz"] / sing_hz(5) - 1) < 0.04, f"T3 peak at the singing pitch within 4% (got {pk['peak_hz']:.0f} vs {sing_hz(5):.0f})")
    ex = 20 * np.log10(1 / (4 - k_of(10)) * (1 + k_of(10)))        # |H(w)| / |H(0)| for the ideal ladder
    check(abs(pk["peak_over_passband_db"] - ex) < 1.5, f"T3 peak over passband {ex:.1f} dB within 1.5 (got {pk['peak_over_passband_db']:.1f})")
    check(len(res["T4"]["rows"]) == 8, "T4 all eight takes measured")
    tr = res["T5"]["fit"]
    check(tr and abs(tr["octaves_per_octave"] - TRACK) < 0.002, f"T5 tracking {TRACK} (got {tr and tr['octaves_per_octave']:.4f})")
    check(not [w for w in res["warnings"] if "missing" in w or "clipped" in w], "no missing or clipped takes reported")
    out = Path(__file__).resolve().parents[1] / "tests" / "synthetic_report"
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(tmp / "analysis", out)
    shutil.rmtree(tmp)
    print("all passed" if not fails else f"FAILED: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
