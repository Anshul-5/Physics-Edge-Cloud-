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
#include <math.h>

/** Denominator magnitude (Q16.16) below which a projection is degenerate.
 *  655 in Q16.16 == 0.01 in real terms. */
#define HOM_DENOM_MIN_FP 655

/** EWMA smoothing factor alpha = 1/3 (Q16.16), giving a 3-tap rolling feel */
#define HOM_EMA_ALPHA 21845

/** Macroblock grid dimensions for 160x120 frame */
#define HOM_GRID_COLS      10
#define HOM_GRID_ROWS      7
#define HOM_MB_SIZE        16
#define HOM_MAX_BLOCKS     (HOM_GRID_COLS * HOM_GRID_ROWS) /* 70 */

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

    /* X_m = n_x / d, scaled to Q16.16 with saturation / overflow guard */
    int64_t scaled_nx = n_x * (1LL << HOM_FP_SHIFT);
    int64_t scaled_ny = n_y * (1LL << HOM_FP_SHIFT);

    int64_t q_x = scaled_nx / d;
    int64_t q_y = scaled_ny / d;

    if (q_x > INT32_MAX || q_x < INT32_MIN || q_y > INT32_MAX || q_y < INT32_MIN) {
        out->x_m = 0;
        out->y_m = 0;
        out->valid = false;
        return true;
    }

    out->x_m = (int32_t)q_x;
    out->y_m = (int32_t)q_y;
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
    if (!homography_project(ctx, curr_x, curr_y, &curr) ||
        !homography_project(ctx, prev_x, prev_y, &prev)) {
        return false;
    }

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

bool homography_compute_motion_energy(homography_ctx_t *block_trackers[],
                                      const int8_t *dx_vals,
                                      const int8_t *dy_vals,
                                      const uint8_t *confidences,
                                      uint32_t num_blocks,
                                      int64_t dt_us,
                                      float lambda1, float lambda2, float lambda3,
                                      float v_ref, float a_ref, float j_ref,
                                      float *out_energy)
{
    if (!block_trackers || !dx_vals || !dy_vals || !confidences || !out_energy ||
        dt_us <= 0 || num_blocks == 0 || num_blocks > HOM_MAX_BLOCKS) {
        return false;
    }
    
    if (!isfinite(lambda1) || !isfinite(lambda2) || !isfinite(lambda3) ||
        lambda1 < 0.0f || lambda2 < 0.0f || lambda3 < 0.0f) {
        return false;
    }

    // Check references to prevent division by zero or negative/non-finite scales
    if (!isfinite(v_ref) || !isfinite(a_ref) || !isfinite(j_ref) ||
        v_ref <= 0.0f || a_ref <= 0.0f || j_ref <= 0.0f) {
        return false;
    }

    float numerator = 0.0f;
    float denominator = 0.0f;

    for (uint32_t i = 0; i < num_blocks; i++) {
        if (!block_trackers[i]) {
            continue;
        }
        uint8_t w = confidences[i];
        if (w == 0) {
            continue; // Skip textureless/low confidence blocks
        }

        // Calculate block center (current coordinates)
        int32_t col = (int32_t)(i % HOM_GRID_COLS);
        int32_t row = (int32_t)(i / HOM_GRID_COLS);
        
        int32_t curr_x = col * HOM_MB_SIZE + HOM_MB_SIZE / 2;
        int32_t curr_y = row * HOM_MB_SIZE + HOM_MB_SIZE / 2;
        
        // Previous position based on optical flow displacement
        int32_t prev_x = curr_x - dx_vals[i];
        int32_t prev_y = curr_y - dy_vals[i];

        Kinematics kin;
        bool valid = homography_kinematics_update(block_trackers[i], curr_x, curr_y, prev_x, prev_y, dt_us, &kin, NULL);
        if (!valid) {
            continue; // Skip invalid projections
        }

        // Convert Q16.16 fixed-point metrics back to floats
        float vx = hom_fp_to_float(kin.vx);
        float vy = hom_fp_to_float(kin.vy);
        float ax = hom_fp_to_float(kin.ax);
        float ay = hom_fp_to_float(kin.ay);
        float jx = hom_fp_to_float(kin.jx);
        float jy = hom_fp_to_float(kin.jy);

        // Check for NaN and Inf from calculations
        if (isnan(vx) || isinf(vx) || isnan(vy) || isinf(vy) ||
            isnan(ax) || isinf(ax) || isnan(ay) || isinf(ay) ||
            isnan(jx) || isinf(jx) || isnan(jy) || isinf(jy)) {
            continue;
        }

        float v_norm_sq = vx * vx + vy * vy;
        float a_norm_sq = ax * ax + ay * ay;
        float j_norm_sq = jx * jx + jy * jy;

        // Non-dimensionalized score term for block i
        float term = lambda1 * (v_norm_sq / (v_ref * v_ref)) +
                     lambda2 * (a_norm_sq / (a_ref * a_ref)) +
                     lambda3 * (j_norm_sq / (j_ref * j_ref));

        // Safeguard against NaN/Inf terms
        if (isnan(term) || isinf(term)) {
            continue;
        }

        numerator += (float)w * term;
        denominator += (float)w;
    }

    // Guard against division by zero (e.g. if all confidences are zero)
    if (denominator <= 0.0f) {
        *out_energy = 0.0f;
    } else {
        *out_energy = numerator / denominator;
    }

    return true;
}

bool homography_compute_ttc(float x1_m, float y1_m, float vx1_mps, float vy1_mps,
                            float x2_m, float y2_m, float vx2_mps, float vy2_mps,
                            float *out_ttc_sec)
{
    if (!out_ttc_sec) {
        return false;
    }

    if (isnan(x1_m) || isinf(x1_m) || isnan(y1_m) || isinf(y1_m) ||
        isnan(vx1_mps) || isinf(vx1_mps) || isnan(vy1_mps) || isinf(vy1_mps) ||
        isnan(x2_m) || isinf(x2_m) || isnan(y2_m) || isinf(y2_m) ||
        isnan(vx2_mps) || isinf(vx2_mps) || isnan(vy2_mps) || isinf(vy2_mps)) {
        *out_ttc_sec = 999.0f;
        return false;
    }

    float rx = x1_m - x2_m;
    float ry = y1_m - y2_m;
    float dist = sqrtf(rx * rx + ry * ry);

    if (dist < 1e-4f) {
        *out_ttc_sec = 0.0f;
        return true;
    }

    float r_vx = vx1_mps - vx2_mps;
    float r_vy = vy1_mps - vy2_mps;

    float convergence_speed = -(rx * r_vx + ry * r_vy) / dist;

    // Division-by-zero & divergence guard:
    // If convergence speed <= epsilon (diverging or parallel), TTC is safely clamped to 999.0f
    if (convergence_speed <= 1e-4f) {
        *out_ttc_sec = 999.0f;
    } else {
        *out_ttc_sec = dist / convergence_speed;
    }

    return true;
}

void homography_deinit(homography_ctx_t *ctx)
{
    free(ctx);
}