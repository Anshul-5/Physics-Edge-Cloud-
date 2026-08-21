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
