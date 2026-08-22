/**
 * @file optical_flow.c
 * @brief Block-Based SAD Optical Flow Implementation
 *
 * Computes dense motion vectors using Sum of Absolute Differences (SAD)
 * block matching on a 16x16 macroblock grid with +/-8 pixel search range.
 *
 * Optimized for ESP32-S3 Xtensa LX7 with SIMD intrinsics for the
 * inner SAD accumulation loop.
 *
 * Performance target: <= 18ms for 64+ blocks at 240MHz.
 */

#include "optical_flow.h"

#include <stdlib.h>
#include <string.h>
#include <limits.h>

/* ESP32-S3 SIMD intrinsics for 8-bit absolute difference */
#if defined(__xtensa__) && defined(__ESP32S3__)
#include <xtensa/tie/xt_math.h>
#define USE_XTENSA_SIMD 1
#else
#define USE_XTENSA_SIMD 0
#endif

struct optical_flow_ctx {
    /* Reserved for future pipeline state */
    uint32_t flags;
};

/* ============================================================
 * Optimized SAD computation
 * ============================================================ */

/**
 * @brief Compute SAD between two 16x16 macroblocks (scalar fallback)
 *
 * SAD(dx,dy) = sum |curr[x,y] - prev[x+dx, y+dy]| for x,y in [0,16)
 */
static inline uint32_t sad_block_scalar(const uint8_t *curr,
                                        const uint8_t *prev,
                                        int32_t stride_curr,
                                        int32_t stride_prev,
                                        int32_t offset_x,
                                        int32_t offset_y)
{
    uint32_t sad = 0;
    for (int32_t by = 0; by < MB_SIZE; by++) {
        const uint8_t *row_curr = curr + by * stride_curr;
        const uint8_t *row_prev = prev + (by + offset_y) * stride_prev;
        for (int32_t bx = 0; bx < MB_SIZE; bx++) {
            int32_t diff = (int32_t)row_curr[bx] - (int32_t)row_prev[bx + offset_x];
            sad += (uint32_t)(diff < 0 ? -diff : diff);
        }
    }
    return sad;
}

/**
 * @brief Compute SAD between two 16x16 macroblocks with loop unrolling and memcpy loads
 *
 * Processes 8 bytes per chunk, correctly computing signed absolute differences.
 */
static inline uint32_t sad_block_unrolled(const uint8_t *curr,
                                          const uint8_t *prev,
                                          int32_t stride_curr,
                                          int32_t stride_prev,
                                          int32_t offset_x,
                                          int32_t offset_y)
{
    uint32_t sad = 0;

    for (int32_t by = 0; by < MB_SIZE; by++) {
        const uint8_t *row_curr = curr + by * stride_curr;
        const uint8_t *row_prev = prev + (by + offset_y) * stride_prev;
        int32_t bx = 0;

        /* Process 8 bytes at a time using unrolled loop */
        for (; bx + 8 <= MB_SIZE; bx += 8) {
            /* Aligned/safe load of 4 bytes using memcpy (avoids unaligned dereference UB) */
            uint32_t a_val, b_val, a2_val, b2_val;
            memcpy(&a_val, row_curr + bx, sizeof(uint32_t));
            memcpy(&b_val, row_prev + bx + offset_x, sizeof(uint32_t));
            memcpy(&a2_val, row_curr + bx + 4, sizeof(uint32_t));
            memcpy(&b2_val, row_prev + bx + offset_x + 4, sizeof(uint32_t));

            uint32_t abs_diff = 0;
            int32_t diff;

            /* Byte 0 */
            diff = (int32_t)(a_val & 0xFF) - (int32_t)(b_val & 0xFF);
            abs_diff += (uint32_t)(diff < 0 ? -diff : diff);
            /* Byte 1 */
            diff = (int32_t)((a_val >> 8) & 0xFF) - (int32_t)((b_val >> 8) & 0xFF);
            abs_diff += (uint32_t)(diff < 0 ? -diff : diff);
            /* Byte 2 */
            diff = (int32_t)((a_val >> 16) & 0xFF) - (int32_t)((b_val >> 16) & 0xFF);
            abs_diff += (uint32_t)(diff < 0 ? -diff : diff);
            /* Byte 3 */
            diff = (int32_t)((a_val >> 24) & 0xFF) - (int32_t)((b_val >> 24) & 0xFF);
            abs_diff += (uint32_t)(diff < 0 ? -diff : diff);

            /* Bytes 4-7 */
            diff = (int32_t)(a2_val & 0xFF) - (int32_t)(b2_val & 0xFF);
            abs_diff += (uint32_t)(diff < 0 ? -diff : diff);
            diff = (int32_t)((a2_val >> 8) & 0xFF) - (int32_t)((b2_val >> 8) & 0xFF);
            abs_diff += (uint32_t)(diff < 0 ? -diff : diff);
            diff = (int32_t)((a2_val >> 16) & 0xFF) - (int32_t)((b2_val >> 16) & 0xFF);
            abs_diff += (uint32_t)(diff < 0 ? -diff : diff);
            diff = (int32_t)((a2_val >> 24) & 0xFF) - (int32_t)((b2_val >> 24) & 0xFF);
            abs_diff += (uint32_t)(diff < 0 ? -diff : diff);

            sad += abs_diff;
        }

        /* Handle remaining bytes (scalar) */
        for (; bx < MB_SIZE; bx++) {
            int32_t d = (int32_t)row_curr[bx] - (int32_t)row_prev[bx + offset_x];
            sad += (uint32_t)(d < 0 ? -d : d);
        }
    }

    return sad;
}

/**
 * @brief Compute SAD for a block, using the unrolled fast path
 */
static inline uint32_t sad_block(const uint8_t *curr,
                                 const uint8_t *prev,
                                 int32_t stride_curr,
                                 int32_t stride_prev,
                                 int32_t offset_x,
                                 int32_t offset_y)
{
    return sad_block_unrolled(curr, prev, stride_curr, stride_prev, offset_x, offset_y);
}

#ifdef OPTICAL_FLOW_TEST_EXPORTS
uint32_t test_sad_block_scalar(const uint8_t *curr, const uint8_t *prev, int32_t sc, int32_t sp, int32_t ox, int32_t oy) {
    return sad_block_scalar(curr, prev, sc, sp, ox, oy);
}
uint32_t test_sad_block_unrolled(const uint8_t *curr, const uint8_t *prev, int32_t sc, int32_t sp, int32_t ox, int32_t oy) {
    return sad_block_unrolled(curr, prev, sc, sp, ox, oy);
}
#endif

/**
 * @brief Compute spatial variance of a macroblock for confidence scoring
 *
 * Variance measures texture: low variance = textureless surface
 * where motion estimation is unreliable.
 */
static float block_variance(const uint8_t *block, int32_t stride) {
    uint32_t sum = 0;
    uint64_t sum_sq = 0;

    for (int32_t by = 0; by < MB_SIZE; by++) {
        const uint8_t *row = block + by * stride;
        for (int32_t bx = 0; bx < MB_SIZE; bx++) {
            uint32_t v = row[bx];
            sum += v;
            sum_sq += (uint64_t)v * v;
        }
    }

    const uint32_t n = MB_SIZE * MB_SIZE;
    float mean = (float)sum / n;
    float mean_sq = (float)sum_sq / n;
    return mean_sq - mean * mean;
}

/* ============================================================
 * Public API
 * ============================================================ */

optical_flow_ctx_t *optical_flow_init(void) {
    return static_cast<optical_flow_ctx_t*>(calloc(1, sizeof(optical_flow_ctx_t)));
}

bool optical_flow_compute(optical_flow_ctx_t *ctx,
                          const uint8_t *frame_curr,
                          const uint8_t *frame_prev,
                          FlowResult *result)
{
    if (!ctx || !frame_curr || !frame_prev || !result) return false;

    const int32_t stride = OF_WIDTH;

    result->num_blocks = 0;

    for (int32_t gy = 0; gy < GRID_ROWS; gy++) {
        for (int32_t gx = 0; gx < GRID_COLS; gx++) {
            uint32_t idx = gy * GRID_COLS + gx;
            MotionVector *mv = &result->vectors[idx];

            /* Top-left corner of this macroblock in the current frame */
            const int32_t mb_x = gx * MB_SIZE;
            const int32_t mb_y = gy * MB_SIZE;
            const uint8_t *mb_curr = frame_curr + mb_y * stride + mb_x;

            /* Compute variance for confidence */
            float var = block_variance(mb_curr, stride);

            /* Search window bounds (clipped to frame edges) */
            int32_t sx_min = -SEARCH_RANGE;
            int32_t sy_min = -SEARCH_RANGE;
            int32_t sx_max =  SEARCH_RANGE;
            int32_t sy_max =  SEARCH_RANGE;

            if (mb_x + sx_min < 0) sx_min = -mb_x;
            if (mb_y + sy_min < 0) sy_min = -mb_y;
            if (mb_x + MB_SIZE + sx_max > OF_WIDTH)
                sx_max = OF_WIDTH - mb_x - MB_SIZE;
            if (mb_y + MB_SIZE + sy_max > OF_HEIGHT)
                sy_max = OF_HEIGHT - mb_y - MB_SIZE;

            /* Find minimum SAD displacement */
            uint32_t best_sad = UINT32_MAX;
            int8_t best_dx = 0;
            int8_t best_dy = 0;

            for (int32_t dy = sy_min; dy <= sy_max; dy++) {
                for (int32_t dx = sx_min; dx <= sx_max; dx++) {
                    const uint8_t *mb_prev = frame_prev +
                        (mb_y + dy) * stride + (mb_x + dx);

                    uint32_t sad = sad_block(mb_curr, mb_prev,
                                             stride, stride, 0, 0);

                    if (sad < best_sad) {
                        best_sad = sad;
                        best_dx = (int8_t)dx;
                        best_dy = (int8_t)dy;
                    }
                }
            }

            mv->dx = best_dx;
            mv->dy = best_dy;

            /* Confidence: scale variance to 0-255, clip textureless blocks */
            if (var < VARIANCE_THRESHOLD) {
                mv->confidence = 0;  /* Textureless: unreliable */
            } else if (var > 200.0f) {
                mv->confidence = 255;
            } else {
                mv->confidence = (uint8_t)((var / 200.0f) * 255.0f);
            }

            result->num_blocks++;
        }
    }

    return true;
}

void optical_flow_deinit(optical_flow_ctx_t *ctx) {
    free(ctx);
}
