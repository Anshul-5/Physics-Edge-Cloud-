#include <stdint.h>
#include <stddef.h>
#include "uplink_buffer.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < sizeof(MotionVector)) return 0;
    
    uplink_buffer_ctx_t *ctx = uplink_buffer_init();
    if (!ctx) return 0;
    
    size_t num_vectors = size / sizeof(MotionVector);
    const MotionVector *vectors = (const MotionVector *)data;
    
    for (size_t i = 0; i < num_vectors && i < 100; i++) {
        uplink_buffer_push(ctx, &vectors[i]);
    }
    
    MotionVector popped;
    while (uplink_buffer_pop(ctx, &popped)) {
    }
    
    uplink_buffer_deinit(ctx);
    return 0;
}
