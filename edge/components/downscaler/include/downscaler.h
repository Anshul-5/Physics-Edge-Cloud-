/**
 * @file downscaler.h
 * @brief INT8 Bilinear Downscaling for PhysEdge-Cloud L1 Edge Gate
 *
 * High-performance bilinear interpolation downsampling from 320x240
 * to 160x120 grayscale using fixed-point arithmetic (Q8.8).
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Output resolution after downscaling */
#define DOWNSCALED_WIDTH   160
#define DOWNSCALED_HEIGHT  120

/** Output buffer size in bytes */
#define DOWNSCALED_BUF_SIZE (DOWNSCALED_WIDTH * DOWNSCALED_HEIGHT)  /* 19,200 bytes */

/**
 * @brief Input frame descriptor (raw camera output)
 */
typedef struct {
    const uint8_t *buffer;  /**< Grayscale pixel data */
    uint32_t width;         /**< Frame width (e.g., 320) */
    uint32_t height;        /**< Frame height (e.g., 240) */
    uint32_t stride;        /**< Bytes per row */
} InputFrame;

/**
 * @brief Downscaler context (opaque)
 */
typedef struct downscaler_ctx downscaler_ctx_t;

/**
 * @brief Initialize the downscaler with pre-allocated output buffer
 *
 * @param output_buffer Pre-allocated buffer of at least DOWNSCALED_BUF_SIZE bytes.
 *                      Must remain valid for the lifetime of the context.
 * @return Downscaler context, or NULL on failure
 */
downscaler_ctx_t *downscaler_init(uint8_t *output_buffer);

/**
 * @brief Downscale a 320x240 frame to 160x120 using bilinear interpolation
 *
 * Uses Q8.8 fixed-point arithmetic for speed (no float on MCU).
 * Target: <= 8ms per frame on ESP32-S3 @ 240MHz.
 *
 * @param ctx Downscaler context
 * @param input Input frame (320x240 grayscale)
 * @return Pointer to downscaled output buffer (160x120)
 */
const uint8_t *downscale_bilinear(downscaler_ctx_t *ctx, const InputFrame *input);

/**
 * @brief Deinitialize and free the downscaler
 *
 * @param ctx Downscaler context
 */
void downscaler_deinit(downscaler_ctx_t *ctx);

#ifdef __cplusplus
}
#endif
