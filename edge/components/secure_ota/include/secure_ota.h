#ifndef SECURE_OTA_H
#define SECURE_OTA_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Return codes for secure OTA operations
typedef enum {
    SECURE_OTA_SUCCESS = 0,
    SECURE_OTA_ERR_INVALID_MAGIC = -1,
    SECURE_OTA_ERR_INVALID_SIGNATURE = -2,
    SECURE_OTA_ERR_ROLLBACK_DETECTED = -3,
    SECURE_OTA_ERR_OUT_OF_BOUNDS = -4,
    SECURE_OTA_ERR_KEY_FAILED = -5,
    SECURE_OTA_ERR_VERIFY_FAILED = -6,
    SECURE_OTA_ERR_NULL_PARAM = -7
} secure_ota_err_t;

// Struct representing the parsed OTA header
typedef struct {
    uint32_t security_version;
    uint32_t payload_len;
    const uint8_t *payload;
    uint32_t signature_len;
    const uint8_t *signature;
} secure_ota_header_t;

/**
 * @brief Parses an OTA image and validates its format.
 * 
 * @param image_data Pointer to the raw image data.
 * @param image_len Length of the image data.
 * @param header Pointer to a secure_ota_header_t struct to populate.
 * @return SECURE_OTA_SUCCESS on success, or an error code.
 */
secure_ota_err_t secure_ota_parse_image(const uint8_t *image_data, size_t image_len, secure_ota_header_t *header);

/**
 * @brief Verifies the ECDSA-SHA256 signature of the OTA image.
 * 
 * @param image_data Pointer to the raw image data.
 * @param image_len Length of the image data.
 * @param header Pointer to the parsed header.
 * @param public_key_pem PEM-encoded ECDSA public key.
 * @return SECURE_OTA_SUCCESS if signature is valid, or an error code.
 */
secure_ota_err_t secure_ota_verify_signature(const uint8_t *image_data, size_t image_len, const secure_ota_header_t *header, const char *public_key_pem);

/**
 * @brief Verifies that the security version is greater than or equal to the current device security version.
 * 
 * @param header Pointer to the parsed header.
 * @param current_security_version Current security version of the device (from EFUSEs).
 * @return SECURE_OTA_SUCCESS if update is allowed, or SECURE_OTA_ERR_ROLLBACK_DETECTED.
 */
secure_ota_err_t secure_ota_check_rollback(const secure_ota_header_t *header, uint32_t current_security_version);

#ifdef __cplusplus
}
#endif

#endif // SECURE_OTA_H
