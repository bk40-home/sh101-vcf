#!/usr/bin/env python3
"""Fit the SH-101 reference model to a capture report (TAL-BassLine-101, or a real unit later).

    python3 fit.py tal/calib.json [--kit ../capture] [--no-validate]
        -> fit/params.json   the fitted parameters (render_takes.py --set ... form too)
           fit/fit_report.md target against fitted model, per measurement

Stages, each fitting only what its measurements pin down:
  A  resonance and output compensation, from the filter's small-signal (linear) response:
     T3 at RES 2.5 and 5 (bass loss, peak height, peak frequency; RES 7.5 and up already sing in a noise take)
     and the T2 onset bracket  ->  k at each RES (kmax, res_curve), fwd
  B  drive and diode level, from self-oscillation simulated by the model:
     T1/T2 singing level re the open saw, and THD  ->  drive, clip
  C  cutoff taper, straight from T1 (sliders that sing at full level), corrected for where the model sings
  V  validation: all 41 takes rendered with the fitted model, measured by analyse.py, compared line by line.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, least_squares

from sh101ref import Model, params

HERE = Path(__file__).resolve().parent
FS = 44100.0
SCHEMATIC = params()                                     # the schematic-derived defaults


# ------------------------------------------------------------------------------------------- linear model
def lin_P(f, cap):
    s = 1j * np.asarray(f, float)
    P = np.ones_like(s)
    for c in cap:
        P = P / (1 + s * c)
    return P


def sing_ratio(cap):
    """frequency (re the pole frequency) where the loop's phase reaches -180, and the k that makes it sing"""
    ph = lambda f: np.angle(lin_P(f, cap)) if f < 0.5 else np.unwrap(np.angle(lin_P(np.linspace(1e-3, f, 400), cap)))[-1]
    f180 = brentq(lambda f: ph(f) + np.pi, 0.3, 3.0)
    return f180, 1 / abs(lin_P(f180, cap))


def lin_metrics(k, fwd, cap, sing_hz, corner0=None):
    """the T3 measurements of the linear model (fc chosen so it sings at sing_hz), as analyse.py takes them"""
    f180, _ = sing_ratio(cap)
    fc = sing_hz / f180
    f = np.geomspace(5, 20000, 6000)
    H = np.abs(lin_P(f / fc, cap) / (1 + k * lin_P(f / fc, cap))) * (1 + fwd * k)
    hdb = 20 * np.log10(H)
    if corner0 is None:                                   # RES 0: the -3 dB corner
        corner = f[np.argmax(hdb < hdb[0] - 3)]
        return {"corner_hz": corner, "fc": fc}
    band = (f >= 20) & (f <= max(40.0, min(0.15 * corner0, 200.0)))
    pb = 10 * np.log10(np.mean(H[band] ** 2))
    m = (f >= corner0 / 2) & (f <= 8 * corner0)
    i = np.flatnonzero(m)[np.argmax(hdb[m])]
    return {"passband_db": pb, "peak_hz": f[i], "peak_over_passband_db": hdb[i] - pb}


def stage_a(tal, cap, fwd_fixed=None):
    t3 = {r["res"]: r for r in tal["T3"]["takes"]}
    sing = next(r["hz"] for r in tal["T1"]["rows"] if r["slider"] == 5)
    r0 = lin_metrics(0, 0, cap, sing)
    clean = [r for r in (2.5, 5.0) if r in t3]

    def resid(x):
        fwd, ks = (fwd_fixed, x) if fwd_fixed is not None else (x[0], x[1:])
        out = []
        for kk, res in zip(ks, clean):
            m = lin_metrics(kk, fwd, cap, sing, r0["corner_hz"])
            out += [(m["passband_db"] - 0.0) - t3[res]["bass_loss_db"],             # bass loss re RES 0
                    m["peak_over_passband_db"] - t3[res]["peak_over_passband_db"],
                    3 * np.log2(m["peak_hz"] / t3[res]["peak_hz"]) * 12]             # semitones, weighted x3
        return out
    if fwd_fixed is not None:
        sol = least_squares(resid, [1.0] * len(clean), bounds=([0] * len(clean), [4] * len(clean)))
        fwd, ks = fwd_fixed, dict(zip(clean, sol.x))
    else:
        sol = least_squares(resid, [0.25] + [1.0] * len(clean), bounds=([0] + [0] * len(clean), [1.5] + [4] * len(clean)))
        fwd, ks = sol.x[0], dict(zip(clean, sol.x[1:]))

    # onset: the bracket T2 proves (last silent, first singing), the linear k that sings there
    rows = tal["T2"]["rows"]
    br = next(((a["res"], b["res"]) for a, b in zip(rows, rows[1:]) if a["level_db"] <= -40 < b["level_db"]), None)
    _, kcrit = sing_ratio(cap)
    pts = [(r, ks[r]) for r in clean] + ([(sum(br) / 2, kcrit)] if br else [])
    # k = kmax (res/10)^p through the points (log-linear least squares)
    lr = np.log([p[0] / 10 for p in pts]); lk = np.log([p[1] for p in pts])
    w = [1.0] * len(clean) + ([3.0] if br else [])
    p, c = np.polyfit(lr, lk, 1, w=w)
    kmax = float(np.exp(c))
    fitpts = [(r, k, kmax * (r / 10) ** p) for r, k in pts]
    return {"fwd": float(fwd), "k_at": {str(r): float(k) for r, k in ks.items()}, "onset_bracket": br,
            "k_crit": float(kcrit), "kmax": kmax, "res_curve": float(p), "k_points": fitpts,
            "corner_model": float(r0["corner_hz"]), "corner_tal": t3[0.0]["corner_hz"] if 0.0 in t3 else None,
            "lin_residuals": [float(v) for v in resid(sol.x)], "sing_hz": sing}


# ------------------------------------------------------------------------------------------- self-oscillation
SAW_RMS = 1 / np.sqrt(3)                                  # T0: a full saw through the open filter (passband 1)


def selfosc(p, fc, k, secs=1.6):
    m = Model(p, FS)
    y = m.run(np.zeros(int(FS * secs)), fc, k)[-int(FS * 0.8):]
    rms = np.sqrt(np.mean(y ** 2))
    if rms < 1e-6:
        return -200.0, 0.0, 0.0
    sp = np.abs(np.fft.rfft(y * np.hanning(len(y)), 1 << 18))
    fr = np.fft.rfftfreq(1 << 18, 1 / FS)
    i = np.argmax(sp)
    f0 = fr[i]
    h = [sp[np.argmin(abs(fr - n * f0))] for n in range(1, 6)]
    thd = 100 * np.sqrt(np.sum(np.square(h[1:]))) / h[0]
    return 20 * np.log10(rms / SAW_RMS), thd, f0


def stage_b(tal, a, cap, fc5):
    t2 = [r for r in tal["T2"]["rows"] if r["res"] >= 8.0]              # singing, settled within the take
    t1 = next(r for r in tal["T1"]["rows"] if r["slider"] == 5)
    kof = lambda res: a["kmax"] * (res / 10) ** a["res_curve"]
    sel = [t2[0], t2[len(t2) // 2], t2[-1]]

    f180, _ = sing_ratio(cap)

    def mk(x):
        return params(drive=float(x[0]), clip=float(x[1]), clip_sharp=float(x[2]), fwd=a["fwd"], kmax=a["kmax"],
                      res_curve=a["res_curve"], cap=cap, os=4, noise_floor=1e-4)

    def resid(x):
        p = mk(x)
        out = []
        for r in sel:
            lv, thd, _ = selfosc(p, fc5, kof(r["res"]))
            out.append(lv - r["level_db"])
        lv, thd, f0 = selfosc(p, fc5, kof(10.0))
        out.append(20 * (np.log10(max(thd, 1e-3)) - np.log10(t1["thd_pct"])) * 0.5)        # THD ratio (dB, half weight)
        out.append(2 * 12 * np.log2(f0 / (fc5 * f180)))                                      # pitch re the linear sing, semitones x2
        return out
    sol = least_squares(resid, [0.15, SCHEMATIC.clip, SCHEMATIC.clip_sharp], bounds=([0.01, 0.01, 2.0], [1.0, 3.0, 30.0]),
                        diff_step=0.05)
    p = mk(sol.x)
    rows = []
    for r in tal["T2"]["rows"]:
        lv, thd, f0 = selfosc(p, fc5, kof(r["res"]), 2.4)
        rows.append({"res": r["res"], "tal_db": r["level_db"], "model_db": lv, "model_hz": f0})
    lv, thd, f0 = selfosc(p, fc5, kof(10.0), 2.4)
    return {"drive": float(sol.x[0]), "clip": float(sol.x[1]), "clip_sharp": float(sol.x[2]), "t2_rows": rows,
            "res10": {"tal_db": t1["level_db"], "model_db": lv, "tal_thd": t1["thd_pct"], "model_thd": thd,
                      "tal_hz": t1["hz"], "model_hz": f0}}


# ------------------------------------------------------------------------------------------- cutoff taper
def stage_c(tal, cap, model_sing_ratio):
    rows = [r for r in tal["T1"]["rows"] if 3 <= r["slider"] <= 9]
    s = np.array([r["slider"] for r in rows]); lf = np.log2([r["hz"] for r in rows])
    m, c = np.polyfit(s, lf, 1)
    dev = float(np.max(np.abs(lf - (m * s + c))) * 1200)
    floor = min(r["hz"] for r in tal["T1"]["rows"] if r["slider"] <= 2)
    top = max(r["hz"] for r in tal["T1"]["rows"])
    # the model's cutoff parameter is its pole frequency; it sings at model_sing_ratio x that
    return {"cut_oct": float(m), "cut_hz0": float(2 ** c / model_sing_ratio), "fit_sliders": [3, 9],
            "worst_cents": dev, "tal_floor_hz": floor, "tal_top_hz": top}


# ------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("calib")
    ap.add_argument("--kit", default=str(HERE.parent / "capture"))
    ap.add_argument("--out", default=str(HERE / "fit"))
    ap.add_argument("--no-validate", action="store_true")
    ap.add_argument("--fit-fwd", action="store_true",
                    help="fit fwd to the reference too (default: keep the schematic's, R130 from VR18's hot end, pin 75)")
    a_ = ap.parse_args()
    tal = json.loads(Path(a_.calib).read_text())
    out = Path(a_.out); out.mkdir(parents=True, exist_ok=True)
    cap = list(SCHEMATIC.cap)

    print("A: resonance and output compensation (linear)")
    A = stage_a(tal, cap, None if a_.fit_fwd else SCHEMATIC.fwd)
    print(f"   fwd {A['fwd']:.3f} (schematic {SCHEMATIC.fwd:.3f}); k(2.5) {A['k_at'].get('2.5', float('nan')):.2f}, "
          f"k(5) {A['k_at'].get('5.0', float('nan')):.2f}; onset {A['onset_bracket']} -> k {A['k_crit']:.3f}")
    print(f"   k = {A['kmax']:.3f} (RES/10)^{A['res_curve']:.3f}   (schematic {SCHEMATIC.kmax:.3f} linear)")

    f180, _ = sing_ratio(cap)
    fc5 = A["sing_hz"] / f180
    print("B: drive and diode level (self-oscillation)")
    B = stage_b(tal, A, cap, fc5)
    print(f"   drive {B['drive']:.3f} (estimate was {SCHEMATIC.drive}), clip {B['clip']:.3f} (schematic {SCHEMATIC.clip:.3f}), "
          f"knee {B['clip_sharp']:.2f} (schematic {SCHEMATIC.clip_sharp:.2f})")
    # where the fitted model actually sings at cutoff 5, for the taper
    sing_ratio_model = B["res10"]["model_hz"] / fc5        # where the fitted model actually sings (pitch is a B target)
    print("C: cutoff taper")
    C = stage_c(tal, cap, sing_ratio_model)
    print(f"   {C['cut_oct']:.4f} octaves per slider unit, pole at {C['cut_hz0']:.3f} Hz at 0 (worst {C['worst_cents']:.0f} cents, "
          f"sliders 3-9); TAL floors at {C['tal_floor_hz']:.0f} Hz and tops out at {C['tal_top_hz']:.0f} Hz")

    fitted = {"drive": B["drive"], "clip": B["clip"], "clip_sharp": B["clip_sharp"], "fwd": A["fwd"], "kmax": A["kmax"], "res_curve": A["res_curve"],
              "cut_hz0": C["cut_hz0"], "cut_oct": C["cut_oct"]}
    (out / "params.json").write_text(json.dumps({"fitted": fitted, "A": A, "B": B, "C": C}, indent=1, default=float))
    sets = " ".join(f"--set {k}={v:.6g}" for k, v in fitted.items())
    (out / "render_args.txt").write_text(sets + "\n")

    val = None
    if not a_.no_validate:
        print("V: rendering all 41 takes with the fitted model, then analyse.py")
        subprocess.run([sys.executable, str(HERE / "render_takes.py"), str(out / "takes"), "--kit", a_.kit,
                        "--cut-min", str(C["tal_floor_hz"]), "--cut-max", str(C["tal_top_hz"])] + sets.split(),
                       check=True)
        subprocess.run([sys.executable, str(Path(a_.kit) / "analyse.py"), str(out / "takes"), str(out / "takes" / "analysis")],
                       check=True, stdout=subprocess.DEVNULL)
        val = json.loads((out / "takes" / "analysis" / "calib.json").read_text())
    report(tal, A, B, C, fitted, val, out)
    print(f"-> {out / 'fit_report.md'}")


def report(tal, A, B, C, fitted, val, out):
    S = SCHEMATIC
    L = ["# SH-101 model fitted to the capture", "",
         "## Fitted parameters", "",
         "| Parameter | Schematic | Fitted | Change |", "|:---|---:|---:|---:|"]
    for k, v in fitted.items():
        s = getattr(S, k)
        L.append(f"| `{k}` | {s:.4g} | {v:.4g} | {100 * (v / s - 1):+.0f}% |")
    L += ["", "`render_takes.py` arguments: `" + (out / "render_args.txt").read_text().strip() + "`", "",
          "## A. Resonance and output compensation (linear, from T3 at RES 2.5 and 5, and the T2 onset)", "",
          "| RES | k fitted | k from the fitted curve |", "|---:|---:|---:|"]
    L += [f"| {r:g} | {k:.3f} | {kc:.3f} |" for r, k, kc in A["k_points"]]
    L += ["", f"Onset bracket from T2: {A['onset_bracket']}; the linear loop sings at k = {A['k_crit']:.3f} (the two stage-1 "
              f"pole offset included).",
          f"Residuals of the linear fit (bass loss dB, peak dB, peak position x3 semitones): "
          + ", ".join(f"{v:+.2f}" for v in A["lin_residuals"]),
          f"Corner at RES 0: TAL {A['corner_tal']:.0f} Hz, linear model {A['corner_model']:.0f} Hz.", "",
          "## B. Drive and diode level (self-oscillation at cutoff 5)", "",
          "| RES | TAL level (dB re open saw) | Model |", "|---:|---:|---:|"]
    L += [f"| {r['res']:g} | {r['tal_db']:.1f} | {r['model_db']:.1f} |" for r in B["t2_rows"]]
    r10 = B["res10"]
    L += ["", f"RES 10: THD TAL {r10['tal_thd']:.2f}% / model {r10['model_thd']:.2f}%; pitch TAL {r10['tal_hz']:.1f} Hz / "
              f"model {r10['model_hz']:.1f} Hz.", "",
          "## C. Cutoff taper (T1)", "",
          f"{C['cut_oct']:.4f} octaves per slider unit over sliders 3-9 (worst {C['worst_cents']:.0f} cents from a straight line). "
          f"TAL stops singing lower than about {C['tal_floor_hz']:.0f} Hz (sliders 0-2, and C1/C2 in T5) and tops out at "
          f"{C['tal_top_hz']:.0f} Hz (slider 10): rendered as limits, not part of the model.", ""]
    if val:
        L += ["## V. All 41 takes: TAL against the fitted model (same analyse.py)", "",
              "| Measurement | TAL | Fitted model |", "|:---|---:|---:|"]
        tt, vt = {r["res"]: r for r in tal["T3"]["takes"]}, {r["res"]: r for r in val["T3"]["takes"]}
        L.append(f"| T3 corner at RES 0 (Hz) | {tt[0.0]['corner_hz']:.0f} | {vt[0.0]['corner_hz']:.0f} |")
        L.append(f"| T3 slope at RES 0 (dB/oct) | {tt[0.0].get('slope_db_per_oct', float('nan')):.1f} | {vt[0.0].get('slope_db_per_oct', float('nan')):.1f} |")
        for r in (2.5, 5.0, 7.5, 9.0, 10.0):
            if r in tt and r in vt:
                L.append(f"| T3 RES {r:g}: bass loss / peak (dB) | {tt[r]['bass_loss_db']:.1f} / {tt[r]['peak_over_passband_db']:.1f} | "
                         f"{vt[r]['bass_loss_db']:.1f} / {vt[r]['peak_over_passband_db']:.1f} |")
        tr2, vr2 = tal["T2"]["rows"], val["T2"]["rows"]
        br = lambda rows: next(((a["res"], b["res"]) for a, b in zip(rows, rows[1:]) if a["level_db"] <= -40 < b["level_db"]), None)
        L.append(f"| T2 onset bracket (silent, singing) | {br(tr2)} | {br(vr2)} |")
        for r in (8.0, 9.0, 10.0):
            a = next((x for x in tr2 if x["res"] == r), None); b = next((x for x in vr2 if x["res"] == r), None)
            if a and b:
                L.append(f"| T2 level at RES {r:g} (dB) | {a['level_db']:.1f} | {b['level_db']:.1f} |")
        for s in (3, 5, 7, 9):
            a = next((x for x in tal["T1"]["rows"] if x["slider"] == s), None); b = next((x for x in val["T1"]["rows"] if x["slider"] == s), None)
            if a and b:
                L.append(f"| T1 slider {s}: Hz / THD % | {a['hz']:.1f} / {a['thd_pct']:.2f} | {b['hz']:.1f} / {b['thd_pct']:.2f} |")
        for lv in (2, 10):
            a = next((x for x in tal["T4"]["rows"] if x["res"] == 7 and x["level"] == lv), None)
            b = next((x for x in val["T4"]["rows"] if x["res"] == 7 and x["level"] == lv), None)
            if a and b:
                L.append(f"| T4 RES 7, saw {lv}: resonance's share (dB) | {a['rms_re_res0_db']:.2f} | {b['rms_re_res0_db']:.2f} |")
        if tal["T5"] and val["T5"]:
            ok = lambda rows: [r for r in rows if r["note"] >= 48]
            def slope(rows):
                n = np.array([r["note"] for r in rows]) / 12; return np.polyfit(n, np.log2([r["hz"] for r in rows]), 1)[0]
            L.append(f"| T5 tracking, C3-C6 (oct/oct) | {slope(ok(tal['T5']['rows'])):.3f} | {slope(ok(val['T5']['rows'])):.3f} |")
    (out / "fit_report.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
