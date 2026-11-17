#!/usr/bin/env python3
"""TAL-BassLine-101 against the FM-1 (M-Vsynth2 FILTER TYPE 5): the two analyse.py results side by side.

    python3 compare_ab.py tal/calib.json fm1/calib.json sh101_ab.timeline.json [ab_report.md]

Both captures come from the same set (make_capture_set.py --fm1), each cut with split_takes.py and measured by the
same analyse.py. The FM-1's knobs are whole numbers, so its real RES per take (timeline "fm1") is used for T2.
Levels are re each capture's own open saw (T0), so the two outputs' gains do not matter.
"""
import json
import sys
from pathlib import Path


def row(rows, key, val):
    return next((r for r in rows if abs(r[key] - val) < 1e-6), None)


def onset(rows, res_of):
    """the last silent and the first singing RES (singing: above -40 dB re the open saw)"""
    rs = sorted(rows, key=lambda r: res_of(r))
    for a, b in zip(rs, rs[1:]):
        if a["level_db"] <= -40 < b["level_db"]:
            return res_of(a), res_of(b)
    return None


def main(tal_p, fm_p, tl_p, out_p="ab_report.md"):
    T, F, tl = (json.loads(Path(p).read_text()) for p in (tal_p, fm_p, tl_p))
    act = tl.get("fm1", {})
    L = ["# SH-101: TAL-BassLine-101 against the FM-1 (M-Vsynth2 FILTER TYPE 5)", "",
         "Each capture's levels are re its own open saw (T0). The FM-1's RES is its real slider position (whole knob "
         "values, taper 2.0).", ""]

    L += ["## T1: self-oscillation against FREQ (RES 10)", "",
          "| FREQ | TAL Hz | FM-1 Hz | cents | TAL level | FM-1 level | TAL THD % | FM-1 THD % |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in T["T1"]["rows"]:
        f = row(F["T1"]["rows"], "slider", r["slider"])
        if not f:
            continue
        c = 1200 * __import__("math").log2(f["hz"] / r["hz"]) if f["hz"] > 0 and r["hz"] > 0 else float("nan")
        L.append(f"| {r['slider']:g} | {r['hz']:.1f} | {f['hz']:.1f} | {c:+.0f} | {r['level_db']:+.1f} | {f['level_db']:+.1f} | "
                 f"{r['thd_pct']:.2f} | {f['thd_pct']:.2f} |")

    fres = lambda r: act.get(f"T2_res{round(r['res'] * 100):04d}", {}).get("res", r["res"])
    L += ["", "## T2: where it starts to sing (FREQ 5)", "",
          f"TAL: silent at {onset(T['T2']['rows'], lambda r: r['res'])}; FM-1: {onset(F['T2']['rows'], fres)} "
          "(the last silent, the first singing RES)", "",
          "| RES (TAL) | RES (FM-1, real) | TAL dB | FM-1 dB |", "|---:|---:|---:|---:|"]
    for r in T["T2"]["rows"]:
        f = row(F["T2"]["rows"], "res", r["res"])
        if f:
            L.append(f"| {r['res']:.2f} | {fres(f):.2f} | {r['level_db']:+.1f} | {f['level_db']:+.1f} |")

    L += ["", "## T3: noise response at FREQ 5", "",
          "| RES | TAL bass loss | FM-1 | TAL peak Hz | FM-1 | TAL peak dB | FM-1 |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for r in T["T3"]["takes"]:
        f = row(F["T3"]["takes"], "res", r["res"])
        if not f:
            continue
        g = lambda d, k, fmt: format(d[k], fmt) if d.get(k) is not None else "-"
        L.append(f"| {r['res']:g} | {g(r, 'bass_loss_db', '+.1f')} | {g(f, 'bass_loss_db', '+.1f')} | {g(r, 'peak_hz', '.0f')} | "
                 f"{g(f, 'peak_hz', '.0f')} | {g(r, 'peak_over_passband_db', '+.1f')} | {g(f, 'peak_over_passband_db', '+.1f')} |")
    r0, f0 = row(T["T3"]["takes"], "res", 0.0), row(F["T3"]["takes"], "res", 0.0)
    if r0 and f0:
        L.append(f"\nRES 0: corner TAL {r0.get('corner_hz', 0):.0f} Hz, FM-1 {f0.get('corner_hz', 0):.0f} Hz; slope TAL "
                 f"{r0.get('slope_db_per_oct', 0):.1f}, FM-1 {f0.get('slope_db_per_oct', 0):.1f} dB/oct")

    L += ["", "## T4: a saw at C2 through FREQ 5, RES 0 and 7 (the FM-1's level is MIX against a parked triangle)", "",
          "| level | RES | TAL dB | FM-1 dB | TAL: RES costs | FM-1 |", "|---:|---:|---:|---:|---:|---:|"]
    for r in T["T4"]["rows"]:
        f = next((x for x in F["T4"]["rows"] if x["res"] == r["res"] and x["level"] == r["level"]), None)
        if f:
            L.append(f"| {r['level']} | {r['res']} | {r['rms_db']:+.1f} | {f['rms_db']:+.1f} | "
                     f"{r.get('rms_re_res0_db', 0):+.2f} | {f.get('rms_re_res0_db', 0):+.2f} |")

    if T.get("T5") and F.get("T5"):
        L += ["", "## T5: keyboard tracking (FREQ 3, RES 10, KYBD full)", "", "| note | TAL Hz | FM-1 Hz |", "|---:|---:|---:|"]
        for r in T["T5"]["rows"]:
            f = row(F["T5"]["rows"], "note", r["note"])
            if f:
                L.append(f"| {r['note']} | {r['hz']:.1f} | {f['hz']:.1f} |")
        L.append(f"\nFit: TAL {T['T5'].get('fit')}; FM-1 {F['T5'].get('fit')}")
    if F.get("warnings"):
        L += ["", "## FM-1 analysis warnings", ""] + [f"- {w}" for w in F["warnings"]]
    Path(out_p).write_text("\n".join(L) + "\n")
    print(f"-> {out_p}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(*sys.argv[1:5])
