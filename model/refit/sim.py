"""The TAL takes simulated through the device module (sh101_vcf.h, 1x, as on the FM-1), timed as analyse.py reads them:
a note's window is 1.5 .. 3.8 s after it starts (hold4: note at 0.5 s, window 2.0 .. 4.3 s of the take)."""
import ctypes
from pathlib import Path
import numpy as np

import subprocess

FS = 44100
_SO, _SRC = Path(__file__).with_name("libshim.so"), Path(__file__).with_name("shim.c")
if not _SO.exists() or _SO.stat().st_mtime < max(_SRC.stat().st_mtime, (_SRC.parents[1] / "sh101_vcf.h").stat().st_mtime):
    subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-ffp-contract=off", "-Wno-unused-function", "-o", str(_SO), str(_SRC)], check=True)
L = ctypes.CDLL(str(_SO))
F = ctypes.POINTER(ctypes.c_float)
L.run.argtypes = [F, F, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
L.knob_cut.argtypes = [ctypes.c_float]
L.small_gain.restype = ctypes.c_float
G = {k: ctypes.c_float.in_dll(L, "g_" + k) for k in ("drive", "clip", "sharp", "fwd", "kmax", "curve", "noise")}
W0, W1, N = int(1.5 * FS), int(3.8 * FS), int(4.3 * FS)


def setp(**p):
    for k, v in p.items():
        G[k].value = v
    L.reinit()


def getp():
    return {k: v.value for k, v in G.items()}


def run(x, slider_cut, res_slider, seed=0x2545F491):
    x = np.ascontiguousarray(x, np.float32)
    y = np.zeros_like(x)
    L.run(x.ctypes.data_as(F), y.ctypes.data_as(F), len(x), L.knob_cut(12.7 * slider_cut), int(round(res_slider / 10 * 127 * 256)), seed)
    return y


_SAW = {}


def saw(f, n, a=1.0):
    if (f, n) not in _SAW:
        _SAW[(f, n)] = _saw(f, n)
    return (a * _SAW[(f, n)]).astype(np.float32)


def _saw(f, n, a=1.0):
    t = np.arange(n) / FS
    return (a * 2 / np.pi * sum(np.sin(2 * np.pi * f * h * t) / h * (-1) ** (h + 1) for h in range(1, int(20000 / f) + 1))).astype(np.float32)


def rms_db(y):
    return 20 * np.log10(np.sqrt(np.mean(np.square(y[W0:W1], dtype=np.float64))) + 1e-12)


_T0 = {}


def t0():
    key = tuple(sorted(getp().items()))
    if key not in _T0:
        _T0.clear()
        _T0[key] = rms_db(run(saw(130.81, N), 10, 0))
    return _T0[key]


def t2(res):           # singing level re the open saw (no source; the circuit noise starts it)
    return rms_db(run(np.zeros(N, np.float32), 5, res)) - t0()


def t1(cut=5, res=10):
    y = run(np.zeros(N, np.float32), cut, res)[W0:W1].astype(np.float64)
    sp = np.abs(np.fft.rfft(y * np.hanning(len(y)), 1 << 19)); fr = np.fft.rfftfreq(1 << 19, 1 / FS)
    i = np.argmax(sp[fr > 5]) + np.sum(fr <= 5); f0 = fr[i]
    h = [sp[np.argmin(abs(fr - k * f0))] for k in range(1, 6) if k * f0 < FS / 2]
    return f0, 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-12) - t0(), 100 * np.sqrt(np.sum(np.square(h[1:]))) / h[0]


def t4(level, res):    # a saw at C2 at the level through FREQ 5: what resonance res costs, dB
    x = saw(65.41, N, level / 10)
    return rms_db(run(x, 5, res)) - rms_db(run(x, 5, 0))
