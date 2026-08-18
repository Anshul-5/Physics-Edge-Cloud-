#ifndef JERK_BASELINE_H
#define JERK_BASELINE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NUM_TIME_BINS 24

typedef struct {
    float mu;
    float var;
    uint32_t count;
} time_bin_stats_t;

typedef struct {
    time_bin_stats_t bins[NUM_TIME_BINS];
    
    float alpha;
    float surprise_threshold;
    int trigger_m;
    int trigger_k;

    /* History window for k-of-m gating */
    bool history[32];
    int history_idx;
} jerk_ctx_t;

jerk_ctx_t *jerk_baseline_init(float alpha, float threshold, int k, int m);

/* Process a new jerk magnitude and return true if an anomaly trigger is met */
bool jerk_baseline_update(jerk_ctx_t *ctx, int hour_of_day, float jerk_mag, float *out_surprise);

void jerk_baseline_deinit(jerk_ctx_t *ctx);

#ifdef __cplusplus
}
#endif

#endif // JERK_BASELINE_H
