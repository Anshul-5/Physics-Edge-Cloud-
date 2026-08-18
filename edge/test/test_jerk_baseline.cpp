#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "jerk_baseline.h"

int main() {
    printf("Running jerk baseline tests...\n");

    // Init context with alpha=0.1, threshold=3.0, trigger on 3 out of 5 spikes
    jerk_ctx_t *ctx = jerk_baseline_init(0.1f, 3.0f, 3, 5);
    if (!ctx) {
        printf("Failed to init context\n");
        return 1;
    }

    int hour = 14; // Arbitrary 2pm bin
    float surprise = 0.0f;
    bool triggered = false;

    // 1. Bootstrap Phase: Send 10 normal samples
    for (int i = 0; i < 10; i++) {
        triggered = jerk_baseline_update(ctx, hour, 2.0f + (i % 2)*0.1f, &surprise);
        if (triggered) {
            printf("FAIL: Triggered during bootstrap\n");
            return 1;
        }
    }

    // 2. Normal EWMA Update Phase: Send 50 normal samples (values around 2.0)
    for (int i = 0; i < 50; i++) {
        float noise = ((rand() % 100) / 100.0f) * 0.2f - 0.1f;
        triggered = jerk_baseline_update(ctx, hour, 2.0f + noise, &surprise);
        if (triggered) {
            printf("FAIL: Triggered on normal noise (surprise=%.2f)\n", surprise);
            return 1;
        }
    }

    // 3. Single Spike Test: Should not trigger (since 3/5 gating is active)
    triggered = jerk_baseline_update(ctx, hour, 15.0f, &surprise);
    if (triggered) {
        printf("FAIL: Triggered on single isolated spike\n");
        return 1;
    }
    printf("Single spike handled correctly (surprise=%.2f)\n", surprise);

    // 4. Send normal sample to clear spike
    jerk_baseline_update(ctx, hour, 2.0f, &surprise);

    // 5. Sustained Spike Test: 3 consecutive anomalies should trigger
    int anomalies = 0;
    for (int i = 0; i < 3; i++) {
        triggered = jerk_baseline_update(ctx, hour, 20.0f, &surprise);
        if (triggered) anomalies++;
    }

    if (anomalies == 0) {
        printf("FAIL: Did not trigger on sustained anomaly\n");
        return 1;
    }

    printf("PASS: Jerk Baseline Tests\n");
    jerk_baseline_deinit(ctx);
    return 0;
}
