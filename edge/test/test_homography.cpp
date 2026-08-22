/**
 * @file test_homography.c
 * @brief Unit tests for homography projection & ground-plane kinematics
 *
 * Tests: fixed-point conversion, identity homography projection, perspective
 * projection, denominator guard, velocity/acceleration/jerk computation,
 * EWMA noise smoothing, and error handling.
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "homography.h"

#define ASSERT_TRUE(cond, msg) do { \
    if (!(cond)) { printf("FAIL: %s\n", msg); return 1; } \
} while (0)

/* expected is given as a real number (double), actual as Q16.16 fixed point */
#define ASSERT_NEAR_FP(actual, expected, tol, msg) do { \
    double a = (double)(actual) / (double)HOM_FP_ONE; \
    double e = (double)(expected); \
    if (fabs(a - e) > (double)(tol)) { \
        printf("FAIL: %s (got %.6f, expected %.6f, tol %.6f)\n", msg, a, e, (double)tol); \
        return 1; \
    } \
} while (0)

/* Identity homography: maps pixels directly to meters (for easy verification) */
static const float IDENTITY_H[9] = {
    1.0f, 0.0f, 0.0f,
    0.0f, 1.0f, 0.0f,
    0.0f, 0.0f, 1.0f
};

/* Scaling homography: 1 pixel = 0.5 m in X, 1 pixel = 0.25 m in Y */
static const float SCALE_H[9] = {
    0.5f, 0.0f, 0.0f,
    0.0f, 0.25f, 0.0f,
    0.0f, 0.0f, 1.0f
};

/* Perspective homography with foreshortening in X (h20 != 0) */
static const float PERSPECTIVE_H[9] = {
    1.0f, 0.0f, 0.0f,
    0.0f, 1.0f, 0.0f,
    0.01f, 0.0f, 1.0f
};

/** Test 1: Fixed-point conversions round-trip */
static int test_fixed_point_conversions(void) {
    ASSERT_NEAR_FP(hom_float_to_fp(1.0f), 1.0, 0.000001, "1.0 conversion");
    ASSERT_NEAR_FP(hom_float_to_fp(0.5f), 0.5, 0.000001, "0.5 conversion");
    ASSERT_NEAR_FP(hom_float_to_fp(-2.0f), -2.0, 0.000001, "-2.0 conversion");

    /* Round trip */
    ASSERT_NEAR_FP(hom_float_to_fp(3.14159f), 3.14159, 0.001, "pi conversion");
    ASSERT_NEAR_FP(hom_float_to_fp(hom_fp_to_float(hom_float_to_fp(0.123f))), 0.123, 0.001, "round-trip");
    printf("PASS test_fixed_point_conversions\n");
    return 0;
}

/** Test 2: Fixed-point multiply and divide */
static int test_fixed_point_arith(void) {
    ASSERT_NEAR_FP(hom_fp_mul(hom_float_to_fp(2.0f), hom_float_to_fp(3.0f)), 6.0, 0.001, "multiply 2*3");
    ASSERT_NEAR_FP(hom_fp_mul(hom_float_to_fp(0.5f), hom_float_to_fp(0.25f)), 0.125, 0.001, "multiply 0.5*0.25");
    ASSERT_NEAR_FP(hom_fp_div(hom_float_to_fp(6.0f), hom_float_to_fp(2.0f)), 3.0, 0.001, "divide 6/2");
    ASSERT_NEAR_FP(hom_fp_div(hom_float_to_fp(1.0f), hom_float_to_fp(0.25f)), 4.0, 0.001, "divide 1/0.25");
    ASSERT_NEAR_FP(hom_fp_div(hom_float_to_fp(5.0f), 0), 0.0, 0.001, "divide by zero");
    printf("PASS test_fixed_point_arith\n");
    return 0;
}

/** Test 3: Identity homography maps pixel to metric directly */
static int test_identity_projection(void) {
    homography_ctx_t *ctx = homography_init(IDENTITY_H);
    ASSERT_TRUE(ctx != NULL, "init should succeed");

    HomPoint p;
    ASSERT_TRUE(homography_project(ctx, 10, 20, &p), "project should succeed");
    ASSERT_TRUE(p.valid, "point should be valid");
    ASSERT_NEAR_FP(p.x_m, 10.0, 0.001, "identity X");
    ASSERT_NEAR_FP(p.y_m, 20.0, 0.001, "identity Y");

    homography_deinit(ctx);
    printf("PASS test_identity_projection\n");
    return 0;
}

/** Test 4: Scaling homography maps pixels with correct scale */
static int test_scale_projection(void) {
    homography_ctx_t *ctx = homography_init(SCALE_H);
    ASSERT_TRUE(ctx != NULL, "init should succeed");

    HomPoint p;
    ASSERT_TRUE(homography_project(ctx, 100, 80, &p), "project should succeed");
    ASSERT_TRUE(p.valid, "point should be valid");
    ASSERT_NEAR_FP(p.x_m, 50.0, 0.01, "scaled X (0.5 m/px)");
    ASSERT_NEAR_FP(p.y_m, 20.0, 0.01, "scaled Y (0.25 m/px)");

    homography_deinit(ctx);
    printf("PASS test_scale_projection\n");
    return 0;
}

/** Test 5: Perspective homography with foreshortening */
static int test_perspective_projection(void) {
    homography_ctx_t *ctx = homography_init(PERSPECTIVE_H);
    ASSERT_TRUE(ctx != NULL, "init should succeed");

    /* With h20=0.01, denominator = 1 + 0.01*x.
     * At x=100: denom = 2.0, so X_m = 100/2 = 50 (foreshortened). */
    HomPoint p;
    ASSERT_TRUE(homography_project(ctx, 100, 0, &p), "project should succeed");
    ASSERT_TRUE(p.valid, "point should be valid");
    ASSERT_NEAR_FP(p.x_m, 50.0, 0.1, "perspective X at x=100");
    ASSERT_NEAR_FP(p.y_m, 0.0, 0.001, "perspective Y at y=0");

    homography_deinit(ctx);
    printf("PASS test_perspective_projection\n");
    return 0;
}

/** Test 6: Denominator guard rejects degenerate points */
static int test_denominator_guard(void) {
    homography_ctx_t *ctx = homography_init(PERSPECTIVE_H);
    ASSERT_TRUE(ctx != NULL, "init should succeed");

    /* Find a pixel where denominator approaches zero:
     * denom = 1 + 0.01*x. This never reaches 0 for x >= 0, but at large
     * negative x it would. Use a perspective H with h22 = 0 to test the guard. */
    homography_deinit(ctx);

    const float DEGEN_H[9] = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        1.0f, 0.0f, 0.0f   /* denom = x */
    };
    ctx = homography_init(DEGEN_H);
    ASSERT_TRUE(ctx != NULL, "init should succeed");

    HomPoint p;
    /* denom = x = 0 -> degenerate */
    ASSERT_TRUE(homography_project(ctx, 0, 5, &p), "project should return true");
    ASSERT_TRUE(!p.valid, "point at denom=0 should be invalid");

    /* denom = x = 100 -> valid */
    ASSERT_TRUE(homography_project(ctx, 100, 5, &p), "point at denom!=0 should be valid");
    ASSERT_TRUE(p.valid, "point at denom!=0 should be valid");

    homography_deinit(ctx);

    /* Test threshold just below HOM_DENOM_MIN_FP (655 in Q16.16) */
    const float SMALL_DENOM_H[9] = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 0.005f /* h22 in Q16.16 is 327 < 655 */
    };
    ctx = homography_init(SMALL_DENOM_H);
    ASSERT_TRUE(ctx != NULL, "init should succeed");
    ASSERT_TRUE(homography_project(ctx, 0, 0, &p), "project should succeed");
    ASSERT_TRUE(!p.valid, "denominator below 655 should be marked invalid");
    homography_deinit(ctx);

    printf("PASS test_denominator_guard\n");
    return 0;
}

/** Test 7: Constant motion yields constant velocity */
static int test_constant_velocity(void) {
    homography_ctx_t *ctx = homography_init(SCALE_H);
    ASSERT_TRUE(ctx != NULL, "init should succeed");

    /* Object moves 10 pixels in X per frame = 5 m. dt = 50ms.
     * Velocity should be 5 / 0.05 = 100 m/s. */
    Kinematics k;
    int64_t dt_us = 50000;

    for (int i = 0; i < 5; i++) {
        int32_t curr_x = 100 + i * 10;
        int32_t prev_x = 100 + (i - 1) * 10;
        bool ok = homography_kinematics_update(ctx, curr_x, 50, prev_x, 50, dt_us, &k, NULL);
        ASSERT_TRUE(ok, "kinematics update should succeed");
    }

    /* After warm-up, velocity should converge toward 100 m/s */
    ASSERT_NEAR_FP(k.vx, 100.0, 2.0, "constant velocity X");
    ASSERT_NEAR_FP(k.vy, 0.0, 1.0, "zero velocity Y");
    ASSERT_NEAR_FP(k.ax, 0.0, 5.0, "zero acceleration X");
    ASSERT_NEAR_FP(k.jx, 0.0, 10.0, "zero jerk X");

    homography_deinit(ctx);
    printf("PASS test_constant_velocity\n");
    return 0;
}

/** Test 8: Accelerating motion produces positive acceleration */
static int test_acceleration(void) {
    homography_ctx_t *ctx = homography_init(SCALE_H);
    ASSERT_TRUE(ctx != NULL, "init should succeed");

    /* Object accelerates: each frame velocity increases by 10 px/frame.
     * Positions: 0, 10, 30, 60, 100 (increasing step). */
    Kinematics k;
    int64_t dt_us = 100000; /* 100 ms */
    int32_t positions[] = { 0, 10, 30, 60, 100 };
    int32_t prev_x = positions[0];

    for (int i = 1; i < 5; i++) {
        int32_t curr_x = positions[i];
        bool ok = homography_kinematics_update(ctx, curr_x, 0, prev_x, 0, dt_us, &k, NULL);
        ASSERT_TRUE(ok, "kinematics update should succeed");
        prev_x = curr_x;
    }

    /* With acceleration, velocity should be increasing */
    ASSERT_TRUE(hom_fp_to_float(k.vx) > 0, "velocity should be positive");
    ASSERT_TRUE(hom_fp_to_float(k.ax) > 0, "acceleration should be positive");

    homography_deinit(ctx);
    printf("PASS test_acceleration\n");
    return 0;
}

/** Test 9: EWMA filter suppresses noise */
static int test_ewma_smoothing(void) {
    /* Compare: raw velocity (no filter) vs filtered velocity */
    homography_ctx_t *ctx = homography_init(SCALE_H);
    ASSERT_TRUE(ctx != NULL, "init should succeed");

    /* Apply noisy positions: true velocity 50 m/s but with alternating jitter.
     * The EWMA should produce a smoother, more stable velocity. */
    Kinematics k;
    int64_t dt_us = 100000;
    int32_t jitter[] = { 10, -10, 10, -10, 10 };
    int32_t curr_x = 0, prev_x = -10; /* base 10 px/frame = 5m/0.1s = 50 m/s */

    for (int i = 0; i < 5; i++) {
        curr_x = (i + 1) * 10 + jitter[i];
        prev_x = i * 10 + jitter[i];
        bool ok = homography_kinematics_update(ctx, curr_x, 0, prev_x, 0, dt_us, &k, NULL);
        ASSERT_TRUE(ok, "kinematics update should succeed");
    }

    /* Filtered velocity should be within reasonable bounds of 50 m/s */
    float vx = hom_fp_to_float(k.vx);
    ASSERT_TRUE(vx > 30 && vx < 70, "filtered velocity should be near 50 m/s");

    homography_deinit(ctx);
    printf("PASS test_ewma_smoothing\n");
    return 0;
}

/** Test 10: Null/invalid inputs handled gracefully */
static int test_null_inputs(void) {
    HomPoint p;
    homography_ctx_t *ctx = homography_init(IDENTITY_H);

    ASSERT_TRUE(homography_init(NULL) == NULL, "init(NULL) should fail");
    ASSERT_TRUE(!homography_project(ctx, 10, 10, NULL), "project with NULL out should fail");
    ASSERT_TRUE(!homography_project(NULL, 10, 10, &p), "project with NULL ctx should fail");

    Kinematics k;
    ASSERT_TRUE(!homography_kinematics_update(NULL, 10, 10, 0, 0, 100000, &k, NULL),
                "kinematics with NULL ctx should fail");
    ASSERT_TRUE(!homography_kinematics_update(ctx, 10, 10, 0, 0, 100000, NULL, NULL),
                "kinematics with NULL out should fail");
    ASSERT_TRUE(!homography_kinematics_update(ctx, 10, 10, 0, 0, 0, &k, NULL),
                "kinematics with dt=0 should fail");

    homography_deinit(ctx);
    printf("PASS test_null_inputs\n");
    return 0;
}

static int test_motion_energy(void) {
    const int GRID_COLS = 10;
    const int GRID_ROWS = 7;
    const int NUM_BLOCKS = GRID_COLS * GRID_ROWS;

    // Initialize 70 homography trackers
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

    // Scenario 3: Test num_blocks > NUM_BLOCKS rejected
    ok = homography_compute_motion_energy(
        trackers, dx, dy, confidence, NUM_BLOCKS + 1, 40000,
        1.0f, 1.0f, 1.0f, 10.0f, 1.0f, 1.0f, &energy
    );
    if (ok) {
        printf("FAIL: expected num_blocks > NUM_BLOCKS to return false\n");
        for (int j = 0; j < NUM_BLOCKS; j++) homography_deinit(trackers[j]);
        return 1;
    }

    // Scenario 4: Test negative/invalid lambda and refs rejected
    ok = homography_compute_motion_energy(
        trackers, dx, dy, confidence, NUM_BLOCKS, 40000,
        -1.0f, 1.0f, 1.0f, 10.0f, 1.0f, 1.0f, &energy
    );
    if (ok) {
        printf("FAIL: expected negative lambda to return false\n");
        for (int j = 0; j < NUM_BLOCKS; j++) homography_deinit(trackers[j]);
        return 1;
    }

    ok = homography_compute_motion_energy(
        trackers, dx, dy, confidence, NUM_BLOCKS, 40000,
        1.0f, 1.0f, 1.0f, -10.0f, 1.0f, 1.0f, &energy
    );
    if (ok) {
        printf("FAIL: expected negative v_ref to return false\n");
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

static int test_time_to_collision(void) {
    float ttc = -1.0f;

    // Test 1: Converging head-on (d=100m, v_rel=20m/s -> TTC=5.0s)
    bool ok = homography_compute_ttc(0.0f, 0.0f, 10.0f, 0.0f,
                                     100.0f, 0.0f, -10.0f, 0.0f,
                                     &ttc);
    if (!ok || fabsf(ttc - 5.0f) > 1e-3f) {
        printf("FAIL: expected TTC=5.0s, got %f (ok=%d)\n", ttc, ok);
        return 1;
    }

    // Test 2: Diverging entities (d=100m, moving apart -> TTC=999.0s)
    ok = homography_compute_ttc(0.0f, 0.0f, -10.0f, 0.0f,
                                100.0f, 0.0f, 10.0f, 0.0f,
                                &ttc);
    if (!ok || fabsf(ttc - 999.0f) > 1e-3f) {
        printf("FAIL: expected diverging TTC=999.0s, got %f\n", ttc);
        return 1;
    }

    // Test 3: Parallel motion (same velocity vector -> TTC=999.0s)
    ok = homography_compute_ttc(0.0f, 0.0f, 10.0f, 0.0f,
                                0.0f, 10.0f, 10.0f, 0.0f,
                                &ttc);
    if (!ok || fabsf(ttc - 999.0f) > 1e-3f) {
        printf("FAIL: expected parallel TTC=999.0s, got %f\n", ttc);
        return 1;
    }

    // Test 4: Stationary points (zero velocity -> TTC=999.0s)
    ok = homography_compute_ttc(0.0f, 0.0f, 0.0f, 0.0f,
                                20.0f, 20.0f, 0.0f, 0.0f,
                                &ttc);
    if (!ok || fabsf(ttc - 999.0f) > 1e-3f) {
        printf("FAIL: expected stationary TTC=999.0s, got %f\n", ttc);
        return 1;
    }

    // Test 5: Coincident entities (dist=0 -> TTC=0.0s)
    ok = homography_compute_ttc(5.0f, 5.0f, 1.0f, 1.0f,
                                5.0f, 5.0f, -1.0f, -1.0f,
                                &ttc);
    if (!ok || fabsf(ttc - 0.0f) > 1e-3f) {
        printf("FAIL: expected coincident TTC=0.0s, got %f\n", ttc);
        return 1;
    }

    // Test 6: Null pointer defensive guard
    ok = homography_compute_ttc(0.0f, 0.0f, 1.0f, 0.0f, 10.0f, 0.0f, -1.0f, 0.0f, NULL);
    if (ok != false) {
        printf("FAIL: expected false on null pointer\n");
        return 1;
    }

    printf("PASS test_time_to_collision\n");
    return 0;
}

int main(void) {
    printf("=== Homography & Kinematics Unit Tests ===\n");
    int failures = 0;

    failures += test_fixed_point_conversions();
    failures += test_fixed_point_arith();
    failures += test_identity_projection();
    failures += test_scale_projection();
    failures += test_perspective_projection();
    failures += test_denominator_guard();
    failures += test_constant_velocity();
    failures += test_acceleration();
    failures += test_ewma_smoothing();
    failures += test_null_inputs();
    failures += test_motion_energy();
    failures += test_time_to_collision();

    printf("\n=== Results: %d failures ===\n", failures);
    return failures;
}