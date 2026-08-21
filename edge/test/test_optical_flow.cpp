/**
 * @file test_optical_flow.c
 * @brief Unit tests for block-based SAD optical flow
 *
 * Tests: block matching, motion vector correctness, confidence scoring,
 * boundary handling, and stationary scene detection.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "optical_flow.h"
#include "homography.h"

/** Helper: fill frame with uniform value */
static void fill_frame(uint8_t *frame, uint8_t val) {
    memset(frame, val, OF_WIDTH * OF_HEIGHT);
}

/** Helper: create a shifted block pattern */
static void create_shifted_frames(uint8_t *curr, uint8_t *prev,
                                   int shift_x, int shift_y) {
    fill_frame(curr, 128);
    fill_frame(prev, 128);

    /* Place a bright 16x16 block in the previous frame at center */
    int bx = OF_WIDTH / 2 - 8;
    int by = OF_HEIGHT / 2 - 8;
    for (int y = 0; y < 16; y++) {
        for (int x = 0; x < 16; x++) {
            prev[(by + y) * OF_WIDTH + (bx + x)] = 200;
        }
    }

    /* Place the same block in current frame, shifted by (shift_x, shift_y) */
    int cx = bx + shift_x;
    int cy = by + shift_y;
    for (int y = 0; y < 16; y++) {
        for (int x = 0; x < 16; x++) {
            if (cy + y >= 0 && cy + y < OF_HEIGHT && cx + x >= 0 && cx + x < OF_WIDTH) {
                curr[(cy + y) * OF_WIDTH + (cx + x)] = 200;
            }
        }
    }
}

/** Test 1: Stationary scene produces zero or near-zero vectors */
static int test_stationary(void) {
    uint8_t frame[OF_WIDTH * OF_HEIGHT];
    fill_frame(frame, 100);

    optical_flow_ctx_t *ctx = optical_flow_init();
    FlowResult result;

    bool ok = optical_flow_compute(ctx, frame, frame, &result);
    if (!ok) { printf("FAIL: compute returned false\n"); optical_flow_deinit(ctx); return 1; }

    for (uint32_t i = 0; i < result.num_blocks; i++) {
        /* Uniform frame: SAD is 0 for all displacements, so any vector is valid.
         * Just check confidence is 0 (textureless). */
        if (result.vectors[i].confidence != 0) {
            printf("FAIL: block %u textureless frame should have confidence=0, got %u\n",
                   i, result.vectors[i].confidence);
            optical_flow_deinit(ctx);
            return 1;
        }
    }

    optical_flow_deinit(ctx);
    printf("PASS test_stationary\n");
    return 0;
}

/** Test 2: Shifted block produces correct motion vector */
static int test_shifted_block(void) {
    uint8_t curr[OF_WIDTH * OF_HEIGHT];
    uint8_t prev[OF_WIDTH * OF_HEIGHT];

    /* Block moved RIGHT by 4 pixels in current frame relative to previous.
     * So in prev frame it was LEFT of where it is now.
     * The motion vector should point LEFT (negative dx) to find the match. */
    create_shifted_frames(curr, prev, 4, 0);

    optical_flow_ctx_t *ctx = optical_flow_init();
    FlowResult result;

    optical_flow_compute(ctx, curr, prev, &result);

    /* Find the block containing the bright region */
    int center_gx = (OF_WIDTH / 2) / MB_SIZE;
    int center_gy = (OF_HEIGHT / 2) / MB_SIZE;
    uint32_t idx = center_gy * GRID_COLS + center_gx;

    MotionVector mv = result.vectors[idx];
    /* dx should be negative (searching left in prev frame) */
    if (mv.dx > -2 || mv.dx < -6) {
        printf("FAIL: expected dx ~-4, got dx=%d (block %u)\n", mv.dx, idx);
        optical_flow_deinit(ctx);
        return 1;
    }

    optical_flow_deinit(ctx);
    printf("PASS test_shifted_block\n");
    return 0;
}

/** Test 3: Grid dimensions are correct */
static int test_grid_dims(void) {
    if (GRID_COLS != 10) {
        printf("FAIL: GRID_COLS = %d, expected 10\n", GRID_COLS);
        return 1;
    }
    if (GRID_ROWS != 7) {
        printf("FAIL: GRID_ROWS = %d, expected 7\n", GRID_ROWS);
        return 1;
    }
    if (NUM_BLOCKS != 70) {
        printf("FAIL: NUM_BLOCKS = %d, expected 70\n", NUM_BLOCKS);
        return 1;
    }
    printf("PASS test_grid_dims\n");
    return 0;
}

/** Test 4: Textureless scene has low confidence */
static int test_textureless_confidence(void) {
    uint8_t frame[OF_WIDTH * OF_HEIGHT];
    fill_frame(frame, 128);

    optical_flow_ctx_t *ctx = optical_flow_init();
    FlowResult result;

    optical_flow_compute(ctx, frame, frame, &result);

    /* Uniform frame should have zero confidence everywhere */
    for (uint32_t i = 0; i < result.num_blocks; i++) {
        if (result.vectors[i].confidence != 0) {
            printf("FAIL: textureless block %u has confidence %d, expected 0\n",
                   i, result.vectors[i].confidence);
            optical_flow_deinit(ctx);
            return 1;
        }
    }

    optical_flow_deinit(ctx);
    printf("PASS test_textureless_confidence\n");
    return 0;
}

/** Test 5: Textured scene has non-zero confidence */
static int test_textured_confidence(void) {
    uint8_t frame[OF_WIDTH * OF_HEIGHT];

    /* Create a gradient pattern (high texture) */
    for (int y = 0; y < OF_HEIGHT; y++) {
        for (int x = 0; x < OF_WIDTH; x++) {
            frame[y * OF_WIDTH + x] = (uint8_t)((x * 3 + y * 7) & 0xFF);
        }
    }

    optical_flow_ctx_t *ctx = optical_flow_init();
    FlowResult result;

    optical_flow_compute(ctx, frame, frame, &result);

    /* At least some blocks should have non-zero confidence */
    uint32_t confident_count = 0;
    for (uint32_t i = 0; i < result.num_blocks; i++) {
        if (result.vectors[i].confidence > 0) confident_count++;
    }

    if (confident_count < NUM_BLOCKS / 2) {
        printf("FAIL: only %u/%d blocks have confidence\n", confident_count, NUM_BLOCKS);
        optical_flow_deinit(ctx);
        return 1;
    }

    optical_flow_deinit(ctx);
    printf("PASS test_textured_confidence\n");
    return 0;
}

/** Test 6: Null inputs handled gracefully */
static int test_null_inputs(void) {
    optical_flow_ctx_t *ctx = optical_flow_init();
    FlowResult result;

    bool ok = optical_flow_compute(ctx, NULL, NULL, &result);
    if (ok) { printf("FAIL: NULL input should return false\n"); optical_flow_deinit(ctx); return 1; }

    uint8_t frame[OF_WIDTH * OF_HEIGHT];
    fill_frame(frame, 0);
    ok = optical_flow_compute(ctx, frame, NULL, &result);
    if (ok) { printf("FAIL: NULL prev should return false\n"); optical_flow_deinit(ctx); return 1; }

    optical_flow_deinit(ctx);
    printf("PASS test_null_inputs\n");
    return 0;
}

/** Test 7: num_blocks matches expected count */
static int test_num_blocks(void) {
    uint8_t frame[OF_WIDTH * OF_HEIGHT];
    fill_frame(frame, 50);

    optical_flow_ctx_t *ctx = optical_flow_init();
    FlowResult result;

    optical_flow_compute(ctx, frame, frame, &result);

    if (result.num_blocks != NUM_BLOCKS) {
        printf("FAIL: num_blocks = %u, expected %d\n", result.num_blocks, NUM_BLOCKS);
        optical_flow_deinit(ctx);
        return 1;
    }

    optical_flow_deinit(ctx);
    printf("PASS test_num_blocks\n");
    return 0;
}

static int test_motion_energy(void) {
    // Initialize 70 homography trackers (since GRID_COLS=10, GRID_ROWS=7)
    // We will use a standard identity homography matrix for simplicity
    float h_norm[9] = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f
    };

    homography_ctx_t *trackers[NUM_BLOCKS];
    for (int i = 0; i < NUM_BLOCKS; i++) {
        trackers[i] = homography_init(h_norm);
        if (!trackers[i]) {
            printf("FAIL: failed to init homography tracker %d\n", i);
            return 1;
        }
    }

    int8_t dx[NUM_BLOCKS];
    int8_t dy[NUM_BLOCKS];
    uint8_t confidence[NUM_BLOCKS];

    // Scenario 1: Stationary blocks (dx=0, dy=0) with some confidence
    for (int i = 0; i < NUM_BLOCKS; i++) {
        dx[i] = 0;
        dy[i] = 0;
        confidence[i] = 100; // All confident
    }

    // First frame (dt = 40ms, i.e. 40,000 us) to seed tracking
    float energy = -1.0f;
    bool ok = homography_compute_motion_energy(
        trackers, dx, dy, confidence, NUM_BLOCKS, 40000,
        1.0f, 0.0f, 0.0f, // lambda1=1.0, others 0
        1.0f, 1.0f, 1.0f, // refs = 1.0
        &energy
    );
    
    // First frame velocity is computed, but let's check it is 0
    if (!ok || energy < -1e-4f || energy > 1e-4f) {
        printf("FAIL: expected 0 energy for stationary blocks on first frame, got %f (ok=%d)\n", energy, ok);
        for (int j = 0; j < NUM_BLOCKS; j++) homography_deinit(trackers[j]);
        return 1;
    }

    // Second frame: constant displacement dx = 2 pixels for all blocks
    // With identity homography, 1 pixel = 1 meter. So displacement is 2 meters.
    // dt = 40ms (0.04s). Velocity = 2 / 0.04 = 50 m/s.
    // With EMA alpha = 1/3 (HOM_EMA_ALPHA = 21845):
    // v_smoothed = (1/3) * 50 + (2/3) * 0 = 16.66667 m/s.
    // v_ref = 10.0f. So term = (16.66667)^2 / (10.0f)^2 = 277.7778 / 100 = 2.77778.
    // Expected energy = 2.77778.
    for (int i = 0; i < NUM_BLOCKS; i++) {
        dx[i] = 2;
        dy[i] = 0;
    }

    ok = homography_compute_motion_energy(
        trackers, dx, dy, confidence, NUM_BLOCKS, 40000,
        1.0f, 0.0f, 0.0f, // lambda1=1.0, others 0
        10.0f, 1.0f, 1.0f, // v_ref = 10.0
        &energy
    );

    float expected_energy = 2.77778f;
    if (!ok || fabsf(energy - expected_energy) > 0.05f) {
        printf("FAIL: expected energy ~%f, got %f\n", expected_energy, energy);
        for (int j = 0; j < NUM_BLOCKS; j++) homography_deinit(trackers[j]);
        return 1;
    }

    // Scenario 2: Test division by zero safeguard (all confidence = 0)
    for (int i = 0; i < NUM_BLOCKS; i++) {
        confidence[i] = 0;
    }
    ok = homography_compute_motion_energy(
        trackers, dx, dy, confidence, NUM_BLOCKS, 40000,
        1.0f, 1.0f, 1.0f,
        10.0f, 1.0f, 1.0f,
        &energy
    );
    if (!ok || energy != 0.0f) {
        printf("FAIL: expected division-by-zero safeguard to return 0.0f, got %f (ok=%d)\n", energy, ok);
        for (int j = 0; j < NUM_BLOCKS; j++) homography_deinit(trackers[j]);
        return 1;
    }

    // Clean up
    for (int i = 0; i < NUM_BLOCKS; i++) {
        homography_deinit(trackers[i]);
    }

    printf("PASS test_motion_energy\n");
    return 0;
}

int main(void) {
    printf("=== Optical Flow Unit Tests ===\n");
    int failures = 0;

    failures += test_stationary();
    failures += test_shifted_block();
    failures += test_grid_dims();
    failures += test_textureless_confidence();
    failures += test_textured_confidence();
    failures += test_null_inputs();
    failures += test_num_blocks();
    failures += test_motion_energy();

    printf("\n=== Results: %d failures ===\n", failures);
    return failures;
}
