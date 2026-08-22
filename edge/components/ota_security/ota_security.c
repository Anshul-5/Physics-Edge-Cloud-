/**
 * @file ota_security.c
 * @brief Implementation of ESP32-S3 OTA Anti-Rollback and Header Validation.
 */

#include "ota_security.h"
#include <string.h>

int ota_validate_rollback_version(uint32_t hardware_counter, uint32_t image_version)
{
    // Anti-rollback check: image security counter must be >= hardware counter
    if (image_version < hardware_counter) {
        return -1; // Rollback attack detected
    }
    return 0; // Valid version
}

bool ota_validate_header_magic(const ota_header_t *header)
{
    if (!header) {
        return false;
    }
    return header->magic == OTA_MAGIC_HEADER;
}

ota_hdr_result_t ota_validate_header(const ota_header_t *header, size_t image_len)
{
    if (!header) {
        return OTA_HDR_ERR_NULL;
    }

    if (image_len < sizeof(ota_header_t)) {
        return OTA_HDR_ERR_OUT_OF_BOUNDS;
    }

    if (header->magic != OTA_MAGIC_HEADER) {
        return OTA_HDR_ERR_BAD_MAGIC;
    }

    if (header->payload_size == 0 || header->payload_size > image_len - sizeof(ota_header_t)) {
        return OTA_HDR_ERR_BAD_SIZE;
    }

    return OTA_HDR_OK;
}
