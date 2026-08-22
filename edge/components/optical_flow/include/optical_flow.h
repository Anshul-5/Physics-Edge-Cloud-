/**
 * @file optical_flow.h
 * @brief Block-Based SAD Optical Flow for PhysEdge-Cloud L1 Edge Gate
 *
 * Computes dense motion vectors using Sum of Absolute Differences (SAD)
 * block matching on a 16x16 macroblock grid. Optimized for ESP32-S3
 * with SIMD intrinsics.
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Frame dimensions expected by the optical flow module */
#define OF_WIDTH       160
#define OF_HEIGHT      120

/** Macroblock size (16x16 pixels) */
#define MB_SIZE        16

/** Search range: +/-8 pixels in each direction */
#define SEARCH_RANGE   8

/** Grid dimensions: 160/16 = 10, 120/16 = 7.5 -> 7 full blocks */
#define GRID_COLS      (OF_WIDTH / MB_SIZE)    /* 10 */
#define GRID_ROWS      (OF_HEIGHT / MB_SIZE)   /* 7 */
#define NUM_BLOCKS     (GRID_COLS * GRID_ROWS) /* 70 */

/** Confidence threshold: spatial variance below this = textureless */
#define VARIANCE_THRESHOLD  15.0f

#ifndef MOTION_VECTOR_STRUCT_DEFINED
#define MOTION_VECTOR_STRUCT_DEFINED
/**
 * @brief 2D motion vector with confidence
 */
typedef struct {
    int8_t dx;          /**< Horizontal displacement (pixels) */
    int8_t dy;          /**< Vertical displacement (pixels) */
    uint8_t confidence; /**< 0-255, 0=textureless/low confidence */
} MotionVector;
#endif

/**
 * @brief Optical flow result grid
 */
typedef struct {
    MotionVector vectors[NUM_BLOCKS];  /**< Motion vector per macroblock */
    uint32_t num_blocks;               /**< Number of valid blocks computed */
} FlowResult;

/**
 * @brief Optical flow context (opaque)
 */
typedef struct optical_flow_ctx optical_flow_ctx_t;

/**
 * @brief Initialize the optical flow processor
 *
 * @return Context handle, or NULL on failure
 */
optical_flow_ctx_t *optical_flow_init(void);

/**
 * @brief Compute optical flow between two consecutive frames
 *
 * Performs block-based SAD matching on a 16x16 macroblock grid.
 * Each block searches a +/-8 pixel window in the previous frame
 * to find the displacement vector minimizing SAD.
 *
 * @param ctx        Optical flow context
 * @param frame_curr Current frame (160x120 grayscale)
 * @param frame_prev Previous frame (160x120 grayscale)
 * @param result     Output flow result grid
 * @return true on success, false on error
 */
bool optical_flow_compute(optical_flow_ctx_t *ctx,
                          const uint8_t *frame_curr,
                          const uint8_t *frame_prev,
                          FlowResult *result);

/**
 * @brief Deinitialize and free the optical flow processor
 *
 * @param ctx Optical flow context
 */
void optical_flow_deinit(optical_flow_ctx_t *ctx);

#ifdef __cplusplus
}
#endif
