#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "downscaler.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < 16) return 0;
    
    uint32_t w = *(const uint32_t *)(data + 0) % 1024;
    uint32_t h = *(const uint32_t *)(data + 4) % 1024;
    uint32_t stride = *(const uint32_t *)(data + 8) % 2048;
    
    if (w == 0 || h == 0 || stride < w) return 0;
    
    const uint8_t *pixel_data = data + 12;
    size_t pixel_data_size = size - 12;
    
    if (pixel_data_size < (size_t)stride * h) return 0;
    
    InputFrame frame;
    frame.buffer = pixel_data;
    frame.width = w;
    frame.height = h;
    frame.stride = stride;
    
    uint8_t out_buf[DOWNSCALED_BUF_SIZE];
    downscaler_ctx_t *ctx = downscaler_init(out_buf);
    if (ctx) {
        downscale_bilinear(ctx, &frame);
        downscaler_deinit(ctx);
    }
    
    return 0;
}
