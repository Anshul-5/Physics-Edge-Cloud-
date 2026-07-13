/**
 * @file main.c
 * @brief PhysEdge-Cloud L1 Edge Gate - Main Entry Point
 *
 * Initializes camera capture and downscaler, then runs the main
 * frame acquisition loop: capture -> downscale -> output.
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_timer.h"

#include "camera_capture.h"
#include "downscaler.h"

static const char *TAG = "l1_gate";

/** Pre-allocated output buffer (19.2 KB in PSRAM) */
static uint8_t scaled_buffer[DOWNSCALED_BUF_SIZE];

void app_main(void) {
    ESP_LOGI(TAG, "=== PhysEdge-Cloud L1 Edge Gate ===");
    ESP_LOGI(TAG, "ESP32-S3 @ %d MHz", CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_240);

    /* Initialize camera */
    camera_capture_ctx_t *cam = camera_capture_init();
    if (!cam) {
        ESP_LOGE(TAG, "Camera init failed, halting");
        vTaskDelay(portMAX_DELAY);
        return;
    }

    /* Initialize downscaler with pre-allocated buffer */
    downscaler_ctx_t *scaler = downscaler_init(scaled_buffer);
    if (!scaler) {
        ESP_LOGE(TAG, "Downscaler init failed, halting");
        camera_capture_deinit(cam);
        vTaskDelay(portMAX_DELAY);
        return;
    }

    ESP_LOGI(TAG, "Pipeline ready: 320x240 -> 160x120 INT8 bilinear");
    ESP_LOGI(TAG, "Output buffer: %d bytes (%.1f KB)",
             DOWNSCALED_BUF_SIZE, DOWNSCALED_BUF_SIZE / 1024.0f);

    /* Main frame loop */
    GrayscaleFrame raw_frame;
    uint32_t frame_count = 0;
    uint32_t total_us = 0;

    while (1) {
        int64_t t0 = esp_timer_get_time();

        /* Acquire raw frame */
        if (!camera_capture_acquire(cam, &raw_frame)) {
            ESP_LOGW(TAG, "Frame acquisition failed, skipping");
            continue;
        }

        /* Build input descriptor */
        InputFrame input = {
            .buffer = raw_frame.buffer,
            .width  = raw_frame.width,
            .height = raw_frame.height,
            .stride = raw_frame.stride,
        };

        /* Downscale */
        const uint8_t *scaled = downscale_bilinear(scaler, &input);

        int64_t t1 = esp_timer_get_time();
        uint32_t elapsed_us = (uint32_t)(t1 - t0);
        total_us += elapsed_us;
        frame_count++;

        if (frame_count % 50 == 0) {
            float avg_ms = (total_us / (float)frame_count) / 1000.0f;
            ESP_LOGI(TAG, "Frame %lu: %lu us (%.2f ms avg) | buf=%p",
                     frame_count, elapsed_us, avg_ms, (void *)scaled);
        }

        /* Release raw frame */
        camera_capture_release(cam, &raw_frame);

        /* Yield to other tasks */
        taskYIELD();
    }
}
