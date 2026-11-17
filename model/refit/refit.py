#!/usr/bin/env python3
"""Refit the diodes (level, knee) and the drive of sh101_vcf.h against TAL-BassLine-101, on the device module itself.
The loop gain is scaled with the diodes' small-signal gain, so the onset and the small-signal response (fitted before,
and matching TAL) stay put. Targets: T2's build-up (RES 7.25 .. 10), T1's level, THD and pitch at FREQ 5, T4's RES 7."""
import json
import numpy as np
from scipy.optimize import least_squares
from sim import setp, getp, t0, t1, t2, t4, L

BASE = dict(drive=0.19918, clip=0.51447, sharp=8.7977, fwd=0.202, kmax=5.8657, curve=1.14896, noise=1e-4)
T2 = {7.25: -26.5, 7.5: -14.0, 7.75: -4.7, 8.0: 0.0, 8.25: 2.3, 8.5: 3.6, 8.75: 4.5, 9.0: 5.2, 9.25: 5.7, 9.5: 6.1,
      9.75: 6.4, 10.0: 6.7}
T2W = {7.25: 0.3, 7.5: 0.5}                      # the steps still building up within the window: weighted down
T1 = dict(hz=268.4, level=6.6, thd=0.95)
T4 = {2: -0.89, 5: -1.10, 8: -1.41, 10: -1.62}

setp(**BASE)
D0_BASE = L.small_gain()


def params(x):
    clip, sharp, drive = x
    setp(**dict(BASE, clip=clip, sharp=sharp, drive=drive))
    d0 = L.small_gain()
    setp(kmax=BASE["kmax"] * D0_BASE / d0)          # the same small-signal loop gain k D0 as before
    return getp()


def resid(x, verbose=False):
    params(x)
    t0()
    r = []
    for res, v in T2.items():
        r.append(T2W.get(res, 1.0) * (t2(res) - v))
    if t2(7.0) > -40:
        r.append(10.0)                            # 7.0 must stay silent (the onset)
    f, lv, thd = t1()
    r += [lv - T1["level"], 2 * (np.log2(thd / T1["thd"])), 1200 * np.log2(f / T1["hz"]) / 20]
    for lvl, v in T4.items():
        r.append(2 * (t4(lvl, 7.0) - v))
    if verbose:
        print(" ".join(f"{v:+.2f}" for v in r))
    return r


if __name__ == "__main__":
    x0 = [BASE["clip"], BASE["sharp"], BASE["drive"]]
    print("before:", round(float(np.sum(np.square(resid(x0, True)))), 2))
    best = None
    for start in ([0.51, 8.8, 0.20], [0.4, 4.0, 0.2], [0.3, 2.0, 0.25], [0.6, 3.0, 0.15]):
        sol = least_squares(resid, start, bounds=([0.05, 0.3, 0.05], [2.0, 20.0, 0.6]), diff_step=0.02, max_nfev=60)
        print("start", start, "->", [round(v, 4) for v in sol.x], "cost", round(2 * sol.cost, 2))
        if best is None or sol.cost < best.cost:
            best = sol
    p = params(best.x)
    print("after:", round(2 * best.cost, 2))
    resid(best.x, True)
    json.dump({"params": p, "x": list(best.x), "cost": 2 * best.cost}, open("refit.json", "w"), indent=1)
