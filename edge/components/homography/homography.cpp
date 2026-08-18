/**
 * @file homography.c
 * @brief Homography Projection & Ground-Plane Kinematics Implementation
 *
 * Converts pixel optical-flow displacements into physical metric kinematics
 * using a fixed-point (Q16.16) planar homography. Applies a 3-tap EWMA filter
 * to velocity before computing acceleration and jerk to suppress noise
 * amplification in the derivative chain.
 *
 * Performance target: <= 1.5ms for all moving blobs (single blob O(1)).
 */

#include "homography.h"

#include <stdlib.h>
#include <limits.h>

/** Denominator magnitude (Q16.16) below which a projection is degenerate.
 *  ~1e-6 in real terms as specified by the calibration guard. */
#define HOM_DENOM_MIN_FP 1

/** EWMA smoothing factor alpha = 1/3 (Q16.16), giving a 3-tap rolling feel */
#define HOM_EMA_ALPHA 21845

struct homography_ctx {
    /* 3x3 homography, row-major, Q16.16 */
    int32_t h[9];

    /* EWMA state for noise-smoothed kinematics */
    int32_t prev_vx;
    int32_t prev_vy;
    int32_t prev_ax;
    int32_t prev_ay;
    bool     has_prev;
};

homography_ctx_t *homography_init(const float h_norm[9])
{
    if (!h_norm) return NULL;

    homography_ctx_t *ctx = (homography_ctx_t *)calloc(1, sizeof(homography_ctx_t));
    if (!ctx) return NULL;

    for (int i = 0; i < 9; i++) {
        ctx->h[i] = hom_float_to_fp(h_norm[i]);
    }

    return ctx;
}

bool homography_project(const homography_ctx_t *ctx,
                        int32_t x, int32_t y,
                        HomPoint *out)
{
    if (!ctx || !out) return false;

    /* Numerator and denominator in Q16.16 (each term is h_fp * pixel). */
    int64_t n_x = (int64_t)ctx->h[0] * (int64_t)x
                + (int64_t)ctx->h[1] * (int64_t)y
                + (int64_t)ctx->h[2];
    int64_t n_y = (int64_t)ctx->h[3] * (int64_t)x
                + (int64_t)ctx->h[4] * (int64_t)y
                + (int64_t)ctx->h[5];
    int64_t d   = (int64_t)ctx->h[6] * (int64_t)x
                + (int64_t)ctx->h[7] * (int64_t)y
                + (int64_t)ctx->h[8];

    /* Reject degenerate denominators (near the horizon) */
    int64_t d_abs = d < 0 ? -d : d;
    if (d_abs < HOM_DENOM_MIN_FP) {
        out->x_m = 0;
        out->y_m = 0;
        out->valid = false;
        return true;
    }

    /* X_m = n_x / d, scaled to Q16.16 */
    out->x_m = (int32_t)((n_x << HOM_FP_SHIFT) / d);
    out->y_m = (int32_t)((n_y << HOM_FP_SHIFT) / d);
    out->valid = true;
    return true;
}

bool homography_kinematics_update(homography_ctx_t *ctx,
                                  int32_t curr_x, int32_t curr_y,
                                  int32_t prev_x, int32_t prev_y,
                                  int64_t dt_us,
                                  Kinematics *out,
                                  int32_t *p_current_xm)
{
    if (!ctx || !out || dt_us <= 0) return false;

    HomPoint curr, prev;
    homography_project(ctx, curr_x, curr_y, &curr);
    homography_project(ctx, prev_x, prev_y, &prev);

    if (!curr.valid || !prev.valid) return false;

    if (p_current_xm) *p_current_xm = curr.x_m;

    /* dt in seconds (Q16.16) */
    int32_t dt_fp = (int32_t)((dt_us << HOM_FP_SHIFT) / 1000000LL);
    if (dt_fp == 0) return false;

    /* Raw velocity = delta_metric / dt (Q16.16) */
    int32_t raw_vx = hom_fp_div(curr.x_m - prev.x_m, dt_fp);
    int32_t raw_vy = hom_fp_div(curr.y_m - prev.y_m, dt_fp);

    const int32_t ema = HOM_EMA_ALPHA;
    const int32_t ema_inv = HOM_FP_ONE - ema;

    int32_t sm_vx, sm_vy, sm_ax, sm_ay;

    if (ctx->has_prev) {
        /* v_smoothed = alpha * raw + (1-alpha) * prev_smoothed */
        sm_vx = hom_fp_mul(ema, raw_vx) + hom_fp_mul(ema_inv, ctx->prev_vx);
        sm_vy = hom_fp_mul(ema, raw_vy) + hom_fp_mul(ema_inv, ctx->prev_vy);

        /* Acceleration = smoothed velocity difference / dt */
        int32_t raw_ax = hom_fp_div(sm_vx - ctx->prev_vx, dt_fp);
        int32_t raw_ay = hom_fp_div(sm_vy - ctx->prev_vy, dt_fp);

        sm_ax = hom_fp_mul(ema, raw_ax) + hom_fp_mul(ema_inv, ctx->prev_ax);
        sm_ay = hom_fp_mul(ema, raw_ay) + hom_fp_mul(ema_inv, ctx->prev_ay);

        /* Jerk = acceleration difference / dt */
        out->jx = hom_fp_div(sm_ax - ctx->prev_ax, dt_fp);
        out->jy = hom_fp_div(sm_ay - ctx->prev_ay, dt_fp);
    } else {
        /* First observation: seed velocity, zero accel/jerk */
        sm_vx = raw_vx;
        sm_vy = raw_vy;
        sm_ax = 0;
        sm_ay = 0;
        out->jx = 0;
        out->jy = 0;
    }

    out->vx = sm_vx;
    out->vy = sm_vy;
    out->ax = sm_ax;
    out->ay = sm_ay;

    /* Commit state */
    ctx->prev_vx = sm_vx;
    ctx->prev_vy = sm_vy;
    ctx->prev_ax = sm_ax;
    ctx->prev_ay = sm_ay;
    ctx->has_prev = true;

    return true;
}

void homography_deinit(homography_ctx_t *ctx)
{
    if (ctx) free(ctx);
}