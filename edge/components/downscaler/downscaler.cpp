/**
 * @file downscaler.c
 * @brief INT8 Bilinear Downscaler Implementation
 *
 * Bilinear interpolation from 320x240 -> 160x120 using Q8.8 fixed-point
 * arithmetic to avoid floating-point on the MCU. Optimized for ESP32-S3.
 *
 * Performance target: <= 8ms per frame at 240MHz.
 */

#include "downscaler.h"

#include <stdlib.h>
#include <string.h>

/** Q8.8 fixed-point: 1.0 = 256 */
#define FP_SHIFT     8
#define FP_ONE       (1 << FP_SHIFT)       /* 256 */
#define FP_HALF      (1 << (FP_SHIFT - 1)) /* 128 */

struct downscaler_ctx {
    uint8_t *output;
};

downscaler_ctx_t *downscaler_init(uint8_t *output_buffer) {
    if (!output_buffer) return NULL;

    downscaler_ctx_t *ctx = static_cast<downscaler_ctx_t*>(calloc(1, sizeof(downscaler_ctx_t)));
    if (!ctx) return NULL;

    ctx->output = output_buffer;
    return ctx;
}

const uint8_t *downscale_bilinear(downscaler_ctx_t *ctx, const InputFrame *input) {
    if (!ctx || !input || !input->buffer) return NULL;
    if (input->width < 2 || input->height < 2) return NULL;
    if (input->stride < input->width) return NULL;
    if (input->width < DOWNSCALED_WIDTH || input->height < DOWNSCALED_HEIGHT) return NULL;

    const uint8_t *src = input->buffer;
    const uint32_t src_w = input->width;
    const uint32_t src_h = input->height;
    const uint32_t src_stride = input->stride;
    uint8_t *dst = ctx->output;

    /*
     * Compute fixed-point ratios:
     *   x_ratio = (src_w - 1) / dst_w  in Q8.8
     *   y_ratio = (src_h - 1) / dst_h  in Q8.8
     *
     * For 320->160: x_ratio = 319/160 = 1.99375 -> Q8.8 = 510
     * For 240->120: y_ratio = 239/120 = 1.99167 -> Q8.8 = 510
     */
    const uint32_t x_ratio_fp = (uint32_t)(((src_w - 1) << FP_SHIFT) / DOWNSCALED_WIDTH);
    const uint32_t y_ratio_fp = (uint32_t)(((src_h - 1) << FP_SHIFT) / DOWNSCALED_HEIGHT);

    for (uint32_t i = 0; i < DOWNSCALED_HEIGHT; i++) {
        /* Source y coordinate in Q8.8 */
        const uint32_t y_fp = i * y_ratio_fp;
        const uint32_t y0 = y_fp >> FP_SHIFT;         /* Integer part */
        const uint32_t fy = y_fp & (FP_ONE - 1);      /* Fractional part (0..255) */
        const uint32_t fy_inv = FP_ONE - fy;           /* 1 - fy */

        /* Precompute row pointers for this scanline */
        const uint8_t *row0 = src + (y0 * src_stride);
        const uint8_t *row1 = src + ((y0 + 1) * src_stride);

        for (uint32_t j = 0; j < DOWNSCALED_WIDTH; j++) {
            /* Source x coordinate in Q8.8 */
            const uint32_t x_fp = j * x_ratio_fp;
            const uint32_t x0 = x_fp >> FP_SHIFT;
            const uint32_t fx = x_fp & (FP_ONE - 1);
            const uint32_t fx_inv = FP_ONE - fx;

            /* Four neighboring pixels */
            const uint8_t a = row0[x0];
            const uint8_t b = row0[x0 + 1];
            const uint8_t c = row1[x0];
            const uint8_t d = row1[x0 + 1];

            /*
             * Bilinear interpolation in Q8.8 fixed-point:
             *   val = a*(1-fx)*(1-fy) + b*fx*(1-fy) + c*(1-fx)*fy + d*fx*fy
             *
             * All multiplications are in Q8.8, result shifted back to Q0.8.
             * Sum of weights = (fx_inv*fy_inv + fx*fy_inv + fx_inv*fy + fx*fy) = FP_ONE*FP_ONE
             * So final result = sum >> FP_SHIFT
             */
            const uint32_t p00 = a * fx_inv * fy_inv;  /* a * (1-fx) * (1-fy) */
            const uint32_t p10 = b * fx * fy_inv;       /* b * fx * (1-fy) */
            const uint32_t p01 = c * fx_inv * fy;       /* c * (1-fx) * fy */
            const uint32_t p11 = d * fx * fy;            /* d * fx * fy */

            const uint32_t sum = p00 + p10 + p01 + p11;
            dst[(i * DOWNSCALED_WIDTH) + j] = (uint8_t)(sum >> (FP_SHIFT * 2));
        }
    }

    return dst;
}

void downscaler_deinit(downscaler_ctx_t *ctx) {
    free(ctx);
}
