#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "optical_flow.h"

#define OF_FRAME_SIZE (OF_WIDTH * OF_HEIGHT)

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < OF_FRAME_SIZE * 2) return 0;
    
    const uint8_t *curr = data;
    const uint8_t *prev = data + OF_FRAME_SIZE;
    
    optical_flow_ctx_t *ctx = optical_flow_init();
    if (ctx) {
        FlowResult result;
        memset(&result, 0, sizeof(result));
        optical_flow_compute(ctx, curr, prev, &result);
        optical_flow_deinit(ctx);
    }
    
    return 0;
}
