#ifndef UPLINK_BUFFER_H
#define UPLINK_BUFFER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define UPLINK_MAX_FLOW_BLOCKS 70

#ifndef MOTION_VECTOR_STRUCT_DEFINED
#define MOTION_VECTOR_STRUCT_DEFINED
typedef struct {
    int8_t dx;
    int8_t dy;
    uint8_t confidence;
} MotionVector;
#endif

/**
 * @brief Represents a single frame + flow state entry
 */
typedef struct {
    uint64_t timestamp;
    float suspicion;
    float jerk;
    uint8_t *frame_data;
    uint32_t frame_size;
    MotionVector *flow_vectors;
    uint32_t flow_count;
} buffer_entry_t;

/**
 * @brief Circular ring buffer for telemetry
 *
 * @note Threading Contract: This data structure is NOT internally thread-safe.
 * Concurrent access from multiple FreeRTOS tasks must be serialized by the caller.
 */
typedef struct {
    buffer_entry_t *entries;
    int capacity;
    int head;
    int tail;
    int count;
} ring_buffer_t;

ring_buffer_t* uplink_buffer_init(int capacity);
bool uplink_buffer_push(ring_buffer_t *rb, const buffer_entry_t *entry);
bool uplink_buffer_pop(ring_buffer_t *rb, buffer_entry_t *out_entry);
void uplink_buffer_deinit(ring_buffer_t *rb);

#ifdef __cplusplus
}
#endif

#endif // UPLINK_BUFFER_H
