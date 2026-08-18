idf_component_register(
    SRCS "main.cpp"
    INCLUDE_DIRS "."
    REQUIRES camera_capture downscaler optical_flow homography esp_timer espressif__esp32-camera
)
