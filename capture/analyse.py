#!/usr/bin/env python3
"""Measure the SH-101 filter captures (see CAPTURE.md) and write the calibration data.

    python3 analyse.py <folder of WAVs> [outdir]      -> outdir/report.md, calib.json, *.png

Files are matched by take id anywhere in the name (Ableton's "All Individual Tracks" export names each file after
its track: "1-T1_cut05.wav", "SH101 T1_cut05.wav" ... all work). Missing takes are reported and skipped.
Needs numpy, scipy, matplotlib.
"""
import json
import re
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

from takes import BEAT, CLIPS, TAKES, TRACK_WINDOW, WINDOW

warnings = []


# ---------------------------------------------------------------------------------------------- reading
def read_wav(path):
    """-> (mono float64 in -1..1, sample rate). PCM 16/24/32-bit and 32-bit float."""
    try:
        with wave.open(str(path), "rb") as w:
            n, ch, sw, fs = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
            raw = w.readframes(n)
        if sw == 3:
            b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
            x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
            x = np.where(x >= 1 << 23, x - (1 << 24), x) / float(1 << 23)
        elif sw == 2:
            x = np.frombuffer(raw, "<i2") / 32768.0
        elif sw == 4:
            x = np.frombuffer(raw, "<i4") / 2147483648.0
        else:
            raise ValueError(f"{sw * 8}-bit PCM")
    except wave.Error:                                         # 32-bit float WAV (format 3)
        from scipy.io import wavfile
        fs, x = wavfile.read(str(path))
        ch = 1 if x.ndim == 1 else x.shape[1]
        x = x.astype(np.float64).reshape(-1)
    x = np.asarray(x, np.float64).reshape(-1, ch).mean(axis=1)
    return x, fs


def find_files(folder):
    ids = sorted((t["id"] for t in TAKES), key=len, reverse=True)
    found = {}
    for p in sorted(Path(folder).rglob("*")):
        if p.suffix.lower() not in (".wav", ".wave"):
            continue
        for tid in ids:                                        # longest id first: T1_cut10 before T1_cut1
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(tid)}(?![0-9])", p.stem):
                if tid in found:
                    warnings.append(f"{tid}: two files ({found[tid].name}, {p.name}); using the first")
                else:
                    found[tid] = p
                break
    return found


# ---------------------------------------------------------------------------------------------- helpers
def db(x):
    return 20 * np.log10(np.maximum(x, 1e-12))


def rms(x):
    return float(np.sqrt(np.mean(x * x))) if len(x) else 0.0


def onset_shift(x, fs, nominal, tid=""):
    """Seconds by which the take starts later than the clip says (plug-in latency, a render not quite from bar 1).
    Only small shifts are believed: a first note that stays silent (a filter too low to sing) would otherwise
    shift every window onto the next note."""
    env = np.abs(x)
    pk = env.max() if len(env) else 0
    if pk < 1e-4:
        return 0.0
    i = int(np.argmax(env > 0.01 * pk))
    sh = i / fs - nominal
    if sh > 0.25:
        warnings.append(f"{tid}: sound starts {sh:.2f} s after its note; read at the clip's own timing")
        return 0.0
    return max(-0.05, sh)


def window(x, fs, t0, t1):
    return x[int(t0 * fs):int(t1 * fs)]


def pitch(x, fs, fmin=5.0, fmax=None):
    """Strongest spectral peak (Hann, 8x zero-pad, parabolic on log magnitude) -> (Hz, amplitude)."""
    fmax = fmax or 0.45 * fs
    n = len(x)
    nfft = 1 << int(np.ceil(np.log2(n * 8)))
    X = np.abs(np.fft.rfft(x * np.hanning(n), nfft))
    f = np.arange(len(X)) * fs / nfft
    band = (f >= fmin) & (f <= fmax)
    k = int(np.flatnonzero(band)[np.argmax(X[band])])
    a, b, c = np.log(X[k - 1:k + 2] + 1e-30)
    d = 0.5 * (a - c) / (a - 2 * b + c)
    return (k + d) * fs / nfft, float(np.exp(b - 0.25 * (a - c) * d) * 2 / np.sum(np.hanning(n)))


def harmonics(x, fs, f0, n=10):
    """Amplitudes of harmonics 1..n of f0 (single-bin DFT on a Hann window, each refined +-0.5%)."""
    w = np.hanning(len(x))
    t = np.arange(len(x)) / fs
    out = []
    for h in range(1, n + 1):
        best = 0.0
        for df in np.linspace(-0.005, 0.005, 11):
            fh = h * f0 * (1 + df)
            if fh >= fs / 2:
                break
            best = max(best, abs(np.sum(x * w * np.exp(-2j * np.pi * fh * t))) * 2 / np.sum(w))
        out.append(best)
    return np.array(out)


def psd(x, fs):
    f, p = signal.welch(x, fs, nperseg=16384, noverlap=12288)
    return f, p


def smooth_oct(f, y_db, frac=1 / 12):
    """Fractional-octave smoothing of a dB curve (on power)."""
    p = 10 ** (y_db / 10)
    out = np.empty_like(y_db)
    for i, fi in enumerate(f):
        if fi <= 0:
            out[i] = y_db[i]
            continue
        m = (f >= fi * 2 ** (-frac / 2)) & (f <= fi * 2 ** (frac / 2))
        out[i] = 10 * np.log10(np.mean(p[m]))
    return out


# ---------------------------------------------------------------------------------------------- tests
def load(found, tid):
    if tid not in found:
        return None
    x, fs = read_wav(found[tid])
    t = next(t for t in TAKES if t["id"] == tid)
    nominal = CLIPS[t["clip"]]["notes"][0][1] * BEAT
    sh = onset_shift(x, fs, nominal, tid)
    if np.max(np.abs(x)) >= 0.999:
        warnings.append(f"{tid}: reaches full scale (clipped?) - lower TAL's volume and bounce all takes again")
    return x, fs, sh, t


def steady(found, tid):
    r = load(found, tid)
    if r is None:
        return None
    x, fs, sh, t = r
    a, b = WINDOW[t["clip"]]
    return window(x, fs, a + sh, b + sh), fs


def t0_ref(found):
    s = steady(found, "T0_open")
    if s is None:
        warnings.append("T0_open missing: levels are given in dBFS instead of re the open saw")
        return 1.0
    return rms(s[0])


def t1(found, ref):
    rows = []
    for t in (t for t in TAKES if t["test"] == "T1"):
        s = steady(found, t["id"])
        if s is None:
            continue
        x, fs = s
        if rms(x) < 1e-4:
            warnings.append(f"{t['id']}: silent - the filter did not sing (see CAPTURE.md: the noise nudge)")
            continue
        f0, _ = pitch(x, fs)
        h = harmonics(x, fs, f0, 5)
        rows.append({"slider": t["value"], "hz": f0, "level_db": db(rms(x) / ref),
                     "thd_pct": 100 * float(np.sqrt(np.sum(h[1:] ** 2)) / max(h[0], 1e-12))})
    # fit only takes that sing at full level (a take still building up reads a wrong pitch), and below 15 kHz
    # (the top of the range may hit a ceiling)
    med = float(np.median([r["level_db"] for r in rows])) if rows else 0.0
    for r in rows:
        r["in_fit"] = r["hz"] < 15000 and r["level_db"] > med - 10
    fr = [r for r in rows if r["in_fit"]]
    if len(fr) >= 3:
        s = np.array([r["slider"] for r in fr]); lf = np.log2([r["hz"] for r in fr])
        m, c = np.polyfit(s, lf, 1)
        fit = {"octaves_per_slider_unit": m, "hz_at_0": 2 ** c, "max_dev_cents": float(np.max(np.abs(lf - (m * s + c))) * 1200),
               "points": len(fr)}
    else:
        fit = None
    return {"rows": rows, "loglinear_fit": fit}


def t2(found, ref):
    rows = []
    for t in (t for t in TAKES if t["test"] == "T2"):
        s = steady(found, t["id"])
        if s is None:
            continue
        x, fs = s
        lv = db(rms(x) / ref)
        row = {"res": t["value"], "level_db": lv}
        if lv > -50:
            row["hz"] = pitch(x, fs)[0]
        rows.append(row)
    # Past the onset a self-oscillation's power grows linearly with the excess loop gain (a Hopf bifurcation):
    # fit power against resonance over the first three singing takes and take its zero.
    sing = [r for r in rows if r["level_db"] > -40][:3]
    onset, rule = None, None
    if len(sing) >= 2:
        x = np.array([r["res"] for r in sing]); y = 10 ** (np.array([r["level_db"] for r in sing]) / 10)
        m, c = np.polyfit(x, y, 1)
        if m > 0:
            onset, rule = float(-c / m), "zero of power against resonance, first singing takes"
    # the bracket the captures prove: last silent step, first singing step. A Hopf extrapolation outside it is
    # wrong for this filter's law (a diode-limited loop jumps straight to full level), so fall back to the bracket
    bracket = None
    for a, b in zip(rows, rows[1:]):
        if a["level_db"] <= -40 < b["level_db"]:
            bracket = (a["res"], b["res"])
            break
    if bracket and (onset is None or not bracket[0] <= onset <= bracket[1]):
        a, b = next((a, b) for a, b in zip(rows, rows[1:]) if a["res"] == bracket[0])
        onset = a["res"] + (b["res"] - a["res"]) * (-40 - a["level_db"]) / (b["level_db"] - a["level_db"])
        rule = "crossing of -40 dB re the open saw, between the last silent and first singing steps"
    if rows and rows[0]["level_db"] > -40:
        warnings.append("T2: already singing at the lowest resonance captured - add lower steps")
    return {"rows": rows, "onset_res": onset, "onset_rule": rule, "onset_bracket": bracket}


def band_db(f, p_ratio, lo, hi):
    """Mean power ratio over lo..hi Hz, in dB (averaging power over the band keeps the noise estimate steady)."""
    m = (f >= lo) & (f <= hi)
    return float(10 * np.log10(np.mean(p_ratio[m])))


def crossing(grid, h, level, start):
    """First frequency above start where h falls through level, interpolated between grid points."""
    i = np.flatnonzero((grid > start) & (h < level))
    if not len(i) or i[0] == 0:
        return None
    j = i[0]
    return float(np.exp(np.interp(level, [h[j], h[j - 1]], [np.log(grid[j]), np.log(grid[j - 1])])))


def t3(found):
    op = steady(found, "T3_open")
    if op is None:
        warnings.append("T3_open missing: T3 cannot be normalised, skipped")
        return None
    f, p_open = psd(*op)
    grid = np.geomspace(20, 15000, 240)
    out = {"grid_hz": grid.tolist(), "takes": []}
    res0 = None
    for t in (t for t in TAKES if t["test"] == "T3" and t["value"] is not None):
        s = steady(found, t["id"])
        if s is None:
            continue
        _, p = psd(*s)
        ratio = np.maximum(p, 1e-30) / np.maximum(p_open, 1e-30)
        hg = np.interp(grid, f, smooth_oct(f, 10 * np.log10(ratio), 1 / 6))
        row = {"res": t["value"], "response_db": hg.tolist()}
        if t["value"] == 0:
            p0 = band_db(f, ratio, 20, 50)                      # first pass, then a band scaled to the corner
            fc = crossing(grid, hg, p0 - 3, 50)
            if fc:
                p0 = band_db(f, ratio, 20, max(40.0, min(0.15 * fc, 200.0)))
                fc = crossing(grid, hg, p0 - 3, 50)
            res0 = {"passband_db": p0, "corner_hz": fc}
            row.update(res0)
            if fc:
                f4, f8 = 4 * fc, min(8 * fc, 12000)
                if f8 > f4 * 1.4:
                    row["slope_db_per_oct"] = float((np.interp(f8, grid, hg) - np.interp(f4, grid, hg)) / np.log2(f8 / f4))
                    row["slope_between_hz"] = [f4, f8]
        elif res0:
            fc = res0["corner_hz"] or 500.0
            pb = band_db(f, ratio, 20, max(40.0, min(0.15 * fc, 200.0)))
            row["passband_db"] = pb
            row["bass_loss_db"] = pb - res0["passband_db"]
            # the peak from the raw ratio, lightly smoothed (1/48 octave): a resonant peak is only a few Hz wide
            fine = smooth_oct(f, 10 * np.log10(ratio), 1 / 48)
            m = (f >= fc / 2) & (f <= 8 * fc)
            k = int(np.flatnonzero(m)[np.argmax(fine[m])])
            row["peak_hz"] = float(f[k])
            row["peak_over_passband_db"] = float(fine[k] - pb)
            row["peak_over_res0_passband_db"] = float(fine[k] - res0["passband_db"])
        out["takes"].append(row)
    if res0 is None:
        warnings.append("T3_res0000 missing: no corner, bass loss or slope")
    return out


def t4(found):
    rows = []
    f0 = 440 * 2 ** ((36 - 69) / 12)
    for t in (t for t in TAKES if t["test"] == "T4"):
        s = steady(found, t["id"])
        if s is None:
            continue
        x, fs = s
        h = harmonics(x, fs, f0, 30)
        res, lvl = t["value"]
        rows.append({"res": res, "level": lvl, "rms_db": db(rms(x)), "harmonics_db": db(h).tolist()})
    for r in rows:                                             # resonance's share, per mixer level: r7 against r0
        r0 = next((q for q in rows if q["res"] == 0 and q["level"] == r["level"]), None)
        if r0 and r["res"]:
            r["rms_re_res0_db"] = r["rms_db"] - r0["rms_db"]
    return {"f0_hz": f0, "rows": rows}


def t5(found):
    r = load(found, "T5_track")
    if r is None:
        return None
    x, fs, sh, _ = r
    rows = []
    for note, start, _ in CLIPS["track"]["notes"]:
        a = start * BEAT + sh
        seg = window(x, fs, a + TRACK_WINDOW[0], a + TRACK_WINDOW[1])
        if rms(seg) < 1e-4:
            warnings.append(f"T5_track: note {note} silent")
            continue
        rows.append({"note": note, "hz": pitch(seg, fs)[0], "level_db": db(rms(seg))})
    fit = None
    med = float(np.median([r["level_db"] for r in rows])) if rows else 0.0
    for r_ in rows:                                            # a note still building up reads a wrong pitch
        r_["in_fit"] = r_["level_db"] > med - 10
    fr = [r_ for r_ in rows if r_["in_fit"]]
    if len(fr) >= 3:
        n = np.array([r["note"] for r in fr]) / 12.0; lf = np.log2([r["hz"] for r in fr])
        m, c = np.polyfit(n, lf, 1)
        for r_ in rows:
            r_["dev_cents"] = float((np.log2(r_["hz"]) - (m * r_["note"] / 12 + c)) * 1200)
        fit = {"octaves_per_octave": m, "max_dev_cents": max(abs(r_["dev_cents"]) for r_ in fr), "points": len(fr)}
    return {"rows": rows, "fit": fit}


# ---------------------------------------------------------------------------------------------- report
def plots(res, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if res["T1"]["rows"]:
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.semilogy([r["slider"] for r in res["T1"]["rows"]], [r["hz"] for r in res["T1"]["rows"]], "o-")
        ax.set(xlabel="Cutoff slider", ylabel="Singing pitch (Hz)", title="T1: cutoff taper")
        ax.grid(True, which="both", alpha=0.3); fig.tight_layout(); fig.savefig(out / "t1_taper.png", dpi=120); plt.close(fig)
    if res["T3"]:
        fig, ax = plt.subplots(figsize=(6, 3.5))
        g = res["T3"]["grid_hz"]
        for r in res["T3"]["takes"]:
            ax.semilogx(g, r["response_db"], label=f"res {r['res']:g}")
        ax.set(xlabel="Hz", ylabel="dB re open", title="T3: response against resonance (cutoff 5, 1/6-octave smoothed)", ylim=(-80, 30))
        ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(out / "t3_response.png", dpi=120); plt.close(fig)
    if res["T5"] and res["T5"]["fit"]:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot([r["note"] for r in res["T5"]["rows"]], [r["dev_cents"] for r in res["T5"]["rows"]], "o-")
        ax.set(xlabel="MIDI note", ylabel="cents from fit", title="T5: keyboard tracking")
        ax.grid(True, alpha=0.3); fig.tight_layout(); fig.savefig(out / "t5_tracking.png", dpi=120); plt.close(fig)


def report(res, found, out):
    L = ["# SH-101 filter capture: measurements", "",
         f"Takes found: {len(found)} of {len(TAKES)}.", ""]
    if warnings:
        L += ["## Warnings", ""] + [f"- {w}" for w in warnings] + [""]
    t = res["T1"]
    if t["rows"]:
        L += ["## T1 cutoff taper (resonance 10)", "", "| Slider | Singing pitch (Hz) | Level (dB re open saw) | THD (%) |", "|---:|---:|---:|---:|"]
        L += [f"| {r['slider']:g}{'' if r['in_fit'] else ' (not fitted)'} | {r['hz']:.1f} | {r['level_db']:.1f} | {r['thd_pct']:.2f} |" for r in t["rows"]]
        if t["loglinear_fit"]:
            q = t["loglinear_fit"]
            L += ["", f"Log-linear fit over the {q['points']} takes singing at full level below 15 kHz: {q['octaves_per_slider_unit']:.3f} octaves per slider unit, "
                      f"{q['hz_at_0']:.1f} Hz at 0, worst deviation {q['max_dev_cents']:.0f} cents."]
        L += [""]
    t = res["T2"]
    if t["rows"]:
        L += ["## T2 onset of self-oscillation (cutoff 5)", "", "| Res | Level (dB re open saw) | Pitch (Hz) |", "|---:|---:|---:|"]
        L += [f"| {r['res']:g} | {r['level_db']:.1f} | {r.get('hz', float('nan')):.1f} |" for r in t["rows"]]
        L += ["", (f"Onset: resonance **{t['onset_res']:.2f}** ({t['onset_rule']}"
                   + (f"; silent at {t['onset_bracket'][0]:g}, singing at {t['onset_bracket'][1]:g}" if t.get("onset_bracket") else "") + ").")
              if t["onset_res"] is not None else "Onset: not bracketed.", ""]
    t = res["T3"]
    if t:
        L += ["## T3 response against resonance (cutoff 5, noise)", "",
              "| Res | Passband (dB) | Bass loss (dB) | Peak (Hz) | Peak over passband (dB) |", "|---:|---:|---:|---:|---:|"]
        for r in t["takes"]:
            L += [f"| {r['res']:g} | {r['passband_db']:.1f} | {r.get('bass_loss_db', 0):.1f} | "
                  f"{r.get('peak_hz', float('nan')):.0f} | {r.get('peak_over_passband_db', float('nan')):.1f} |"]
        r0 = next((r for r in t["takes"] if r["res"] == 0), None)
        if r0 and r0.get("corner_hz"):
            L += ["", f"Resonance 0: -3 dB corner {r0['corner_hz']:.0f} Hz"
                      + (f", slope {r0['slope_db_per_oct']:.1f} dB/octave above it." if "slope_db_per_oct" in r0 else ".")]
            sing = next((r["hz"] for r in res["T1"]["rows"] if r["slider"] == 5), None)
            if sing:
                L += [f"Singing pitch at the same cutoff (T1, slider 5): {sing:.0f} Hz, **{sing / r0['corner_hz']:.3f} x the corner** "
                      "(an ideal 4-pole ladder: 2.30)."]
        L += [""]
    t = res["T4"]
    if t["rows"]:
        L += ["## T4 drive (saw C2, cutoff 5)", "", "| Res | Saw level | Output (dBFS rms) | Resonance's share (dB re res 0) |", "|---:|---:|---:|---:|"]
        L += [f"| {r['res']} | {r['level']} | {r['rms_db']:.1f} | {r.get('rms_re_res0_db', float('nan')):.1f} |" for r in t["rows"]]
        L += ["", "The harmonic levels per take are in calib.json.", ""]
    t = res["T5"]
    if t and t["fit"]:
        L += ["## T5 keyboard tracking (kybd 10, resonance 10)", "",
              f"{t['fit']['octaves_per_octave']:.3f} octaves per octave, worst deviation {t['fit']['max_dev_cents']:.1f} cents.", ""]
        L += ["| Note | Hz | Cents from fit |", "|---:|---:|---:|"] + [f"| {r['note']}{'' if r['in_fit'] else ' (not fitted)'} | {r['hz']:.1f} | {r['dev_cents']:+.1f} |" for r in t["rows"]]
    (out / "report.md").write_text("\n".join(L) + "\n")


def main(folder, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    found = find_files(folder)
    missing = [t["id"] for t in TAKES if t["id"] not in found]
    if missing:
        warnings.append(f"missing takes ({len(missing)}): {', '.join(missing)}")
    ref = t0_ref(found)
    res = {"T0_rms": ref, "T1": t1(found, ref), "T2": t2(found, ref), "T3": t3(found), "T4": t4(found), "T5": t5(found)}
    res["warnings"] = warnings
    res["files"] = {k: v.name for k, v in found.items()}
    (out / "calib.json").write_text(json.dumps(res, indent=1, default=float))
    plots(res, out)
    report(res, found, out)
    print(f"{len(found)}/{len(TAKES)} takes -> {out}/report.md, calib.json")
    for w in warnings:
        print("warning:", w)
    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "analysis")
