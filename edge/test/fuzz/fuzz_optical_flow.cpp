#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "optical_flow.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < DOWNSCALED_BUF_SIZE * 2) return 0;
    
    const uint8_t *prev = data;
    const uint8_t *curr = data + DOWNSCALED_BUF_SIZE;
    
    optical_flow_ctx_t *ctx = optical_flow_init();
    if (ctx) {
        MotionVector vectors[FLOW_GRID_COLS * FLOW_GRID_ROWS];
        uint32_t flow_count = 0;
        optical_flow_compute(ctx, prev, curr, vectors, &flow_count);
        optical_flow_deinit(ctx);
    }
    
    return 0;
}
