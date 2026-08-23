#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "uplink_buffer.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < sizeof(buffer_entry_t)) return 0;
    
    ring_buffer_t *rb = uplink_buffer_init(10);
    if (!rb) return 0;
    
    buffer_entry_t entry;
    memset(&entry, 0, sizeof(entry));
    entry.timestamp = *(const uint64_t *)data;
    entry.suspicion = 0.5f;
    entry.jerk = 1.0f;
    
    uplink_buffer_push(rb, &entry);
    
    buffer_entry_t popped;
    memset(&popped, 0, sizeof(popped));
    uplink_buffer_pop(rb, &popped);
    
    uplink_buffer_deinit(rb);
    return 0;
}
