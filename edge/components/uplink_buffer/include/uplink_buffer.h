#ifndef UPLINK_BUFFER_H
#define UPLINK_BUFFER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Represents a single frame + flow state
typedef struct {
    uint64_t timestamp;
    float suspicion;
    float jerk;
    uint8_t *frame_data;
    uint32_t frame_size;
    void *flow_vectors;
    uint32_t flow_count;
} buffer_entry_t;

typedef struct {
    buffer_entry_t *entries;
    int capacity;
    int head;
    int tail;
    int count;
} ring_buffer_t;

ring_buffer_t* uplink_buffer_init(int capacity);
bool uplink_buffer_push(ring_buffer_t *rb, buffer_entry_t *entry);
bool uplink_buffer_pop(ring_buffer_t *rb, buffer_entry_t *out_entry);
void uplink_buffer_deinit(ring_buffer_t *rb);

#ifdef __cplusplus
}
#endif

#endif // UPLINK_BUFFER_H
