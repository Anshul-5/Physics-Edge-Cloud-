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

bool uplink_buffer_push(ring_buffer_t *rb, buffer_entry_t *entry) {
    if (!rb || !entry) return false;
    
    // If full, we overwrite the oldest (tail)
    if (rb->count == rb->capacity) {
        // Free old memory inside the entry before overwriting
        free(rb->entries[rb->tail].frame_data);
        free(rb->entries[rb->tail].flow_vectors);
        
        rb->tail = (rb->tail + 1) % rb->capacity;
        rb->count--;
    }
    
    // Deep copy into the head
    buffer_entry_t *dest = &rb->entries[rb->head];
    dest->timestamp = entry->timestamp;
    dest->suspicion = entry->suspicion;
    dest->jerk = entry->jerk;
    dest->frame_size = entry->frame_size;
    dest->flow_count = entry->flow_count;
    
    if (entry->frame_size > 0 && entry->frame_data) {
        dest->frame_data = static_cast<uint8_t*>(malloc(entry->frame_size));
        if (dest->frame_data) {
            memcpy(dest->frame_data, entry->frame_data, entry->frame_size);
        }
    } else {
        dest->frame_data = NULL;
    }
    
    if (entry->flow_count > 0 && entry->flow_vectors) {
        size_t flow_bytes = entry->flow_count * 8; // Assuming 8 bytes per flow vector
        dest->flow_vectors = malloc(flow_bytes);
        if (dest->flow_vectors) {
            memcpy(dest->flow_vectors, entry->flow_vectors, flow_bytes);
        }
    } else {
        dest->flow_vectors = NULL;
    }
    
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
