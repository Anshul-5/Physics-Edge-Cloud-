#include <stdio.h>
#include <stdlib.h>
#include "uplink_buffer.h"

int main() {
    printf("Running PSRAM Uplink Buffer tests...\n");

    ring_buffer_t *rb = uplink_buffer_init(3);
    if (!rb) {
        printf("FAIL: Init returned NULL\n");
        return 1;
    }

    buffer_entry_t entry;
    entry.timestamp = 1000;
    entry.suspicion = 0.5f;
    entry.jerk = 1.0f;
    entry.frame_size = 10;
    entry.frame_data = (uint8_t*)malloc(10);
    entry.flow_count = 0;
    entry.flow_vectors = NULL;

    // Push 4 times into a capacity 3 buffer (should overwrite first)
    uplink_buffer_push(rb, &entry);
    entry.timestamp = 2000;
    uplink_buffer_push(rb, &entry);
    entry.timestamp = 3000;
    uplink_buffer_push(rb, &entry);
    entry.timestamp = 4000;
    uplink_buffer_push(rb, &entry);

    if (rb->count != 3) {
        printf("FAIL: Count %d != 3\n", rb->count);
        return 1;
    }

    buffer_entry_t out;
    uplink_buffer_pop(rb, &out);
    if (out.timestamp != 2000) {
        printf("FAIL: Expected timestamp 2000, got %llu\n", (unsigned long long)out.timestamp);
        return 1;
    }
    free(out.frame_data);
    
    uplink_buffer_pop(rb, &out);
    if (out.timestamp != 3000) return 1;
    free(out.frame_data);
    
    uplink_buffer_pop(rb, &out);
    if (out.timestamp != 4000) return 1;
    free(out.frame_data);

    if (rb->count != 0) {
        printf("FAIL: Count %d != 0\n", rb->count);
        return 1;
    }
    
    free(entry.frame_data);
    uplink_buffer_deinit(rb);

    printf("PASS: PSRAM Circular Buffer Tests\n");
    return 0;
}
