#include "secure_ota.h"
#include <string.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/err.h>

#define SECURE_OTA_MAGIC "PEOTA"
#define SECURE_OTA_MAGIC_LEN 5

secure_ota_err_t secure_ota_parse_image(const uint8_t *image_data, size_t image_len, secure_ota_header_t *header) {
    if (image_data == NULL || header == NULL) {
        return SECURE_OTA_ERR_NULL_PARAM;
    }
    
    // Minimum image length bounds check to prevent out-of-bounds reads (OpenSSF Standard)
    const size_t min_header_len = SECURE_OTA_MAGIC_LEN + sizeof(uint32_t) + sizeof(uint32_t) + sizeof(uint32_t);
    if (image_len < min_header_len) {
        return SECURE_OTA_ERR_OUT_OF_BOUNDS;
    }
    
    // Verify Magic Bytes
    if (memcmp(image_data, SECURE_OTA_MAGIC, SECURE_OTA_MAGIC_LEN) != 0) {
        return SECURE_OTA_ERR_INVALID_MAGIC;
    }
    
    size_t offset = SECURE_OTA_MAGIC_LEN;
    
    // Read Security Version
    memcpy(&(header->security_version), image_data + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    
    // Read Payload Length
    memcpy(&(header->payload_len), image_data + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    
    // Validate bounds for payload to prevent buffer overread (OpenSSF Standard)
    if (offset + header->payload_len > image_len) {
        return SECURE_OTA_ERR_OUT_OF_BOUNDS;
    }
    header->payload = image_data + offset;
    offset += header->payload_len;
    
    // Read Signature Length
    if (offset + sizeof(uint32_t) > image_len) {
        return SECURE_OTA_ERR_OUT_OF_BOUNDS;
    }
    memcpy(&(header->signature_len), image_data + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    
    // Validate bounds for signature
    if (offset + header->signature_len > image_len) {
        return SECURE_OTA_ERR_OUT_OF_BOUNDS;
    }
    header->signature = image_data + offset;
    
    return SECURE_OTA_SUCCESS;
}

secure_ota_err_t secure_ota_verify_signature(const uint8_t *image_data, size_t image_len, const secure_ota_header_t *header, const char *public_key_pem) {
    if (image_data == NULL || header == NULL || public_key_pem == NULL) {
        return SECURE_OTA_ERR_NULL_PARAM;
    }
    
    // Validate signature length parameter bounds
    if (header->signature_len == 0 || header->signature == NULL) {
        return SECURE_OTA_ERR_INVALID_SIGNATURE;
    }
    
    // Initialize OpenSSL BIO to read PEM key
    BIO *bio = BIO_new_mem_buf(public_key_pem, -1);
    if (bio == NULL) {
        return SECURE_OTA_ERR_KEY_FAILED;
    }
    
    EVP_PKEY *pkey = PEM_read_bio_PUBKEY(bio, NULL, NULL, NULL);
    BIO_free(bio);
    if (pkey == NULL) {
        return SECURE_OTA_ERR_KEY_FAILED;
    }
    
    // signed_data_len represents Magic + Security Version + Payload Len + Payload
    size_t signed_data_len = SECURE_OTA_MAGIC_LEN + sizeof(uint32_t) + sizeof(uint32_t) + header->payload_len;
    if (signed_data_len > image_len) {
        EVP_PKEY_free(pkey);
        return SECURE_OTA_ERR_OUT_OF_BOUNDS;
    }
    
    // Initialize EVP verification context (using cryptographically secure ECDSA-SHA256 signature verification)
    EVP_MD_CTX *md_ctx = EVP_MD_CTX_new();
    if (md_ctx == NULL) {
        EVP_PKEY_free(pkey);
        return SECURE_OTA_ERR_VERIFY_FAILED;
    }
    
    secure_ota_err_t result = SECURE_OTA_ERR_INVALID_SIGNATURE;
    
    // Perform standard ECDSA-SHA256 signature verification (OpenSSF compliance)
    if (EVP_DigestVerifyInit(md_ctx, NULL, EVP_sha256(), NULL, pkey) == 1) {
        if (EVP_DigestVerifyUpdate(md_ctx, image_data, signed_data_len) == 1) {
            int verify_res = EVP_DigestVerifyFinal(md_ctx, header->signature, header->signature_len);
            if (verify_res == 1) {
                result = SECURE_OTA_SUCCESS;
            } else if (verify_res == 0) {
                result = SECURE_OTA_ERR_INVALID_SIGNATURE;
            } else {
                result = SECURE_OTA_ERR_VERIFY_FAILED;
            }
        }
    }
    
    EVP_MD_CTX_free(md_ctx);
    EVP_PKEY_free(pkey);
    
    return result;
}

secure_ota_err_t secure_ota_check_rollback(const secure_ota_header_t *header, uint32_t current_security_version) {
    if (header == NULL) {
        return SECURE_OTA_ERR_NULL_PARAM;
    }
    
    // Monotonic anti-rollback protection check
    if (header->security_version < current_security_version) {
        return SECURE_OTA_ERR_ROLLBACK_DETECTED;
    }
    
    return SECURE_OTA_SUCCESS;
}
