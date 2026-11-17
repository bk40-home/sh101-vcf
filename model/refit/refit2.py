#!/usr/bin/env python3
"""Refit, second pass: the onset is no longer pinned at TAL's first non-silent step (7.12). TAL's slow climb from
7.25 to 8 is taken as what it looks like: a filter just short of oscillation ringing on its noise. Free: the loop gain
curve (kmax, power), the circuit noise, the diodes (level, knee) and the drive. Held: the small-signal loop gain at
RES 2.5 and 5 (T3's clean peaks, fitted before), as k x D0 (D0: the diodes' small-signal gain)."""
import json, sys
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from sim import setp, getp, t0, t1, t2, t4, L
from refit import BASE, T2, T1, T4

A = json.load(open(Path(__file__).resolve().parents[1] / "fit_circuit" / "params.json"))["A"]["k_at"]
setp(**BASE); D0B = L.small_gain()
KEFF = {2.5: A["2.5"] * D0B, 5.0: A["5.0"] * D0B}     # the small-signal loop gains that matched TAL's T3


def params(x):
    clip, sharp, drive, kmax, curve, lnoise = x
    setp(**dict(BASE, clip=clip, sharp=sharp, drive=drive, kmax=kmax, curve=curve, noise=10 ** lnoise))
    return getp()


def resid(x, verbose=False):
    p = params(x); d0 = L.small_gain()
    r = [8 * np.log(p["kmax"] * (res / 10) ** p["curve"] * d0 / v) * 10 for res, v in KEFF.items()]   # held
    t0()
    for res, v in T2.items():
        r.append(t2(res) - v)
    r.append(max(0.0, t2(7.0) + 50) / 3)          # TAL: -76.8 at 7.0
    f, lv, thd = t1()
    r += [lv - T1["level"], 2 * np.log2(thd / T1["thd"]), 1200 * np.log2(f / T1["hz"]) / 20]
    for lvl, v in T4.items():
        r.append(2 * (t4(lvl, 7.0) - v))
    if verbose:
        print(" ".join(f"{v:+.2f}" for v in r))
    return r


if __name__ == "__main__":
    lo = [0.05, 0.3, 0.05, 3.5, 0.6, -6.0]; hi = [2.0, 20.0, 0.6, 8.0, 1.6, -2.0]
    best = None
    for st in ([0.51, 8.8, 0.20, 4.73, 0.97, -4.0], [0.4, 5.0, 0.2, 4.9, 1.0, -3.0], [0.3, 3.0, 0.25, 5.2, 1.1, -3.5]):
        s = least_squares(resid, st, bounds=(lo, hi), diff_step=0.02, max_nfev=80)
        print("start", st, "->", [round(float(v), 4) for v in s.x], "cost", round(2 * s.cost, 2), flush=True)
        if best is None or s.cost < best.cost:
            best = s
    p = params(best.x); print("best", {k: round(v, 5) for k, v in p.items()}, "D0", round(L.small_gain(), 5))
    resid(best.x, True)
    json.dump({"params": p, "x": [float(v) for v in best.x], "cost": 2 * best.cost}, open("refit2.json", "w"), indent=1)
