#ifndef PHYSEDGE_OTA_SECURITY_H
#define PHYSEDGE_OTA_SECURITY_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

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

typedef enum {
    OTA_HDR_OK = 0,
    OTA_HDR_ERR_NULL = -1,
    OTA_HDR_ERR_BAD_MAGIC = -2,
    OTA_HDR_ERR_BAD_SIZE = -3,
    OTA_HDR_ERR_OUT_OF_BOUNDS = -4,
} ota_hdr_result_t;

/**
 * @brief Validates image security version against hardware monotonic counter.
 * 
 * @param hardware_counter Current monotonic security counter burned in hardware.
 * @param image_version Security counter embedded in the OTA binary header.
 * @return int 0 if valid (image_version >= hardware_counter), -1 if rollback rejected.
 */
int ota_validate_rollback_version(uint32_t hardware_counter, uint32_t image_version);

/**
 * @brief Validates header magic bytes (format sanity check only).
 * 
 * @note This is a format check, not cryptographic verification.
 * For cryptographic verification, use secure_ota_verify_signature().
 * 
 * @param header Pointer to the parsed OTA header.
 * @return true if valid magic, false otherwise.
 */
bool ota_validate_header_magic(const ota_header_t *header);

/**
 * @brief Performs structural validation of the full OTA header.
 *
 * Checks magic constant, minimum size, and validates that payload_size
 * fits safely within image_len without integer overflow.
 *
 * @param header Pointer to the parsed OTA header.
 * @param image_len Total size of the received OTA image buffer.
 * @return OTA_HDR_OK on success, or an appropriate error code.
 */
ota_hdr_result_t ota_validate_header(const ota_header_t *header, size_t image_len);

#ifdef __cplusplus
}
#endif

#endif // PHYSEDGE_OTA_SECURITY_H
