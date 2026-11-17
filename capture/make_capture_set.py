#!/usr/bin/env python3
"""Build the whole capture as ONE Live track: every take back to back in the Arrangement, TAL-BassLine-101's
controls automated per take, so one export gives all of it (works in Live Lite: one track).

    python3 make_capture_set.py <your set with TAL configured>.als [out.als] [--fm1]

--fm1: also the FM-1 side of the A/B (fm1_track.py): the set's second MIDI track plays the same notes to the FM-1
(M-Vsynth2, FILTER TYPE 5) with the take settings as MIDI CC envelopes; see FM1.md.

The input set must have TAL-BassLine-101 on its first track with its controls exposed through Configure
(Cutoff, Resonance, Saw, Noise, Keyboard, ... as in clean.als). Writes out.als and out.timeline.json
(where each take starts in the export); split_takes.py uses the timeline to cut the export into takes.
"""
import copy
import gzip
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from takes import BEAT, BPM, CLIPS, TAKES

GAP_BEATS = 4                 # 2 s between takes: resonance off, sources off, so a singing filter dies away
KICK_BEATS = 0.2              # a 0.1 s touch of noise at each note-on of the singing takes (starts the oscillation)
KICK_NOISE = 0.03

# Panel controls: take setting name -> TAL parameter name (as Live lists it after Configure)
CONTROL = {"Cutoff": "Cutoff", "Res": "Resonance", "Saw": "Saw", "Noise": "Noise", "Kybd": "Keyboard"}

# Everything held fixed for the whole capture (TAL's normalised 0..1 values). The VCA is made a gate whichever
# way its switch reads: attack 0, sustain full, release 0.
FIXED = {
    "Pulse": 0.0, "Sub Osc": 0.0, "Envelope": 0.0, "Modulation": 0.0,
    "Adsr Attack": 0.0, "Adsr Decay": 0.5, "Adsr Sustain": 1.0, "Adsr Release": 0.0,
    "Dco LFO": 0.0, "Porta Amount": 0.0, "Bender Dco": 0.0, "Bender Filter": 0.0, "Bender Mod": 0.0,
    "Vel Envelope": 0.0, "Vel Volume": 0.0, "Distortion": 0.0,
    "Dco Range": 0.3, "Octave": 0.6, "Fine Tune": 0.5,       # TAL's default patch: 8', no transpose, in tune
    "Volume": 0.5,
}
DEFAULT = {"Cutoff": 10, "Res": 0, "Saw": 0, "Noise": 0, "Kybd": 0}   # panel units (0..10) between takes
SINGING = ("T1", "T2", "T5")


def plugin_targets(track):
    """TAL parameter name -> (ParameterId, AutomationTarget Id) for every exposed control."""
    dev = next(d for d in track.iter() if d.tag.endswith("PluginDevice"))
    out = {}
    for p in dev.find("ParameterList"):
        pid = p.find("ParameterId").get("Value")
        if pid == "-1":
            continue
        name = p.find("ParameterName").get("Value")
        out.setdefault(name, (pid, p.find("ParameterValue/AutomationTarget").get("Id")))
    return out


def env_xml(eid, target, events):
    e = ET.Element("AutomationEnvelope", Id=str(eid))
    ET.SubElement(ET.SubElement(e, "EnvelopeTarget"), "PointeeId", Value=target)
    a = ET.SubElement(e, "Automation")
    ev = ET.SubElement(a, "Events")
    ET.SubElement(ev, "FloatEvent", Id="0", Time="-63072000", Value=f"{events[0][1]:.10g}")
    for i, (t, v) in enumerate(events, 1):
        ET.SubElement(ev, "FloatEvent", Id=str(i), Time=f"{t:.10g}", Value=f"{v:.10g}")
    tv = ET.SubElement(a, "AutomationTransformViewState")
    ET.SubElement(tv, "IsTransformPending", Value="false")
    ET.SubElement(tv, "TimeAndValueTransforms")
    return e


def steps(segments):
    """[(start_beat, value)] -> events holding each value until the next start (vertical steps)."""
    ev = []
    for i, (t, v) in enumerate(segments):
        if i and v != segments[i - 1][1]:
            ev.append((t, segments[i - 1][1]))
        if not ev or ev[-1][1] != v or i == 0:
            ev.append((t, v))
    return ev


def main(src, dst):
    root = ET.fromstring(gzip.open(src).read())
    ls = root.find("LiveSet")
    tempo = ls.find("MainTrack/DeviceChain/Mixer/Tempo/Manual").get("Value")
    if abs(float(tempo) - BPM) > 1e-6:
        sys.exit(f"the set's tempo is {tempo}; set it to {BPM:g} first")
    track = ls.find("Tracks")[0]
    tg = plugin_targets(track)
    need = set(CONTROL.values()) | set(FIXED)
    missing = sorted(n for n in need if n not in tg)
    if missing:
        sys.exit("not exposed in the set (Configure them in Live first): " + ", ".join(missing))

    # ---- the timeline: [gap][take] per take ----
    t = 0.0
    timeline, notes, ctl, starts = [], [], {k: [] for k in CONTROL}, []
    noise_kicks = []
    for tk in TAKES:
        for k in CONTROL:                                            # the gap: everything back to rest
            ctl[k].append((t, DEFAULT[k] / 10))
        t += GAP_BEATS
        start = t
        for k in CONTROL:
            ctl[k].append((t, tk["settings"].get(k, 0) / 10))
        clip = CLIPS[tk["clip"]]
        for note, nb, length in clip["notes"]:
            notes.append((note, start + nb, length))
            if tk["test"] in SINGING:
                noise_kicks.append((start + nb, start + nb + KICK_BEATS, tk["settings"].get("Noise", 0) / 10))
        timeline.append({"id": tk["id"], "start_s": start * BEAT, "beats": clip["beats"]})
        starts.append((tk, start))
        t += clip["beats"]
    end = t + GAP_BEATS
    for k in CONTROL:
        ctl[k].append((end - GAP_BEATS, DEFAULT[k] / 10))

    # the noise kicks ride on the Noise control
    ns = []
    for k_t, v in ctl["Noise"]:
        ns.append((k_t, v))
    for a, b, base in noise_kicks:
        ns.append((a, KICK_NOISE))
        ns.append((b, base))
    ns.sort(key=lambda e: e[0])
    ctl["Noise"] = ns

    # ---- automation ----
    envs = track.find("AutomationEnvelopes/Envelopes")
    for e in list(envs):
        envs.remove(e)
    eid = 0
    for k, segs in ctl.items():
        envs.append(env_xml(eid, tg[CONTROL[k]][1], steps(segs)))
        eid += 1
    for name, v in FIXED.items():
        envs.append(env_xml(eid, tg[name][1], [(0.0, v)]))
        eid += 1

    # ---- one arrangement clip with every note ----
    tpl = ET.fromstring(Path(__file__).with_name("clip_template.xml").read_text())
    clip = copy.deepcopy(tpl)
    clip.set("Id", "0")
    clip.set("Time", "0")
    clip.find("CurrentStart").set("Value", "0")
    clip.find("CurrentEnd").set("Value", f"{end:g}")
    lp = clip.find("Loop")
    for tag in ("LoopEnd", "OutMarker", "HiddenLoopEnd"):
        lp.find(tag).set("Value", f"{end:g}")
    lp.find("LoopOn").set("Value", "false")
    clip.find("Name").set("Value", "SH-101 capture")
    kts = clip.find("Notes/KeyTracks")
    for k in list(kts):
        kts.remove(k)
    nid = 1
    for i, key in enumerate(sorted({n[0] for n in notes})):
        kt = ET.SubElement(kts, "KeyTrack", Id=str(i))
        ns_ = ET.SubElement(kt, "Notes")
        for note, nb, length in notes:
            if note == key:
                ET.SubElement(ns_, "MidiNoteEvent", Time=f"{nb:g}", Duration=f"{length:g}", Velocity="100",
                              OffVelocity="0", NoteId=str(nid))
                nid += 1
        ET.SubElement(kt, "MidiKey", Value=str(key))
    clip.find("Notes/NoteIdGenerator/NextId").set("Value", str(nid))
    arr = track.find("DeviceChain/MainSequencer/ClipTimeable/ArrangerAutomation/Events")
    for c in list(arr):
        arr.remove(c)
    arr.append(clip)

    fm1_actual = None
    if FM1:                                   # the FM-1 side: the set's second MIDI track
        from fm1_track import fm1_clip
        mtr = [t_ for t_ in ls.find("Tracks") if t_.tag == "MidiTrack"]
        if len(mtr) < 2:
            sys.exit("--fm1: the set needs a second MIDI track (empty) for the FM-1")
        ft = mtr[1]
        mc = {int(c.tag.split(".")[1]): c.get("Id") for c in ft.find("DeviceChain/MainSequencer/MidiControllers")}
        fclip, fm1_actual = fm1_clip(clip, mc, starts, GAP_BEATS)
        fclip.set("Id", "1")
        farr = ft.find("DeviceChain/MainSequencer/ClipTimeable/ArrangerAutomation/Events")
        for c in list(farr):
            farr.remove(c)
        farr.append(fclip)
        ft.find("Name/EffectiveName").set("Value", "FM-1 SH101")
        un = ft.find("Name/UserName")
        if un is not None:
            un.set("Value", "FM-1 SH101")

    data = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")
    Path(dst).write_bytes(gzip.compress(data))
    bars = end / 4
    tl = {"bpm": BPM, "total_s": end * BEAT, "render_bars": int(-(-bars // 1)), "takes": timeline}
    if fm1_actual:
        tl["fm1"] = fm1_actual
    Path(dst).with_suffix(".timeline.json").write_text(json.dumps(tl, indent=1))
    print(f"{dst}: {len(TAKES)} takes, {len(notes)} notes, {eid} automation lanes, "
          f"{end * BEAT:.0f} s = {bars:.1f} bars (render {tl['render_bars']} bars from 1.1.1)")


FM1 = False

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--fm1"]
    FM1 = "--fm1" in sys.argv
    if not args:
        sys.exit(__doc__)
    main(args[0], args[1] if len(args) > 1 else ("sh101_ab.als" if FM1 else "sh101_capture.als"))
