#!/usr/bin/env python3
"""Render the capture kit's 41 takes through the SH-101 reference model, as WAVs analyse.py reads exactly as it
reads the TAL bounces. Model and TAL then come out of the same measurement code, number for number.

    python3 render_takes.py <outdir> [--kit ../capture] [--set name=value ...]

    e.g. python3 render_takes.py build/model --set kmax=4.6 --set fwd=0.4
         python3 ../capture/analyse.py build/model build/model/analysis

Sources (an assumption until the TAL captures say otherwise, MODEL.md): the mixer is linear in its slider
(level/10), a saw at 10 is a full-scale band-limited saw (+-1), noise at 10 is white noise of rms 0.5.
VCA in GATE: the output is the filter's output while the note is held.
"""
import argparse
import sys
import wave
from pathlib import Path

import numpy as np

from sh101ref import Model, as_dict, params

FS = 44100
OUT_GAIN = 0.25                      # model output (oscillator units) -> WAV full scale


def saw(f, n):
    t = np.arange(n) / FS
    y = np.zeros(n)
    for h in range(1, int(0.45 * FS / f) + 1):
        y += np.sin(2 * np.pi * h * f * t) / h
    return 2 / np.pi * y


def write24(path, x):
    v = np.clip(np.round(x * (1 << 23)), -(1 << 23), (1 << 23) - 1).astype(np.int32)
    b = np.stack([v & 255, (v >> 8) & 255, (v >> 16) & 255], axis=1).astype(np.uint8).tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(3); w.setframerate(FS); w.writeframes(b)


CUT_MIN, CUT_MAX = 0.0, 1e9          # optional panel limits (--cut-min/--cut-max): where a reference stops tracking


def cut_hz(p, slider, kybd, note):
    f = p.cut_hz0 * 2 ** (p.cut_oct * slider + p.kybd_oct * (kybd / 10) * (note - 48) / 12)
    return min(max(f, CUT_MIN), CUT_MAX)


def k_of(p, res):
    return p.kmax * (res / 10) ** p.res_curve


def render(t, p, clips, beat, rng):
    s = t["settings"]
    n = int(clips[t["clip"]]["beats"] * beat * FS)
    m = Model(p, FS)
    lat = m.latency
    out = np.zeros(n)
    gate = np.zeros(n)
    notes = clips[t["clip"]]["notes"]
    edges = [0] + [int(st * beat * FS) for _, st, _ in notes] + [n]
    for i, (a, b) in enumerate(zip(edges, edges[1:])):          # one segment per note (and the lead-in)
        note = notes[max(i - 1, 0)][0]
        fc = cut_hz(p, s.get("Cutoff", 0), s.get("Kybd", 0), note)
        x = np.zeros(b - a + (lat if b == n else 0))
        if i >= 1:
            nn = notes[i - 1]
            L = min(int(nn[2] * beat * FS), len(x))
            src = np.zeros(L)
            if s.get("Saw"):
                src += s["Saw"] / 10 * saw(440 * 2 ** ((nn[0] - 69) / 12), L)
            if s.get("Noise"):
                src += s["Noise"] / 10 * 0.5 * rng.standard_normal(L)
            x[:L] = src
            gate[a:a + L] = 1
        y = m.run(x, fc, k_of(p, s.get("Res", 0)))
        out[a:a + len(y)] = y[:n - a] if a + len(y) > n else y
    out = np.concatenate([out[lat:], np.zeros(lat)])                 # undo the resampler's delay
    return out * gate * OUT_GAIN, m.stats()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--kit", default=str(Path(__file__).resolve().parent.parent / "capture"))
    ap.add_argument("--set", action="append", default=[], help="name=value (cap=a,b,c,d)")
    ap.add_argument("--cut-min", type=float, default=0.0, help="lowest cutoff (Hz) the panel reaches")
    ap.add_argument("--cut-max", type=float, default=1e9, help="highest cutoff (Hz)")
    a = ap.parse_args()
    global CUT_MIN, CUT_MAX
    CUT_MIN, CUT_MAX = a.cut_min, a.cut_max
    sys.path.insert(0, a.kit)
    from takes import BEAT, CLIPS, TAKES
    over = {}
    for kv in a.set:
        k, v = kv.split("=", 1)
        over[k] = [float(x) for x in v.split(",")] if k == "cap" else (int(v) if k in ("os", "clip_place", "fwd_from", "max_iter") else float(v))
    p = params(**over)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    worst = 0
    for i, t in enumerate(TAKES, 1):
        y, st = render(t, p, CLIPS, BEAT, rng)
        worst = max(worst, st["worst_resid"])
        write24(out / f"{i}-{t['id']}.wav", y)
    (out / "params.txt").write_text("\n".join(f"{k} = {v}" for k, v in as_dict(p).items()) + "\n")
    print(f"{len(TAKES)} takes -> {out} (worst solver residual {worst:.1e})")


if __name__ == "__main__":
    main()
