#include "jerk_baseline.h"
#include <stdlib.h>
#include <math.h>

#define EPSILON 1e-6f

jerk_ctx_t *jerk_baseline_init(float alpha, float threshold, int k, int m) {
    if (k > m || m > 32 || k <= 0 || m <= 0) return NULL;
    if (!isfinite(alpha) || alpha <= 0.0f || alpha >= 1.0f) return NULL;
    if (!isfinite(threshold) || threshold <= 0.0f) return NULL;

    jerk_ctx_t *ctx = static_cast<jerk_ctx_t*>(calloc(1, sizeof(jerk_ctx_t)));
    if (!ctx) return NULL;

    ctx->alpha = alpha;
    ctx->surprise_threshold = threshold;
    ctx->trigger_k = k;
    ctx->trigger_m = m;
    ctx->history_idx = 0;

    for (int i = 0; i < NUM_TIME_BINS; i++) {
        ctx->bins[i].mu = 0.0f;
        ctx->bins[i].var = 0.0f;
        ctx->bins[i].count = 0;
    }

    return ctx;
}

bool jerk_baseline_update(jerk_ctx_t *ctx, int hour_of_day, float jerk_mag, float *out_surprise) {
    if (!ctx || !isfinite(jerk_mag) || hour_of_day < 0 || hour_of_day >= NUM_TIME_BINS) return false;

    time_bin_stats_t *bin = &ctx->bins[hour_of_day];
    float surprise = 0.0f;

    if (bin->count < 10) {
        /* Bootstrapping phase: simple rolling average */
        bin->count++;
        float delta = jerk_mag - bin->mu;
        bin->mu += delta / bin->count;
        bin->var += delta * (jerk_mag - bin->mu);
        if (out_surprise) *out_surprise = 0.0f;
        return false;
    }

    /* Compute standard surprise BEFORE updating (prevents single huge spikes from masking themselves) */
    float variance = bin->var / bin->count;
    float std_dev = sqrtf(variance + EPSILON);
    surprise = fabsf(jerk_mag - bin->mu) / std_dev;

    if (out_surprise) *out_surprise = surprise;

    /* Update baselines using EWMA ONLY if it is not an extreme anomaly (robustness against outliers) */
    if (surprise < ctx->surprise_threshold * 1.5f) {
        float alpha = ctx->alpha;
        float diff = jerk_mag - bin->mu;
        bin->mu = (1.0f - alpha) * bin->mu + alpha * jerk_mag;
        
        float diff_new = jerk_mag - bin->mu;
        float inst_var = diff * diff_new; /* Welford-style variance update component */
        
        /* Update the actual EWMA variance properly */
        variance = (1.0f - alpha) * variance + alpha * inst_var;
        bin->var = variance * bin->count; /* Storing sum of squares instead of variance directly for bootstrapping compatibility */
    }

    /* k-of-m Hysteresis Gating */
    bool is_spike = (surprise > ctx->surprise_threshold);
    
    ctx->history[ctx->history_idx] = is_spike;
    ctx->history_idx = (ctx->history_idx + 1) % ctx->trigger_m;

    int active_count = 0;
    for (int i = 0; i < ctx->trigger_m; i++) {
        if (ctx->history[i]) active_count++;
    }

    return (active_count >= ctx->trigger_k);
}

bool jerk_baseline_apply_constraint(jerk_ctx_t *ctx, float factor) {
    if (!ctx || !isfinite(factor)) {
        return false;
    }
    
    // Poisoning mitigation: Clamp the constraint factor to +/- 25% ([0.75, 1.25]) (OpenSSF Standard)
    float safe_factor = factor;
    if (safe_factor < 0.75f) {
        safe_factor = 0.75f;
    } else if (safe_factor > 1.25f) {
        safe_factor = 1.25f;
    }
    
    float next_threshold = ctx->surprise_threshold * safe_factor;
    if (!isfinite(next_threshold) || next_threshold <= 0.0f) {
        return false;
    }
    
    ctx->surprise_threshold = next_threshold;
    return true;
}

void jerk_baseline_deinit(jerk_ctx_t *ctx) {
    if (ctx) {
        free(ctx);
    }
}
