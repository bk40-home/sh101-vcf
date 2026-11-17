/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 Kris Bishop */
/* =============================================================================
 * sh101_ref.h — SH-101 VCF reference model (host only, double precision)
 * =============================================================================
 *
 * PURPOSE
 *   The "truth" the FM-1 module is tested against: accuracy first, no CPU limits.
 *   Every sample the whole circuit is solved exactly (Newton on all unknowns
 *   together), at an oversampled rate, with linear-phase resampling. Nothing in
 *   here is meant to run on the FM-1.
 *
 * THE CIRCUIT (see MODEL.md for the sources of each statement)
 *   IR3109: four OTA stages, each wired as a buffered integrator with its output
 *   fed back to its own input divider, so each is a one-pole lowpass whose OTA
 *   saturates on the DIFFERENCE between its input and its output:
 *       C dy/dt = Iabc * tanh(a (x - y) / 2Vt)   ->   dy/dt = w * Vs * tanh((x - y) / Vs)
 *   with all voltages here in units of Vs (the stage's linear range), so
 *       dy_i/dt = w_i * tanh(x_i - y_i),   x_1 = filter input, x_i = y_(i-1).
 *   Resonance (SH-101, unlike the Juno): a transistor phase splitter (TR2) takes
 *   the 4th stage's output. Its inverted copy goes back to the input through the
 *   resonance pot, with a pair of clipping diodes to ground in that path; its
 *   non-inverted copy is ADDED TO THE OUTPUT, which is how the 101 compensates
 *   the passband loss (at the output, not the input).
 *
 *   Feedback, two placements of the diodes against the pot (which one the 101
 *   has is to be decided by the measurements, see MODEL.md):
 *     SH101_CLIP_BEFORE_POT:  v = D(y4),      u = x - k v
 *     SH101_CLIP_AFTER_POT:   v = D(k y4),    u = x - v     <- the 101 (service manual: RES pot, then TR26,
 *                                                               then the diodes D30/D31)
 *   and the output, SH101_FWD_WIPER: out = y4 (1 + f k)  <- the 101 (TR26's emitter, unclipped)
 *                   SH101_FWD_CLIPPED: out = y4 + f k v (before pot) / y4 + f v (after pot)
 *   D is the diode pair with its series resistance, solved exactly:
 *       v + c sinh(v / vd) = w      (w the voltage driving the series resistor)
 *   parametrised by the clip level and the knee's sharpness (MODEL.md).
 *
 * DISCRETISATION
 *   Trapezoidal (TPT), cutoff pre-warped per stage at the oversampled rate:
 *       y_i = s_i + g_i tanh(x_i - y_i),   g_i = tan(pi f_i / fs_os),
 *       then s_i <- 2 y_i - s_i.
 *   Unknowns per sample: y1..y4 and the diode voltage v. Newton on the 5x5
 *   system to |step| < 1e-13, from the previous sample's solution.
 *
 * UNITS
 *   Input: an oscillator at full level = 1.0. It enters the filter as
 *   x = drive * input (drive = Vs units per full-scale oscillator). The output
 *   is divided by drive again, so at k = 0 and small signals the passband gain
 *   is exactly 1.
 * ============================================================================= */
#ifndef SH101_REF_H
#define SH101_REF_H

#include <math.h>
#include <string.h>

enum { SH101_CLIP_BEFORE_POT = 0, SH101_CLIP_AFTER_POT = 1 };
enum { SH101_FWD_CLIPPED = 0, SH101_FWD_WIPER = 1 };   /* where the output's added copy is taken */

typedef struct {
    /* ---- circuit (MODEL.md: "parameters") ---- */
    double drive;          /* Vs units per full-scale oscillator into the filter */
    double cap[4];         /* relative stage capacitances (1 = nominal); pole i sits at fc / cap[i] */
    double fwd;            /* f: share of the phase splitter's forward copy added to the output */
    int fwd_from;          /* SH101_FWD_WIPER: out = y4 (1 + f k), the 101 (TR26's emitter, before the diodes);
                              SH101_FWD_CLIPPED: out = y4 + f * (the clipped feedback) */
    double clip;           /* diode pair: level at which it conducts (units of the node it sits on) */
    double clip_sharp;     /* knee: ln(2 * clip / c); ~11 for silicon diodes behind ~10k */
    int clip_place;        /* SH101_CLIP_BEFORE_POT or SH101_CLIP_AFTER_POT */
    double noise_floor;    /* rms of a noise added at the input (units), so resonance starts from silence */
    /* ---- panel maps (replaced by the T1 / T2 fits) ---- */
    double cut_hz0;        /* cutoff slider 0 -> Hz */
    double cut_oct;        /* octaves per cutoff slider unit */
    double kmax;           /* k at resonance slider 10 */
    double res_curve;      /* k = kmax * (res/10)^res_curve */
    double kybd_oct;       /* octaves of cutoff per octave of keyboard at KYBD 10, relative to MIDI 48 */
    /* ---- numerics ---- */
    int os;                /* oversampling factor (1, 2, 4, 8, 16) */
    double tol;            /* Newton step tolerance */
    int max_iter;
} sh101_param_t;

static inline void sh101_defaults(sh101_param_t *p)
{
    memset(p, 0, sizeof *p);
    /* Values from the SH-101 service manual's circuit diagram (MODEL.md, "From the schematic") */
    p->drive = 0.3;                                    /* estimate: source levels not on the schematic; fit (T4) */
    p->cap[0] = 1.0286;                                /* stage 1's input node also carries R113 15k: its pole sits 2.9% lower */
    p->cap[1] = p->cap[2] = p->cap[3] = 1.0;           /* C47/C48/C50/C51 all 240p */
    p->fwd = 0.2020;                                   /* out = y4 + TR26 emitter (R130 = R132 = 150k) = y4 (1 + k/4.951) */
    p->fwd_from = SH101_FWD_WIPER;
    p->clip = 0.346;                                   /* D30/D31 1S2473 behind R129 5.6k / R113 15k, in stage units */
    p->clip_sharp = 10.77;
    p->clip_place = SH101_CLIP_AFTER_POT;              /* VR18 (RES) feeds TR26; the diodes come after it */
    p->noise_floor = 1e-4;                             /* about -80 dB: an analog circuit's own noise */
    p->cut_hz0 = 10.0;
    p->cut_oct = log2(20000.0 / 10.0) / 10.0;
    p->kmax = 4.951;                                   /* TR26 gain 15k/10k x divider 15k/20.6k x injection 68k/15k */
    p->res_curve = 1.0;                                /* VR18 100k B (linear) used as a potentiometer */
    p->kybd_oct = 1.0;
    p->os = 8;
    p->tol = 1e-13;
    p->max_iter = 60;
}

/* ---------------------------------------------------------------------------------------- resampler
 * Linear-phase Kaiser-windowed sinc, passband to 0.45 fs, ~120 dB stop band. Polyphase both ways. */
#define SH101_FIR_PER_PHASE 96
#define SH101_OS_MAX 16
typedef struct {
    int os, n;                                          /* n = taps = SH101_FIR_PER_PHASE * os */
    double h[SH101_FIR_PER_PHASE * SH101_OS_MAX];
    double up[SH101_FIR_PER_PHASE];                     /* input history (base rate) */
    double dn[SH101_FIR_PER_PHASE * SH101_OS_MAX];      /* output history (oversampled) */
    int dpos;
} sh101_rs_t;

static double sh101_bessel_i0(double x)
{
    double s = 1, t = 1;
    for (int k = 1; k < 60; k++) { t *= (x / (2 * k)) * (x / (2 * k)); s += t; if (t < 1e-20 * s) break; }
    return s;
}

static void sh101_rs_init(sh101_rs_t *r, int os)
{
    memset(r, 0, sizeof *r);
    r->os = os;
    r->n = SH101_FIR_PER_PHASE * os;
    if (os == 1) { r->h[0] = 1; r->n = 1; return; }
    const double beta = 12.0, fc = 0.47 / os;           /* cutoff in cycles per oversampled sample */
    double sum = 0, m = (r->n - 1) / 2.0;
    for (int i = 0; i < r->n; i++) {
        double t = i - m, w = sh101_bessel_i0(beta * sqrt(1 - (t / m) * (t / m))) / sh101_bessel_i0(beta);
        r->h[i] = (t == 0 ? 2 * fc : sin(2 * M_PI * fc * t) / (M_PI * t)) * w;
        sum += r->h[i];
    }
    for (int i = 0; i < r->n; i++) r->h[i] /= sum;      /* unity DC gain */
}

/* one base-rate sample in -> os samples out (interpolated) */
static void sh101_rs_up(sh101_rs_t *r, double x, double *out)
{
    if (r->os == 1) { out[0] = x; return; }
    memmove(r->up + 1, r->up, (SH101_FIR_PER_PHASE - 1) * sizeof(double));
    r->up[0] = x;
    for (int ph = 0; ph < r->os; ph++) {
        double s = 0;
        for (int j = 0; j < SH101_FIR_PER_PHASE; j++) s += r->h[ph + j * r->os] * r->up[j];
        out[ph] = s * r->os;
    }
}

/* os oversampled samples in -> one base-rate sample out (filtered, decimated) */
static double sh101_rs_down(sh101_rs_t *r, const double *in)
{
    if (r->os == 1) return in[0];
    for (int i = 0; i < r->os; i++) {
        r->dpos = (r->dpos + 1) % r->n;
        r->dn[r->dpos] = in[i];
    }
    double s = 0;
    for (int j = 0, p = r->dpos; j < r->n; j++, p = (p ? p - 1 : r->n - 1)) s += r->h[j] * r->dn[p];
    return s;
}

/* ---------------------------------------------------------------------------------------- the filter */
typedef struct {
    sh101_param_t p;
    double fs;                /* base rate */
    double s[4];              /* TPT states (units) */
    double y[4], v;           /* last solution: the Newton start */
    double g[4];              /* per stage, oversampled */
    double k;
    double vd, c;             /* diode equation, from clip / clip_sharp */
    sh101_rs_t up, dn;
    unsigned rng;
    /* diagnostics */
    long samples, iters, worst_iter;
    double worst_resid;
} sh101_ref_t;

static void sh101_init(sh101_ref_t *f, const sh101_param_t *p, double fs)
{
    memset(f, 0, sizeof *f);
    f->p = *p;
    f->fs = fs;
    f->vd = p->clip / p->clip_sharp;
    f->c = 2 * p->clip * exp(-p->clip_sharp);
    f->rng = 0x9E3779B9u;
    sh101_rs_init(&f->up, p->os);
    sh101_rs_init(&f->dn, p->os);
}

/* cutoff (Hz of the poles at cap = 1) and loop gain k */
static void sh101_set(sh101_ref_t *f, double fc_hz, double k)
{
    double fso = f->fs * f->p.os;
    for (int i = 0; i < 4; i++) {
        double fi = fc_hz / f->p.cap[i];
        if (fi > 0.49 * fso) fi = 0.49 * fso;
        f->g[i] = tan(M_PI * fi / fso);
    }
    f->k = k;
}

static double sh101_gauss(sh101_ref_t *f)
{
    double a = 0;
    for (int i = 0; i < 12; i++) { f->rng = f->rng * 1664525u + 1013904223u; a += (f->rng >> 8) / 16777216.0; }
    return a - 6.0;
}

/* Solve one oversampled step for input x (units). Returns the output (units). */
static double sh101_step_os(sh101_ref_t *f, double x)
{
    const sh101_param_t *p = &f->p;
    double Y[5] = { f->y[0], f->y[1], f->y[2], f->y[3], f->v }, R[5], J[5][5];
    const double k = f->k, vd = f->vd, c = f->c;
    int it;
    for (it = 0; it < p->max_iter; it++) {
        double u = p->clip_place == SH101_CLIP_BEFORE_POT ? x - k * Y[4] : x - Y[4];
        double in[4] = { u, Y[0], Y[1], Y[2] };
        memset(J, 0, sizeof J);
        for (int i = 0; i < 4; i++) {
            double t = tanh(in[i] - Y[i]), d = 1 - t * t;
            R[i] = Y[i] - f->s[i] - f->g[i] * t;
            J[i][i] = 1 + f->g[i] * d;                          /* d/dy_i */
            if (i > 0) J[i][i - 1] = -f->g[i] * d;              /* d/dy_(i-1) through x_i */
            else J[0][4] = -f->g[0] * d * (p->clip_place == SH101_CLIP_BEFORE_POT ? -k : -1);   /* d/dv through u */
        }
        double w = p->clip_place == SH101_CLIP_BEFORE_POT ? Y[3] : k * Y[3];
        double sh = sinh(Y[4] / vd), ch = cosh(Y[4] / vd);
        R[4] = Y[4] + c * sh - w;
        J[4][4] = 1 + c * ch / vd;
        J[4][3] = p->clip_place == SH101_CLIP_BEFORE_POT ? -1 : -k;
        /* solve J d = -R (Gaussian elimination with partial pivoting) */
        double A[5][6];
        for (int i = 0; i < 5; i++) { for (int j = 0; j < 5; j++) A[i][j] = J[i][j]; A[i][5] = -R[i]; }
        for (int col = 0; col < 5; col++) {
            int pv = col;
            for (int r = col + 1; r < 5; r++) if (fabs(A[r][col]) > fabs(A[pv][col])) pv = r;
            if (pv != col) for (int j = 0; j < 6; j++) { double t = A[col][j]; A[col][j] = A[pv][j]; A[pv][j] = t; }
            for (int r = col + 1; r < 5; r++) {
                double m = A[r][col] / A[col][col];
                for (int j = col; j < 6; j++) A[r][j] -= m * A[col][j];
            }
        }
        double d[5], mx = 0;
        for (int i = 4; i >= 0; i--) {
            double s = A[i][5];
            for (int j = i + 1; j < 5; j++) s -= A[i][j] * d[j];
            d[i] = s / A[i][i];
        }
        for (int i = 0; i < 5; i++) {                           /* damped: no step larger than 1 unit */
            if (d[i] > 1) d[i] = 1;
            if (d[i] < -1) d[i] = -1;
            Y[i] += d[i];
            if (fabs(d[i]) > mx) mx = fabs(d[i]);
        }
        if (mx < p->tol) { it++; break; }
    }
    /* residual of the accepted solution (diagnostic) */
    {
        double u = p->clip_place == SH101_CLIP_BEFORE_POT ? x - k * Y[4] : x - Y[4];
        double in[4] = { u, Y[0], Y[1], Y[2] }, rr = 0;
        for (int i = 0; i < 4; i++) rr = fmax(rr, fabs(Y[i] - f->s[i] - f->g[i] * tanh(in[i] - Y[i])));
        double w = p->clip_place == SH101_CLIP_BEFORE_POT ? Y[3] : k * Y[3];
        rr = fmax(rr, fabs(Y[4] + c * sinh(Y[4] / vd) - w));
        if (rr > f->worst_resid) f->worst_resid = rr;
    }
    f->iters += it;
    f->samples++;
    if (it > f->worst_iter) f->worst_iter = it;
    for (int i = 0; i < 4; i++) { f->y[i] = Y[i]; f->s[i] = 2 * Y[i] - f->s[i]; }
    f->v = Y[4];
    if (p->fwd_from == SH101_FWD_WIPER)
        return Y[3] * (1 + p->fwd * k);
    return p->clip_place == SH101_CLIP_BEFORE_POT ? Y[3] + p->fwd * k * Y[4] : Y[3] + p->fwd * Y[4];
}

/* One base-rate sample: input in oscillator units -> output in oscillator units. */
static double sh101_process(sh101_ref_t *f, double in)
{
    double a[SH101_OS_MAX], b[SH101_OS_MAX];
    sh101_rs_up(&f->up, in * f->p.drive, a);
    for (int i = 0; i < f->p.os; i++)
        b[i] = sh101_step_os(f, a[i] + f->p.noise_floor * sh101_gauss(f));
    return sh101_rs_down(&f->dn, b) / f->p.drive;
}

/* group delay of the resampler pair, in base-rate samples (to align outputs with inputs) */
static int sh101_latency(const sh101_ref_t *f)
{
    return f->p.os == 1 ? 0 : (int)((f->up.n - 1) / f->p.os);
}

/* panel maps */
static double sh101_cut_hz(const sh101_param_t *p, double slider, double kybd, int note)
{
    return p->cut_hz0 * pow(2.0, p->cut_oct * slider + p->kybd_oct * (kybd / 10.0) * (note - 48) / 12.0);
}
static double sh101_k(const sh101_param_t *p, double res)
{
    return p->kmax * pow(res / 10.0, p->res_curve);
}

#endif /* SH101_REF_H */
