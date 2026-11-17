"""The capture plan: every take, its MIDI clip and its TAL-BassLine-101 settings.

One source of truth for make_midi.py (the clips), CAPTURE.md (the sheet, by hand from this),
analyse.py (what to measure in each file) and tests/synth_takes.py (the self-test).

Slider positions are on the panel's 0..10 scale. Settings not listed are the COMMON ones.
"""

BPM = 120.0
BEAT = 60.0 / BPM          # 0.5 s

# Clips: (note, start beat, length beats) per note, and the clip length in beats.
CLIPS = {
    "hold4": {"notes": [(48, 1, 8)], "beats": 12},                      # C3, 0.5 .. 4.5 s
    "hold20": {"notes": [(48, 1, 40)], "beats": 44},                    # C3, 0.5 .. 20.5 s (noise needs averaging)
    "saw_c2": {"notes": [(36, 1, 8)], "beats": 12},                     # C2, 0.5 .. 4.5 s
    "track": {"notes": [(24 + 12 * i, 1 + 5 * i, 4) for i in range(6)],  # C1 .. C6, 2 s each, 0.5 s apart
              "beats": 32},
}

# Settings on every track (start from TAL's init patch, then make sure of these)
COMMON = {
    "VCO range": "8'",
    "Pulse / Saw / Sub / Noise": "0 / 0 / 0 / 0 (unless the take says otherwise)",
    "VCF env / mod / kybd": "0 / 0 / 0 (unless the take says otherwise)",
    "VCA": "GATE",
    "Envelope (A D S R)": "0 / 0 / 10 / 0",
    "Portamento, LFO, arp, sequencer, bend": "off / 0",
    "Velocity to VCF or VCA": "off",
    "TAL effects (chorus, delay, etc.)": "off",
}

TAKES = []   # (id, test, clip, {setting: value}, measurement value)


def _add(tid, test, clip, settings, value=None):
    TAKES.append({"id": tid, "test": test, "clip": clip, "settings": settings, "value": value})


_add("T0_open", "T0", "hold4", {"Saw": 10, "Cutoff": 10, "Res": 0}, None)
for s in range(11):                                                       # T1: singing pitch against cutoff
    _add(f"T1_cut{s:02d}", "T1", "hold4", {"Cutoff": s, "Res": 10}, float(s))
for r in range(700, 1001, 25):                                            # T2: where it starts to sing
    _add(f"T2_res{r:04d}", "T2", "hold4", {"Cutoff": 5, "Res": r / 100}, r / 100)   # id: resonance x 100
_add("T3_open", "T3", "hold20", {"Noise": 10, "Cutoff": 10, "Res": 0}, None)
for r in (0, 250, 500, 750, 900, 1000):                                   # T3: response against resonance
    _add(f"T3_res{r:04d}", "T3", "hold20", {"Noise": 10, "Cutoff": 5, "Res": r / 100}, r / 100)   # id: res x 100
for res in (0, 7):                                                        # T4: drive
    for lvl in (2, 5, 8, 10):
        _add(f"T4_r{res}_lvl{lvl:02d}", "T4", "saw_c2", {"Saw": lvl, "Cutoff": 5, "Res": res}, (res, lvl))
_add("T5_track", "T5", "track", {"Cutoff": 3, "Res": 10, "Kybd": 10}, None)   # T5: keyboard tracking

# Steady windows (s) the analysis reads, inside each clip's note
WINDOW = {"hold4": (2.0, 4.3), "hold20": (1.5, 20.3), "saw_c2": (2.0, 4.3)}
TRACK_WINDOW = (0.8, 1.9)            # after each tracking note's start
