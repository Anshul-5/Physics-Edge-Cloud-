idf_component_register(
    SRCS "camera_capture.c"
    INCLUDE_DIRS "include"
    REQUIRES driver esp_timer espressif__esp32-camera
)
