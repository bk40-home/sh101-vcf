#!/usr/bin/env python3
"""Cut the one-track capture export into its takes, and check each for the TAL demo's noise burst.

    python3 split_takes.py <export>.wav <set>.timeline.json [outdir]     -> outdir/<take id>.wav, bursts.txt
    python3 analyse.py outdir                                            (as for separate takes)

A take is flagged when, inside the part analyse.py reads, the energy above 8 kHz jumps more than 10 dB over that
take's own typical level (the demo's burst is a rising noise every minute; real takes are steady there). Flagged
takes are listed with the bar they start at, so only those need bouncing again.
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

from analyse import read_wav
from takes import BEAT, CLIPS, TAKES, TRACK_WINDOW, WINDOW


def write24(path, x, fs):
    v = np.clip(np.round(x * (1 << 23)), -(1 << 23), (1 << 23) - 1).astype(np.int32)
    b = np.stack([v & 255, (v >> 8) & 255, (v >> 16) & 255], axis=1).astype(np.uint8).tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(3); w.setframerate(fs); w.writeframes(b)


def windows(tk):
    """the (start, end) seconds within the take that analyse.py reads"""
    if tk["clip"] == "track":
        return [(nb * BEAT + TRACK_WINDOW[0], nb * BEAT + TRACK_WINDOW[1]) for _, nb, _ in CLIPS["track"]["notes"]]
    return [WINDOW[tk["clip"]]]


def burst(x, fs, wins):
    sos = signal.butter(4, 8000, "highpass", fs=fs, output="sos")
    hf = signal.sosfilt(sos, x)
    hop = int(0.05 * fs)
    worst = 0.0
    for a, b in wins:
        seg = hf[int(a * fs):int(b * fs)]
        if len(seg) < 4 * hop:
            continue
        e = np.array([np.mean(seg[i:i + hop] ** 2) for i in range(0, len(seg) - hop, hop)])
        floor = max(np.median(e), 1e-14)
        if np.sqrt(e.max()) > 10 ** (-70 / 20):                  # ignore anything below -70 dBFS
            worst = max(worst, 10 * np.log10(e.max() / floor))
    return worst


def main(wav, tl_path, out):
    x, fs = read_wav(wav)
    tl = json.loads(Path(tl_path).read_text())
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    by_id = {t["id"]: t for t in TAKES}
    flagged = []
    for ent in tl["takes"]:
        tk = by_id[ent["id"]]
        a = int(ent["start_s"] * fs)
        b = a + int(ent["beats"] * BEAT * fs)
        seg = x[a:min(b, len(x))]
        if len(seg) < (b - a) * 0.9:
            print(f"{ent['id']}: the export ends early (render all {tl['render_bars']} bars from 1.1.1)")
        write24(out / f"{ent['id']}.wav", seg, fs)
        jump = burst(seg, fs, windows(tk))
        if jump > 10:
            bar = ent["start_s"] / BEAT / 4 + 1
            flagged.append(f"{ent['id']}: +{jump:.0f} dB above 8 kHz (the demo's noise burst?): re-export start "
                           f"{bar:.0f}.1.1, length {ent['beats'] / 4:.0f}.0.0, save as {ent['id']}.wav into {out}")
    (out / "bursts.txt").write_text("\n".join(flagged) + "\n" if flagged else "none\n")
    print(f"{len(tl['takes'])} takes -> {out}")
    for f in flagged:
        print("flag:", f)
    if not flagged:
        print("no noise bursts found")
    return flagged


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "takes")
