#!/usr/bin/env python3
"""Write the capture clips as standard MIDI files (format 0, 120 BPM, 4/4): midi/<clip>.mid.

    python3 make_midi.py [outdir]

No dependencies. Drag a file onto a MIDI track in Ableton to get the clip.
"""
import struct
import sys
from pathlib import Path

from takes import BPM, CLIPS

PPQ = 480


def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(out))


def clip_bytes(clip):
    ev = []                                                      # (tick, order, bytes); note-offs before note-ons
    for note, start, length in clip["notes"]:
        ev.append((start * PPQ, 1, bytes([0x90, note, 100])))
        ev.append(((start + length) * PPQ, 0, bytes([0x80, note, 0])))
    ev.sort()
    tempo = int(round(60_000_000 / BPM))
    trk = vlq(0) + b"\xFF\x51\x03" + tempo.to_bytes(3, "big")
    trk += vlq(0) + b"\xFF\x58\x04\x04\x02\x18\x08"            # 4/4
    t = 0
    for tick, _, data in ev:
        trk += vlq(tick - t) + data
        t = tick
    trk += vlq(clip["beats"] * PPQ - t) + b"\xFF\x2F\x00"      # end of track at the clip's length
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, PPQ) + b"MTrk" + struct.pack(">I", len(trk)) + trk


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name, clip in CLIPS.items():
        (out / f"{name}.mid").write_bytes(clip_bytes(clip))
        print(f"{out / name}.mid  ({clip['beats'] * 60 / BPM:.1f} s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "midi")
