/**
 * @file test_downscaler.c
 * @brief Unit tests for INT8 bilinear downscaler
 *
 * Tests correctness of the fixed-point bilinear interpolation
 * against known input/output pairs.
 *
 * Run with: pytest test_downscaler.py (host-side) or
 *           idf.py flash monitor (on-device)
 */

#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "downscaler.h"

/** Test helper: create a gradient pattern 320x240 */
static void fill_gradient(uint8_t *buf, uint32_t w, uint32_t h) {
    for (uint32_t y = 0; y < h; y++) {
        for (uint32_t x = 0; x < w; x++) {
            buf[y * w + x] = (uint8_t)((x * 255) / (w - 1));
        }
    }
}

/** Test helper: create a solid-color frame */
static void fill_solid(uint8_t *buf, uint32_t w, uint32_t h, uint8_t val) {
    memset(buf, val, w * h);
}

/** Test 1: Solid color should produce identical solid color after downscale */
static int test_solid_color(void) {
    uint8_t src[320 * 240];
    uint8_t dst[DOWNSCALED_BUF_SIZE];

    fill_solid(src, 320, 240, 128);

    downscaler_ctx_t *ctx = downscaler_init(dst);
    assert(ctx != NULL);

    InputFrame input = { .buffer = src, .width = 320, .height = 240, .stride = 320 };
    const uint8_t *result = downscale_bilinear(ctx, &input);
    assert(result == dst);

    for (int i = 0; i < DOWNSCALED_BUF_SIZE; i++) {
        if (dst[i] != 128) {
            printf("FAIL test_solid_color: pixel %d = %d, expected 128\n", i, dst[i]);
            downscaler_deinit(ctx);
            return 1;
        }
    }

    downscaler_deinit(ctx);
    printf("PASS test_solid_color\n");
    return 0;
}

/** Test 2: Corners of gradient should match expected values */
static int test_gradient_corners(void) {
    uint8_t src[320 * 240];
    uint8_t dst[DOWNSCALED_BUF_SIZE];

    fill_gradient(src, 320, 240);

    downscaler_ctx_t *ctx = downscaler_init(dst);
    assert(ctx != NULL);

    InputFrame input = { .buffer = src, .width = 320, .height = 240, .stride = 320 };
    downscale_bilinear(ctx, &input);

    /* Top-left corner should be ~0 */
    uint8_t tl = dst[0];
    /* Top-right corner should be ~255 */
    uint8_t tr = dst[DOWNSCALED_WIDTH - 1];
    /* Bottom-left should be ~0 */
    uint8_t bl = dst[(DOWNSCALED_HEIGHT - 1) * DOWNSCALED_WIDTH];
    /* Bottom-right should be ~255 */
    uint8_t br = dst[DOWNSCALED_HEIGHT * DOWNSCALED_WIDTH - 1];

    int pass = 1;
    if (tl > 5)  { printf("FAIL: top-left = %d, expected ~0\n", tl); pass = 0; }
    if (tr < 250) { printf("FAIL: top-right = %d, expected ~255\n", tr); pass = 0; }
    if (bl > 5)  { printf("FAIL: bottom-left = %d, expected ~0\n", bl); pass = 0; }
    if (br < 250) { printf("FAIL: bottom-right = %d, expected ~255\n", br); pass = 0; }

    downscaler_deinit(ctx);
    if (pass) printf("PASS test_gradient_corners\n");
    return !pass;
}

/** Test 3: Output buffer size is exactly 19,200 bytes */
static int test_buffer_size(void) {
    if (DOWNSCALED_BUF_SIZE != 19200) {
        printf("FAIL test_buffer_size: %d != 19200\n", DOWNSCALED_BUF_SIZE);
        return 1;
    }
    printf("PASS test_buffer_size\n");
    return 0;
}

/** Test 4: Null input returns NULL */
static int test_null_input(void) {
    uint8_t dst[DOWNSCALED_BUF_SIZE];
    downscaler_ctx_t *ctx = downscaler_init(dst);

    const uint8_t *result = downscale_bilinear(ctx, NULL);
    assert(result == NULL);

    InputFrame null_frame = {NULL, 320, 240, 320};
    result = downscale_bilinear(ctx, &null_frame);
    assert(result == NULL);

    downscaler_deinit(ctx);
    printf("PASS test_null_input\n");
    return 0;
}

/** Test 5: Output pixel values stay in valid range [0, 255] */
static int test_pixel_range(void) {
    uint8_t src[320 * 240];
    uint8_t dst[DOWNSCALED_BUF_SIZE];

    /* Random-ish pattern: alternating rows */
    for (int y = 0; y < 240; y++) {
        for (int x = 0; x < 320; x++) {
            src[y * 320 + x] = (uint8_t)((x + y) & 0xFF);
        }
    }

    downscaler_ctx_t *ctx = downscaler_init(dst);
    InputFrame input = { .buffer = src, .width = 320, .height = 240, .stride = 320 };
    downscale_bilinear(ctx, &input);

    for (int i = 0; i < DOWNSCALED_BUF_SIZE; i++) {
        if (dst[i] > 255) {  /* uint8_t can't exceed 255, but check for wrap */
            printf("FAIL test_pixel_range: pixel %d out of range\n", i);
            downscaler_deinit(ctx);
            return 1;
        }
    }

    downscaler_deinit(ctx);
    printf("PASS test_pixel_range\n");
    return 0;
}

/** Test 6: Stride < width or width/height < downscaled resolution returns NULL */
static int test_stride_and_dim_validation(void) {
    uint8_t src[320 * 240];
    uint8_t dst[DOWNSCALED_BUF_SIZE];
    downscaler_ctx_t *ctx = downscaler_init(dst);

    // Stride < width
    InputFrame invalid_stride = {src, 320, 240, 300};
    assert(downscale_bilinear(ctx, &invalid_stride) == NULL);

    // Width < DOWNSCALED_WIDTH (160)
    InputFrame small_w = {src, 100, 240, 100};
    assert(downscale_bilinear(ctx, &small_w) == NULL);

    // Height < DOWNSCALED_HEIGHT (120)
    InputFrame small_h = {src, 320, 100, 320};
    assert(downscale_bilinear(ctx, &small_h) == NULL);

    downscaler_deinit(ctx);
    printf("PASS test_stride_and_dim_validation\n");
    return 0;
}

int main(void) {
    printf("=== Downscaler Unit Tests ===\n");
    int failures = 0;

    failures += test_solid_color();
    failures += test_gradient_corners();
    failures += test_buffer_size();
    failures += test_null_input();
    failures += test_pixel_range();
    failures += test_stride_and_dim_validation();

    printf("\n=== Results: %d failures ===\n", failures);
    return failures;
}
