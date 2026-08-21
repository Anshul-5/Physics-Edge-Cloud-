/**
 * @file homography.h
 * @brief Homography Projection & Ground-Plane Kinematics for PhysEdge-Cloud L1 Edge Gate
 *
 * Maps pixel-space optical flow displacements to metric ground-plane coordinates
 * (meters) using a 3x3 planar homography, then computes physical kinematics
 * (velocity, acceleration, jerk) via backward differences with a 3-tap EWMA
 * filter for noise suppression.
 *
 * All arithmetic uses fixed-point (Q16.16) to avoid floating-point on the MCU.
 * Optimized for ESP32-S3 Xtensa LX7 at 240 MHz.
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================
 * Fixed-point configuration (Q16.16)
 * ============================================================ */

/** Number of fractional bits in Q16.16 fixed-point representation */
#define HOM_FP_SHIFT  16

/** 1.0 in Q16.16 */
#define HOM_FP_ONE    ((int32_t)1 << HOM_FP_SHIFT)

/**
 * @brief Convert a floating-point scalar to Q16.16 fixed-point
 */
static inline int32_t hom_float_to_fp(float f)
{
    return (int32_t)(f * (float)HOM_FP_ONE);
}

/**
 * @brief Convert Q16.16 fixed-point back to floating-point
 */
static inline float hom_fp_to_float(int32_t fp)
{
    return (float)fp / (float)HOM_FP_ONE;
}

/**
 * @brief Fixed-point multiply (Q16.16 * Q16.16 -> Q16.16)
 */
static inline int32_t hom_fp_mul(int32_t a, int32_t b)
{
    return (int32_t)(((int64_t)a * b) >> HOM_FP_SHIFT);
}

/**
 * @brief Fixed-point divide (Q16.16 / Q16.16 -> Q16.16)
 *
 * Returns 0 on divide-by-(near)zero.
 */
static inline int32_t hom_fp_div(int32_t a, int32_t b)
{
    if (b == 0) return 0;
    int64_t q = ((int64_t)a << HOM_FP_SHIFT) / (int64_t)b;
    if (q > INT32_MAX) return INT32_MAX;
    if (q < INT32_MIN) return INT32_MIN;
    return (int32_t)q;
}

/* ============================================================
 * Types
 * ============================================================ */

/**
 * @brief Result of mapping a pixel to the metric ground plane
 */
typedef struct {
    int32_t x_m;   /**< Ground-plane X in meters (Q16.16) */
    int32_t y_m;   /**< Ground-plane Y in meters (Q16.16) */
    bool valid;    /**< False if projection denominator was degenerate */
} HomPoint;

/**
 * @brief Kinematic state for one tracked blob
 */
typedef struct {
    int32_t vx;    /**< Velocity X (m/s, Q16.16) */
    int32_t vy;    /**< Velocity Y (m/s, Q16.16) */
    int32_t ax;    /**< Acceleration X (m/s^2, Q16.16) */
    int32_t ay;    /**< Acceleration Y (m/s^2, Q16.16) */
    int32_t jx;    /**< Jerk X (m/s^3, Q16.16) */
    int32_t jy;    /**< Jerk Y (m/s^3, Q16.16) */
} Kinematics;

/**
 * @brief Homography projection context (opaque)
 */
typedef struct homography_ctx homography_ctx_t;

/* ============================================================
 * Public API
 * ============================================================ */

/**
 * @brief Initialize the homography projector
 *
 * @param h_norm 3x3 planar homography matrix (row-major, 9 elements).
 *               Values are in floating point and converted internally to Q16.16.
 * @return Context handle, or NULL on allocation failure
 */
homography_ctx_t *homography_init(const float h_norm[9]);

/**
 * @brief Project a pixel coordinate to metric ground-plane coordinates
 *
 * Projects (x, y) through the homography H:
 *   X_m = (h00 x + h01 y + h02) / (h20 x + h21 y + h22)
 *   Y_m = (h10 x + h11 y + h12) / (h20 x + h21 y + h22)
 *
 * @param ctx Projection context
 * @param x   Pixel X coordinate (column)
 * @param y   Pixel Y coordinate (row)
 * @param out Output metric point
 * @return true on success, false on invalid args
 */
bool homography_project(const homography_ctx_t *ctx,
                        int32_t x, int32_t y,
                        HomPoint *out);

/**
 * @brief Compute kinematics from two pixel observations and elapsed time
 *
 * Projects current and previous pixel positions to metric coordinates,
 * computes velocity by backward difference, then applies a 3-tap EWMA
 * filter to suppress noise before computing acceleration and jerk.
 *
 * @param ctx         Projection context
 * @param curr_x      Current pixel X
 * @param curr_y      Current pixel Y
 * @param prev_x      Previous pixel X
 * @param prev_y      Previous pixel Y
 * @param dt_us       Elapsed time between frames in microseconds
 * @param out         Output kinematics (vx, vy, ax, ay, jx, jy)
 * @param p_current   Optional: receives current projected metric point (may be NULL)
 * @return true on success, false if either projection was invalid
 */
bool homography_kinematics_update(homography_ctx_t *ctx,
                                  int32_t curr_x, int32_t curr_y,
                                  int32_t prev_x, int32_t prev_y,
                                  int64_t dt_us,
                                  Kinematics *out,
                                  int32_t *p_current_xm);

/**
 * @brief Compute the flow-confidence-weighted non-dimensionalized Motion Energy (E) score
 *
 * @param block_trackers Array of homography context pointers (one per macroblock)
 * @param dx_vals        Array of horizontal displacements (pixels)
 * @param dy_vals        Array of vertical displacements (pixels)
 * @param confidences    Array of confidence scores (0-255)
 * @param num_blocks     Number of macroblocks
 * @param dt_us          Time difference in microseconds
 * @param lambda1        Weight for velocity
 * @param lambda2        Weight for acceleration
 * @param lambda3        Weight for jerk
 * @param v_ref          Velocity normalization reference constant
 * @param a_ref          Acceleration normalization reference constant
 * @param j_ref          Jerk normalization reference constant
 * @param out_energy     Pointer to store output motion energy score
 * @return true on success, false on invalid inputs or math errors
 */
bool homography_compute_motion_energy(homography_ctx_t *block_trackers[],
                                      const int8_t *dx_vals,
                                      const int8_t *dy_vals,
                                      const uint8_t *confidences,
                                      uint32_t num_blocks,
                                      int64_t dt_us,
                                      float lambda1, float lambda2, float lambda3,
                                      float v_ref, float a_ref, float j_ref,
                                      float *out_energy);

/**
 * @brief Compute Time-to-Collision (TTC) proxy between two entities on the ground plane.
 *
 * @param x1_m       Entity 1 X (meters)
 * @param y1_m       Entity 1 Y (meters)
 * @param vx1_mps    Entity 1 velocity X (m/s)
 * @param vy1_mps    Entity 1 velocity Y (m/s)
 * @param x2_m       Entity 2 X (meters)
 * @param y2_m       Entity 2 Y (meters)
 * @param vx2_mps    Entity 2 velocity X (m/s)
 * @param vy2_mps    Entity 2 velocity Y (m/s)
 * @param out_ttc_sec Pointer to store computed TTC in seconds (999.0f if diverging/parallel)
 * @return true on valid inputs, false on null pointer
 */
bool homography_compute_ttc(float x1_m, float y1_m, float vx1_mps, float vy1_mps,
                            float x2_m, float y2_m, float vx2_mps, float vy2_mps,
                            float *out_ttc_sec);

/**
 * @brief Deinitialize and free the homography projector
 *
 * @param ctx Context handle
 */
void homography_deinit(homography_ctx_t *ctx);

#ifdef __cplusplus
}
#endif