/**
 * @file camera_capture.h
 * @brief ESP32-S3 Camera Capture Driver for PhysEdge-Cloud L1 Edge Gate
 *
 * Configures the camera sensor for QVGA (320x240) grayscale capture
 * and provides double-buffered frame acquisition.
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_camera.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Target capture resolution */
#define CAPTURE_WIDTH    320
#define CAPTURE_HEIGHT   240
#define CAPTUREPixelFormat PIXFORMAT_GRAYSCALE

/** Double-buffer frame count */
#define FRAME_BUFFER_COUNT 2

/**
 * @brief Grayscale frame buffer descriptor
 */
typedef struct {
    uint8_t *buffer;    /**< Pixel data (uint8 grayscale) */
    uint32_t width;     /**< Frame width in pixels */
    uint32_t height;    /**< Frame height in pixels */
    uint32_t stride;    /**< Bytes per row (may include padding) */
    uint64_t timestamp_us; /**< Capture timestamp in microseconds */
} GrayscaleFrame;

/**
 * @brief Camera capture context (opaque)
 */
typedef struct camera_capture_ctx camera_capture_ctx_t;

/**
 * @brief Initialize the camera capture driver
 *
 * Configures the ESP32 camera sensor for QVGA grayscale capture
 * with double-buffered frame acquisition.
 *
 * @return Pointer to capture context, or NULL on failure
 */
camera_capture_ctx_t *camera_capture_init(void);

/**
 * @brief Acquire a frame from the camera
 *
 * Blocks until a new frame is available. The caller must call
 * camera_capture_release() when done with the frame.
 *
 * @param ctx Capture context from camera_capture_init()
 * @param frame Output frame descriptor
 * @return true on success, false on error
 */
bool camera_capture_acquire(camera_capture_ctx_t *ctx, GrayscaleFrame *frame);

/**
 * @brief Release a previously acquired frame
 *
 * Returns the frame buffer to the capture pool for reuse.
 *
 * @param ctx Capture context
 * @param frame Frame to release
 */
void camera_capture_release(camera_capture_ctx_t *ctx, GrayscaleFrame *frame);

/**
 * @brief Deinitialize and free the camera capture driver
 *
 * @param ctx Capture context to free
 */
void camera_capture_deinit(camera_capture_ctx_t *ctx);

#ifdef __cplusplus
}
#endif
