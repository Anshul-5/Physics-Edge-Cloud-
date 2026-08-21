/**
 * @file ota_security.h
 * @brief ESP32-S3 OTA Secure Boot Anti-Rollback & Signature Validation.
 */

#ifndef PHYSEDGE_OTA_SECURITY_H
#define PHYSEDGE_OTA_SECURITY_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define OTA_MAGIC_HEADER 0x50485953 // "PHYS"
#define OTA_SIG_LEN_BYTES 64        // ECDSA secp256r1 (r, s)

typedef struct {
    uint32_t magic;
    uint32_t security_version;  // Monotonic anti-rollback version
    uint32_t payload_size;      // Size of binary payload in bytes
    uint8_t  sha256_digest[32]; // SHA-256 hash of payload
    uint8_t  signature[OTA_SIG_LEN_BYTES]; // ECDSA signature
} __attribute__((packed)) ota_header_t;

/**
 * @brief Validates image security version against hardware monotonic counter.
 * 
 * @param hardware_counter Current monotonic security counter burned in hardware.
 * @param image_version Security counter embedded in the OTA binary header.
 * @return int 0 if valid (image_version >= hardware_counter), -1 if rollback rejected.
 */
int ota_validate_rollback_version(uint32_t hardware_counter, uint32_t image_version);

/**
 * @brief Validates header magic bytes and structure sanity.
 * 
 * @param header Pointer to the parsed OTA header.
 * @return true if valid magic, false otherwise.
 */
bool ota_validate_header_magic(const ota_header_t *header);

#ifdef __cplusplus
}
#endif

#endif // PHYSEDGE_OTA_SECURITY_H
