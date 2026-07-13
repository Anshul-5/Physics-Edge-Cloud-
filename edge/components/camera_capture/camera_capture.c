/**
 * @file camera_capture.c
 * @brief ESP32-S3 Camera Capture Driver Implementation
 *
 * Configures OV2640/OV5640 sensor for QVGA (320x240) grayscale capture
 * with double-buffered frame acquisition using esp_camera API.
 */

#include "camera_capture.h"

#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_camera.h"
#include "esp_timer.h"

static const char *TAG = "cam_capture";

/** Internal capture context */
struct camera_capture_ctx {
    SemaphoreHandle_t frame_ready;  /**< Signals when a new frame is available */
    GrayscaleFrame buffers[FRAME_BUFFER_COUNT];
    uint8_t write_idx;              /**< Index of the next buffer to write */
};

/**
 * @brief Configure camera sensor for QVGA grayscale
 */
static bool configure_sensor(void) {
    /*
     * Pin assignments for common ESP32-S3 camera boards (e.g., ESP-S3-CAM).
     * Adjust these for your specific hardware.
     */
    camera_config_t config = {
        .pin_pwdn     = -1,   /* GPIO_NUM_NC */
        .pin_reset    = -1,   /* GPIO_NUM_NC */
        .pin_xclk     = 15,
        .pin_sccb_sda = 4,
        .pin_sccb_scl = 5,
        .pin_d7       = 16,
        .pin_d6       = 17,
        .pin_d5       = 18,
        .pin_d4       = 12,
        .pin_d3       = 10,
        .pin_d2       = 8,
        .pin_d1       = 14,
        .pin_d0       = 13,
        .pin_vsync    = 6,
        .pin_href     = 7,
        .pin_pclk     = 11,
        .xclk_freq_hz = 20000000,
        .ledc_timer   = LEDC_TIMER_0,
        .ledc_channel = LEDC_CHANNEL_0,
        .pixel_format = CAPTUREPixelFormat,
        .frame_size   = FRAMESIZE_QVGA,
        .jpeg_quality = 12,
        .fb_count     = FRAME_BUFFER_COUNT,
        .fb_location  = CAMERA_FB_IN_PSRAM,
        .grab_mode    = CAMERA_GRAB_LATEST,
    };

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera init failed: %s", esp_err_to_name(err));
        return false;
    }

    /* Tune sensor for low-latency grayscale */
    sensor_t *sensor = esp_camera_sensor_get();
    if (sensor) {
        sensor->set_brightness(sensor, 0);
        sensor->set_contrast(sensor, 0);
        sensor->set_saturation(sensor, -2);   /* Reduce saturation for grayscale */
        sensor->set_quality(sensor, 10);       /* Low JPEG quality (unused in grayscale) */
        sensor->set_framesize(sensor, FRAMESIZE_QVGA);
        sensor->set_pixformat(sensor, PIXFORMAT_GRAYSCALE);
        ESP_LOGI(TAG, "Sensor tuned for QVGA grayscale");
    }

    return true;
}

camera_capture_ctx_t *camera_capture_init(void) {
    camera_capture_ctx_t *ctx = calloc(1, sizeof(camera_capture_ctx_t));
    if (!ctx) {
        ESP_LOGE(TAG, "Failed to allocate capture context");
        return NULL;
    }

    ctx->frame_ready = xSemaphoreCreateBinary();
    if (!ctx->frame_ready) {
        ESP_LOGE(TAG, "Failed to create semaphore");
        free(ctx);
        return NULL;
    }

    /* Allocate double buffers in PSRAM for large frames */
    const size_t frame_bytes = CAPTURE_WIDTH * CAPTURE_HEIGHT;
    for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
        ctx->buffers[i].buffer = heap_caps_malloc(frame_bytes, MALLOC_CAP_SPIRAM);
        if (!ctx->buffers[i].buffer) {
            /* Fallback to internal SRAM if PSRAM unavailable */
            ctx->buffers[i].buffer = malloc(frame_bytes);
        }
        if (!ctx->buffers[i].buffer) {
            ESP_LOGE(TAG, "Failed to allocate frame buffer %d", i);
            camera_capture_deinit(ctx);
            return NULL;
        }
        ctx->buffers[i].width  = CAPTURE_WIDTH;
        ctx->buffers[i].height = CAPTURE_HEIGHT;
        ctx->buffers[i].stride = CAPTURE_WIDTH;
    }
    ctx->write_idx = 0;

    if (!configure_sensor()) {
        camera_capture_deinit(ctx);
        return NULL;
    }

    ESP_LOGI(TAG, "Camera capture initialized: %dx%d grayscale, %d buffers",
             CAPTURE_WIDTH, CAPTURE_HEIGHT, FRAME_BUFFER_COUNT);
    return ctx;
}

bool camera_capture_acquire(camera_capture_ctx_t *ctx, GrayscaleFrame *frame) {
    if (!ctx || !frame) return false;

    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        ESP_LOGE(TAG, "Failed to acquire camera frame");
        return false;
    }

    /* Copy into our double buffer */
    GrayscaleFrame *dest = &ctx->buffers[ctx->write_idx];
    size_t copy_size = fb->len;
    if (copy_size > CAPTURE_WIDTH * CAPTURE_HEIGHT) {
        copy_size = CAPTURE_WIDTH * CAPTURE_HEIGHT;
    }
    memcpy(dest->buffer, fb->buf, copy_size);
    dest->timestamp_us = esp_timer_get_time();

    esp_camera_fb_return(fb);

    /* Swap write index */
    ctx->write_idx = (ctx->write_idx + 1) % FRAME_BUFFER_COUNT;

    /* Output the frame we just wrote */
    *frame = *dest;
    return true;
}

void camera_capture_release(camera_capture_ctx_t *ctx, GrayscaleFrame *frame) {
    /* Buffer is copied on acquire, so release is a no-op */
    (void)ctx;
    (void)frame;
}

void camera_capture_deinit(camera_capture_ctx_t *ctx) {
    if (!ctx) return;

    esp_camera_deinit();

    for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
        if (ctx->buffers[i].buffer) {
            if (heap_caps_get_allocated_size(ctx->buffers[i].buffer)) {
                heap_caps_free(ctx->buffers[i].buffer);
            } else {
                free(ctx->buffers[i].buffer);
            }
            ctx->buffers[i].buffer = NULL;
        }
    }

    if (ctx->frame_ready) {
        vSemaphoreDelete(ctx->frame_ready);
    }

    free(ctx);
    ESP_LOGI(TAG, "Camera capture deinitialized");
}
