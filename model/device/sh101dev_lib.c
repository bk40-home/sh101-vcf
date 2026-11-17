/* host shim: the device module obv_sh101.h as a shared library (float, as on the FM-1) */
#include <stdint.h>
#include "sh101_vcf.h"
static int inited;
void dev_run(const double *in, double *out, int n, int cut_q8, int res_q8, unsigned seed, int ctl)
{
    sh101_coef_t c; sh101_state_t s;
    if (!inited) { sh101_init(); inited = 1; }
    sh101_reset(&s, seed);
    sh101_coef(&c, cut_q8, res_q8);
    for (int i = 0; i < n; i++) {
        double v = in[i] * 65536.0;
        if (v > 2e9) v = 2e9;
        if (v < -2e9) v = -2e9;
        out[i] = sh101_step(&c, &s, (int32_t)v) / 65536.0;
    }
}
float dev_k(int res_q8) { sh101_coef_t c; if (!inited) { sh101_init(); inited = 1; } sh101_coef(&c, 60 << 8, res_q8); return c.k; }
float dev_g(int cut_q8, int i) { sh101_coef_t c; if (!inited) { sh101_init(); inited = 1; } sh101_coef(&c, cut_q8, 0); return c.G[i]; }
float dev_diode(float w) { if (!inited) { sh101_init(); inited = 1; } return sh101_diode_v(w) / (w ? w : 1); }
