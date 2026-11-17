#!/usr/bin/env python3
"""Refit, third pass: the loop gain from the clean small-signal points alone (T3 at RES 2.5 and 5: k = 4.727 (RES/10)^0.971,
which agrees with the schematic's linear pot, 4.951 RES/10), fixed. Free: the diodes, the drive, the circuit noise."""
import json
import numpy as np
from scipy.optimize import least_squares
from sim import setp, getp, t0, t1, t2, t4, L
from refit import BASE, T2, T1, T4

KMAX, CURVE = 4.727, 0.971
setp(**BASE); D0B = L.small_gain()


def params(x):
    clip, sharp, drive, lnoise = x
    setp(**dict(BASE, clip=clip, sharp=sharp, drive=drive, curve=CURVE, noise=10 ** lnoise))
    setp(kmax=KMAX * D0B / L.small_gain())      # the same small-signal loop gain whatever the diodes
    return getp()


def resid(x, verbose=False):
    params(x); t0()
    r = [t2(res) - v for res, v in T2.items()]
    f, lv, thd = t1()
    r += [lv - T1["level"], 2 * np.log2(thd / T1["thd"]), 1200 * np.log2(f / T1["hz"]) / 20]
    r += [2 * (t4(lvl, 7.0) - v) for lvl, v in T4.items()]
    if verbose:
        print(" ".join(f"{v:+.2f}" for v in r))
    return r


if __name__ == "__main__":
    best = None
    for st in ([0.51, 8.8, 0.20, -4.0], [0.3, 4.0, 0.2, -3.0], [0.8, 10.0, 0.3, -2.5]):
        s = least_squares(resid, st, bounds=([0.05, 0.3, 0.03, -6.0], [2.0, 20.0, 0.6, -1.5]), diff_step=0.02, max_nfev=60)
        print("start", st, "->", [round(float(v), 4) for v in s.x], "cost", round(2 * s.cost, 2), flush=True)
        if best is None or s.cost < best.cost:
            best = s
    p = params(best.x); print("best", {k: round(v, 5) for k, v in p.items()})
    resid(best.x, True)
    print("T2 model:", {r: round(t2(r), 1) for r in (7.0, 7.25, 7.5, 7.75, 8.0, 8.25, 8.5, 9.0, 10.0)})
    print("T4 model:", {l: round(t4(l, 7.0), 2) for l in (2, 5, 8, 10)})
    json.dump({"params": p, "x": [float(v) for v in best.x], "cost": 2 * best.cost}, open("refit3.json", "w"), indent=1)
