#!/usr/bin/env python3
"""The FM-1 side of the A/B: M-Vsynth2 FILTER TYPE 5 (SH101) playing the same 41 takes as TAL-BassLine-101.

make_capture_set.py --fm1 calls fm1_clip(): the same notes as TAL's clip, on the set's second MIDI track, with the
take's settings sent as MIDI CC (clip envelopes). In Live: that track's MIDI To = the FM-1; an audio track records the
FM-1's USB audio. The FM-1 starts from its INIT patch; everything else is set by CC at the clip's start.

Mapping, TAL panel (0..10) -> M-Vsynth2 type 5:
  FREQ   knob = 12.7 x slider (type 5's FREQ is the SH-101 slider: linear in the knob, exponential in Hz)
  RES    knob = 127 sqrt(slider / 10) (type 5's RES taper 2.0; rounded, so the real slider is in the timeline)
  KYBD   KBDTRK 95 (1.0009 octaves an octave on type 5's scale) for 10, 0 for 0
  sources (Synth1 has no oscillator level, and always an oscillator):
    saw    OSC1 SAW; level L by MIX = 127 (1 - L/10) against OSC2 TRI parked at note 117 (~6.6 kHz: the filter, near
           270 Hz in T4, all but removes it)
    noise  MIX 127, OSC2 NOISE
    none   MIX 127, OSC2 SAW with TRACK, PITCH +60 and KEY SHIFT +24: above note 127 the oscillator is muted, so the
           filter starts from its own circuit noise (as the 101). C1 and C2 (T5's two lowest notes) stay below 127.
"""
import xml.etree.ElementTree as ET

from takes import CLIPS, TAKES

CC_OFFSET = 2            # Live's MIDI Ctrl list: Pitch Bend, Channel Pressure, then CC 0..127 (check: see FM1.md)

# set once at the clip's start (the INIT patch otherwise): CC -> value
FIXED = {
    49: 127,             # FILTER TYPE 5, SH101
    17: 42,              # OSC1 SHAPE SAW
    52: 64,              # FILTER env AMOUNT 0
    41: 0, 43: 127,      # FILTER ENV attack 0, SUSTAIN full: Synth1's cutoff sits up to 2.1 knobs below FREQ while
                         # the filter env is below 1, even at AMOUNT 0 (INIT's SUSTAIN 21: ~2 semitones flat on type 5)
    54: 0, 55: 0,        # SATURATION 0, VEL SW off
    45: 0, 46: 64, 47: 127, 48: 0,   # AMP ENV: attack 0, sustain full, release 0 (a gate, as TAL's)
    56: 64, 57: 0,       # GAIN (INIT), AMP VEL 0
    4: 0, 12: 0,         # LFO1, LFO2 DEPTH 0
    60: 0, 61: 0, 59: 0,             # DELAY, CHORUS, EFFECT off
    91: 0, 89: 0, 88: 0, 35: 0,      # UNISON off, PORTA 0, POLY, MOD ENV off
    19: 0, 21: 0, 18: 0, 31: 0, 30: 0, 34: 64,   # FM 0, SUB 0, DETUNE 0, RING off, SYNC off, TUNE 0
}
SRC = {   # per source: CC -> value
    "none":  {28: 127, 24: 0, 27: 127, 25: 127, 33: 127},
    "noise": {28: 127, 24: 127, 27: 0, 25: 64, 33: 64},
    "saw":   {24: 85, 27: 0, 25: 127, 33: 64},          # + MIX by level
}


def slider_to(tk):
    s = tk["settings"]
    cut, res, kyb = s.get("Cutoff", 0), s.get("Res", 0), s.get("Kybd", 0)
    if s.get("Saw", 0):
        src = {**SRC["saw"], 28: round(127 * (1 - s["Saw"] / 10))}
    elif s.get("Noise", 0):
        src = dict(SRC["noise"])
    else:
        src = dict(SRC["none"])
    rk = round(127 * (res / 10) ** 0.5)
    cc = {**src, 50: round(12.7 * cut), 51: rk, 53: 95 if kyb else 0}
    actual = {"cut": cc[50] / 12.7, "res": 10 * (rk / 127) ** 2, "kybd_knob": cc[53], "source": "saw" if s.get("Saw", 0)
              else "noise" if s.get("Noise", 0) else "none", "mix": cc[28]}
    return cc, actual


REST, _ = slider_to({"settings": {"Cutoff": 10, "Res": 0}})     # between takes: silent, open, no resonance


def fm1_clip(tal_clip, mc_targets, take_starts, gap_beats):
    """A copy of TAL's arrangement clip with the FM-1's CC envelopes. take_starts: [(take, start_beat)].
    mc_targets: the MIDI track's ControllerTargets.N ids (N = CC + CC_OFFSET). Returns (clip, per-take actual values)."""
    import copy
    clip = copy.deepcopy(tal_clip)
    clip.find("Name").set("Value", "FM-1 SH101 capture")
    lanes = {}
    for cc, v in FIXED.items():
        lanes.setdefault(cc, []).append((0.0, v))
    actual = {}
    for tk, start in take_starts:
        for cc, v in REST.items():
            lanes.setdefault(cc, []).append((start - gap_beats, v))
        cc_t, act = slider_to(tk)
        actual[tk["id"]] = act
        for cc, v in cc_t.items():
            lanes.setdefault(cc, []).append((start, v))
    env = clip.find("Envelopes/Envelopes")
    for e in list(env):
        env.remove(e)
    for i, (cc, ev) in enumerate(sorted(lanes.items())):
        ce = ET.SubElement(env, "ClipEnvelope", Id=str(i))
        ET.SubElement(ET.SubElement(ce, "EnvelopeTarget"), "PointeeId", Value=mc_targets[cc + CC_OFFSET])
        a = ET.SubElement(ce, "Automation")
        evs = ET.SubElement(a, "Events")
        pts, last = [], None
        for t, v in sorted(ev, key=lambda x: x[0]):
            if last is None:
                pts.append((t, v))
            elif v != last:
                pts.append((t, last))          # a vertical step: hold the old value up to t, then jump
                pts.append((t, v))
            last = v
        ET.SubElement(evs, "FloatEvent", Id="0", Time="-63072000", Value=f"{pts[0][1]:g}")
        for j, (t, v) in enumerate(pts, 1):
            ET.SubElement(evs, "FloatEvent", Id=str(j), Time=f"{t:.10g}", Value=f"{v:g}")
        tv = ET.SubElement(a, "AutomationTransformViewState")
        ET.SubElement(tv, "IsTransformPending", Value="false")
        ET.SubElement(tv, "TimeAndValueTransforms")
    return clip, actual
