#include "uplink_buffer.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

ring_buffer_t* uplink_buffer_init(int capacity) {
    if (capacity <= 0) return NULL;
    
    // Simulate heap_caps_malloc(..., MALLOC_CAP_SPIRAM) for ESP32 PSRAM
    ring_buffer_t *rb = static_cast<ring_buffer_t*>(malloc(sizeof(ring_buffer_t)));
    if (!rb) return NULL;
    
    rb->entries = static_cast<buffer_entry_t*>(calloc(capacity, sizeof(buffer_entry_t)));
    if (!rb->entries) {
        free(rb);
        return NULL;
    }
    
    rb->capacity = capacity;
    rb->head = 0;
    rb->tail = 0;
    rb->count = 0;
    
    return rb;
}

bool uplink_buffer_push(ring_buffer_t *rb, const buffer_entry_t *entry) {
    if (!rb || !entry) return false;
    
    uint8_t *new_frame = NULL;
    MotionVector *new_flow = NULL;
    
    // Allocate and copy frame data if present
    if (entry->frame_size > 0 && entry->frame_data) {
        new_frame = static_cast<uint8_t*>(malloc(entry->frame_size));
        if (!new_frame) {
            return false;
        }
        memcpy(new_frame, entry->frame_data, entry->frame_size);
    }
    
    // Allocate and copy flow vectors if present (using true sizeof(MotionVector))
    if (entry->flow_count > 0 && entry->flow_vectors) {
        if (entry->flow_count > UPLINK_MAX_FLOW_BLOCKS) {
            free(new_frame);
            return false;
        }
        size_t flow_bytes = (size_t)entry->flow_count * sizeof(MotionVector);
        new_flow = static_cast<MotionVector*>(malloc(flow_bytes));
        if (!new_flow) {
            free(new_frame);
            return false;
        }
        memcpy(new_flow, entry->flow_vectors, flow_bytes);
    }
    
    // If full, evict the oldest entry (tail)
    if (rb->count == rb->capacity) {
        free(rb->entries[rb->tail].frame_data);
        free(rb->entries[rb->tail].flow_vectors);
        rb->entries[rb->tail].frame_data = NULL;
        rb->entries[rb->tail].flow_vectors = NULL;
        
        rb->tail = (rb->tail + 1) % rb->capacity;
        rb->count--;
    }
    
    // Commit new entry to head
    buffer_entry_t *dest = &rb->entries[rb->head];
    dest->timestamp = entry->timestamp;
    dest->suspicion = entry->suspicion;
    dest->jerk = entry->jerk;
    dest->frame_data = new_frame;
    dest->frame_size = new_frame ? entry->frame_size : 0;
    dest->flow_vectors = new_flow;
    dest->flow_count = new_flow ? entry->flow_count : 0;
    
    rb->head = (rb->head + 1) % rb->capacity;
    rb->count++;
    
    return true;
}

bool uplink_buffer_pop(ring_buffer_t *rb, buffer_entry_t *out_entry) {
    if (!rb || !out_entry || rb->count == 0) return false;
    
    // Extract the oldest entry (tail)
    buffer_entry_t *src = &rb->entries[rb->tail];
    out_entry->timestamp = src->timestamp;
    out_entry->suspicion = src->suspicion;
    out_entry->jerk = src->jerk;
    out_entry->frame_size = src->frame_size;
    out_entry->flow_count = src->flow_count;
    
    // Transfer ownership of the pointers (caller must free)
    out_entry->frame_data = src->frame_data;
    out_entry->flow_vectors = src->flow_vectors;
    
    // Clear the source so it doesn't get double freed
    src->frame_data = NULL;
    src->flow_vectors = NULL;
    
    rb->tail = (rb->tail + 1) % rb->capacity;
    rb->count--;
    
    return true;
}

void uplink_buffer_deinit(ring_buffer_t *rb) {
    if (!rb) return;
    
    // Free all remaining entries in the buffer
    while (rb->count > 0) {
        buffer_entry_t entry;
        if (uplink_buffer_pop(rb, &entry)) {
            free(entry.frame_data);
            free(entry.flow_vectors);
        }
    }
    
    if (rb->entries) {
        free(rb->entries);
    }
    free(rb);
}
