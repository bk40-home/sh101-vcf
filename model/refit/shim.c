/* the device module with its fitted values as variables (the refit drives them) */
#include <stdint.h>
float g_drive = 0.19918f, g_clip = 0.51447f, g_sharp = 8.7977f, g_fwd = 0.202f, g_kmax = 5.8657f, g_curve = 1.14896f,
      g_noise = 1.0e-4f;
#define SH101_DRIVE g_drive
#define SH101_CLIP g_clip
#define SH101_CLIP_SHARP g_sharp
#define SH101_FWD g_fwd
#define SH101_KMAX g_kmax
#define SH101_RES_CURVE g_curve
#define SH101_NOISE g_noise
#include "../../sh101_vcf.h"
void reinit(void) { sh101_init(); }
int knob_cut(float knob) { return sh101_knob_cut((int32_t)(knob * 65536.0f)); }
float small_gain(void) { return SH101_DTAB[0]; }
void run(const float *x, float *y, int n, int cut_q8, int res_q8, unsigned seed)
{
    sh101_coef_t c = {0}; sh101_state_t s;
    sh101_reset(&s, seed); sh101_coef(&c, cut_q8, res_q8);
    for (int i = 0; i < n; i++) y[i] = sh101_process(&c, &s, x[i]);
}
