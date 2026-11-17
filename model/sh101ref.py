"""Python face of the SH-101 reference model (sh101_ref.h via build/libsh101ref.so).

    from sh101ref import Model, params
    p = params(kmax=4.6, fwd=0.4)            # defaults with overrides
    m = Model(p, fs=44100)
    y = m.run(x, fc_hz=1000.0, k=3.0)        # numpy in, numpy out; state carries across calls
"""
import ctypes
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LIB = HERE / "build" / "libsh101ref.so"


class Param(ctypes.Structure):
    _fields_ = [("drive", ctypes.c_double), ("cap", ctypes.c_double * 4), ("fwd", ctypes.c_double), ("fwd_from", ctypes.c_int),
                ("clip", ctypes.c_double), ("clip_sharp", ctypes.c_double), ("clip_place", ctypes.c_int),
                ("noise_floor", ctypes.c_double), ("cut_hz0", ctypes.c_double), ("cut_oct", ctypes.c_double),
                ("kmax", ctypes.c_double), ("res_curve", ctypes.c_double), ("kybd_oct", ctypes.c_double),
                ("os", ctypes.c_int), ("tol", ctypes.c_double), ("max_iter", ctypes.c_int)]


def _lib():
    src = HERE / "sh101_ref_lib.c"
    if not LIB.exists() or LIB.stat().st_mtime < max(src.stat().st_mtime, (HERE / "sh101_ref.h").stat().st_mtime):
        LIB.parent.mkdir(exist_ok=True)
        subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-o", str(LIB), str(src), "-lm"], check=True)
    lib = ctypes.CDLL(str(LIB))
    lib.sh101_new.restype = ctypes.c_void_p
    lib.sh101_new.argtypes = [ctypes.POINTER(Param), ctypes.c_double]
    lib.sh101_free.argtypes = [ctypes.c_void_p]
    lib.sh101_latency_of.argtypes = [ctypes.c_void_p]
    lib.sh101_run.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
                              ctypes.c_long, ctypes.c_double, ctypes.c_double]
    lib.sh101_stats.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double)]
    assert lib.sh101_param_size() == ctypes.sizeof(Param), "Param layout differs from sh101_param_t"
    return lib


_L = _lib()


def params(**over):
    p = Param()
    _L.sh101_defaults_out(ctypes.byref(p))
    for k, v in over.items():
        if k == "cap":
            for i in range(4):
                p.cap[i] = v[i]
        else:
            setattr(p, k, v)
    return p


def as_dict(p):
    return {n: (list(getattr(p, n)) if n == "cap" else getattr(p, n)) for n, _ in Param._fields_}


class Model:
    def __init__(self, p, fs=44100.0):
        self.p = p
        self.h = _L.sh101_new(ctypes.byref(p), fs)

    def __del__(self):
        if getattr(self, "h", None):
            _L.sh101_free(self.h)

    @property
    def latency(self):
        return _L.sh101_latency_of(self.h)

    def run(self, x, fc_hz, k):
        x = np.ascontiguousarray(x, np.float64)
        y = np.empty_like(x)
        dp = ctypes.POINTER(ctypes.c_double)
        _L.sh101_run(self.h, x.ctypes.data_as(dp), y.ctypes.data_as(dp), len(x), float(fc_hz), float(k))
        return y

    def stats(self):
        s = (ctypes.c_double * 4)()
        _L.sh101_stats(self.h, s)
        return {"samples": s[0], "mean_iter": s[1], "worst_iter": s[2], "worst_resid": s[3]}
