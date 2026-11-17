/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 Kris Bishop */
/* A thin shared-library face on sh101_ref.h for Python (render_takes.py, fitting):
 *   cc -O2 -shared -fPIC -o build/libsh101ref.so sh101_ref_lib.c -lm */
#include <stdlib.h>
#include "sh101_ref.h"

void *sh101_new(const sh101_param_t *p, double fs)
{
    sh101_ref_t *f = malloc(sizeof *f);
    if (f) sh101_init(f, p, fs);
    return f;
}

void sh101_free(void *f) { free(f); }

void sh101_defaults_out(sh101_param_t *p) { sh101_defaults(p); }

int sh101_param_size(void) { return (int)sizeof(sh101_param_t); }

int sh101_latency_of(void *f) { return sh101_latency((sh101_ref_t *)f); }

/* n samples at a fixed cutoff (Hz) and loop gain k */
void sh101_run(void *h, const double *in, double *out, long n, double fc_hz, double k)
{
    sh101_ref_t *f = h;
    sh101_set(f, fc_hz, k);
    for (long i = 0; i < n; i++) out[i] = sh101_process(f, in[i]);
}

/* diagnostics: samples, mean iterations, worst iterations, worst residual */
void sh101_stats(void *h, double *s)
{
    sh101_ref_t *f = h;
    s[0] = (double)f->samples;
    s[1] = f->samples ? (double)f->iters / f->samples : 0;
    s[2] = (double)f->worst_iter;
    s[3] = f->worst_resid;
}
