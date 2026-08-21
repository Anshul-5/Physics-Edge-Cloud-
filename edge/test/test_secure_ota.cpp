/**
 * @file test_secure_ota.cpp
 * @brief Unit tests for secure boot validation & rollback check
 */

#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <stdlib.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/err.h>
#include "secure_ota.h"

// Helper: Generate an ECDSA prime256v1 key pair and return public key PEM and private key
static int generate_key_pair(char **pub_key_pem_out, EVP_PKEY **pkey_out) {
    EVP_PKEY *pkey = EVP_EC_gen("prime256v1");
    if (pkey == NULL) {
        return -1;
    }

    BIO *bio = BIO_new(BIO_s_mem());
    if (bio == NULL) {
        EVP_PKEY_free(pkey);
        return -1;
    }

    if (PEM_write_bio_PUBKEY(bio, pkey) != 1) {
        BIO_free(bio);
        EVP_PKEY_free(pkey);
        return -1;
    }

    char *pub_key_pem = NULL;
    long pub_key_len = BIO_get_mem_data(bio, &pub_key_pem);
    
    char *pub_key_copy = (char *)malloc(pub_key_len + 1);
    memcpy(pub_key_copy, pub_key_pem, pub_key_len);
    pub_key_copy[pub_key_len] = '\0';

    BIO_free(bio);
    *pub_key_pem_out = pub_key_copy;
    *pkey_out = pkey;
    return 0;
}

// Helper: Build a signed OTA image dynamically
static int build_signed_ota_image(EVP_PKEY *pkey, uint32_t security_version, 
                                  const uint8_t *payload, uint32_t payload_len, 
                                  uint8_t **image_out, size_t *image_len_out) {
    // signed data len = Magic (5) + Sec version (4) + Payload Len (4) + Payload
    size_t signed_data_len = 5 + sizeof(uint32_t) + sizeof(uint32_t) + payload_len;
    uint8_t *signed_data = (uint8_t *)malloc(signed_data_len);
    
    // Write Magic
    memcpy(signed_data, "PEOTA", 5);
    size_t offset = 5;
    
    // Write Security Version
    memcpy(signed_data + offset, &security_version, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    
    // Write Payload Len
    memcpy(signed_data + offset, &payload_len, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    
    // Write Payload
    if (payload_len > 0 && payload != NULL) {
        memcpy(signed_data + offset, payload, payload_len);
    }
    
    // Compute ECDSA-SHA256 signature
    EVP_MD_CTX *md_ctx = EVP_MD_CTX_new();
    if (md_ctx == NULL) {
        free(signed_data);
        return -1;
    }
    
    if (EVP_DigestSignInit(md_ctx, NULL, EVP_sha256(), NULL, pkey) != 1) {
        EVP_MD_CTX_free(md_ctx);
        free(signed_data);
        return -1;
    }
    
    if (EVP_DigestSignUpdate(md_ctx, signed_data, signed_data_len) != 1) {
        EVP_MD_CTX_free(md_ctx);
        free(signed_data);
        return -1;
    }
    
    size_t sig_len = 0;
    if (EVP_DigestSignFinal(md_ctx, NULL, &sig_len) != 1) {
        EVP_MD_CTX_free(md_ctx);
        free(signed_data);
        return -1;
    }
    
    uint8_t *signature = (uint8_t *)malloc(sig_len);
    if (EVP_DigestSignFinal(md_ctx, signature, &sig_len) != 1) {
        free(signature);
        EVP_MD_CTX_free(md_ctx);
        free(signed_data);
        return -1;
    }
    
    EVP_MD_CTX_free(md_ctx);
    
    // Final image len = signed data len + Sig Len header (4) + Signature
    size_t final_image_len = signed_data_len + sizeof(uint32_t) + sig_len;
    uint8_t *final_image = (uint8_t *)malloc(final_image_len);
    
    // Copy signed data
    memcpy(final_image, signed_data, signed_data_len);
    offset = signed_data_len;
    
    // Write Signature Len
    uint32_t signature_len_u32 = (uint32_t)sig_len;
    memcpy(final_image + offset, &signature_len_u32, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    
    // Write Signature
    memcpy(final_image + offset, signature, sig_len);
    
    free(signature);
    free(signed_data);
    
    *image_out = final_image;
    *image_len_out = final_image_len;
    return 0;
}

// Test 1: Valid signature and correct security version succeeds
static int test_secure_ota_valid(EVP_PKEY *pkey, const char *pub_key_pem) {
    uint8_t payload[] = "Valid payload data.";
    uint32_t payload_len = sizeof(payload);
    uint32_t security_version = 10;
    
    uint8_t *image_data = NULL;
    size_t image_len = 0;
    
    int build_res = build_signed_ota_image(pkey, security_version, payload, payload_len, &image_data, &image_len);
    assert(build_res == 0);
    
    secure_ota_header_t header;
    secure_ota_err_t err = secure_ota_parse_image(image_data, image_len, &header);
    assert(err == SECURE_OTA_SUCCESS);
    
    err = secure_ota_verify_signature(image_data, image_len, &header, pub_key_pem);
    assert(err == SECURE_OTA_SUCCESS);
    
    // Current device security version = 5. Binary is 10. Update should be allowed.
    err = secure_ota_check_rollback(&header, 5);
    assert(err == SECURE_OTA_SUCCESS);
    
    free(image_data);
    printf("PASS test_secure_ota_valid\n");
    return 0;
}

// Test 2: Invalid Magic bytes fails verification
static int test_secure_ota_invalid_magic(EVP_PKEY *pkey, const char *pub_key_pem) {
    (void)pub_key_pem;
    uint8_t payload[] = "Some data.";
    uint32_t payload_len = sizeof(payload);
    uint8_t *image_data = NULL;
    size_t image_len = 0;
    
    build_signed_ota_image(pkey, 5, payload, payload_len, &image_data, &image_len);
    
    // Tamper with magic bytes
    image_data[0] = 'X';
    
    secure_ota_header_t header;
    secure_ota_err_t err = secure_ota_parse_image(image_data, image_len, &header);
    assert(err == SECURE_OTA_ERR_INVALID_MAGIC);
    
    free(image_data);
    printf("PASS test_secure_ota_invalid_magic\n");
    return 0;
}

// Test 3: Tampered payload data fails signature check
static int test_secure_ota_tampered_payload(EVP_PKEY *pkey, const char *pub_key_pem) {
    uint8_t payload[] = "Valid payload data.";
    uint32_t payload_len = sizeof(payload);
    uint8_t *image_data = NULL;
    size_t image_len = 0;
    
    build_signed_ota_image(pkey, 10, payload, payload_len, &image_data, &image_len);
    
    // Locate payload offset and modify it
    // offset = Magic (5) + Version (4) + Payload Len (4) = 13
    image_data[13] ^= 0xFF; // Flip bits of first payload byte
    
    secure_ota_header_t header;
    secure_ota_err_t err = secure_ota_parse_image(image_data, image_len, &header);
    assert(err == SECURE_OTA_SUCCESS);
    
    err = secure_ota_verify_signature(image_data, image_len, &header, pub_key_pem);
    assert(err == SECURE_OTA_ERR_INVALID_SIGNATURE);
    
    free(image_data);
    printf("PASS test_secure_ota_tampered_payload\n");
    return 0;
}

// Test 4: Tampered security version fails signature verification
static int test_secure_ota_tampered_version(EVP_PKEY *pkey, const char *pub_key_pem) {
    uint8_t payload[] = "Data.";
    uint32_t payload_len = sizeof(payload);
    uint8_t *image_data = NULL;
    size_t image_len = 0;
    
    build_signed_ota_image(pkey, 10, payload, payload_len, &image_data, &image_len);
    
    // Tamper with the security version field (bytes 5 to 8)
    image_data[5] = 99;
    
    secure_ota_header_t header;
    secure_ota_err_t err = secure_ota_parse_image(image_data, image_len, &header);
    assert(err == SECURE_OTA_SUCCESS);
    
    err = secure_ota_verify_signature(image_data, image_len, &header, pub_key_pem);
    assert(err == SECURE_OTA_ERR_INVALID_SIGNATURE);
    
    free(image_data);
    printf("PASS test_secure_ota_tampered_version\n");
    return 0;
}

// Test 5: Outdated binary security version causes rollback error
static int test_secure_ota_rollback(EVP_PKEY *pkey, const char *pub_key_pem) {
    uint8_t payload[] = "Rollback payload.";
    uint32_t payload_len = sizeof(payload);
    uint8_t *image_data = NULL;
    size_t image_len = 0;
    
    // Security version is 4
    build_signed_ota_image(pkey, 4, payload, payload_len, &image_data, &image_len);
    
    secure_ota_header_t header;
    secure_ota_err_t err = secure_ota_parse_image(image_data, image_len, &header);
    assert(err == SECURE_OTA_SUCCESS);
    
    err = secure_ota_verify_signature(image_data, image_len, &header, pub_key_pem);
    assert(err == SECURE_OTA_SUCCESS);
    
    // Current security version is 5. Update has 4. This is a rollback!
    err = secure_ota_check_rollback(&header, 5);
    assert(err == SECURE_OTA_ERR_ROLLBACK_DETECTED);
    
    free(image_data);
    printf("PASS test_secure_ota_rollback\n");
    return 0;
}

// Test 6: Verifying with the wrong public key fails
static int test_secure_ota_wrong_key(EVP_PKEY *pkey) {
    uint8_t payload[] = "Signature test.";
    uint32_t payload_len = sizeof(payload);
    uint8_t *image_data = NULL;
    size_t image_len = 0;
    
    build_signed_ota_image(pkey, 5, payload, payload_len, &image_data, &image_len);
    
    // Generate a different key pair
    char *wrong_pub_key = NULL;
    EVP_PKEY *wrong_pkey = NULL;
    int key_res = generate_key_pair(&wrong_pub_key, &wrong_pkey);
    assert(key_res == 0);
    
    secure_ota_header_t header;
    secure_ota_err_t err = secure_ota_parse_image(image_data, image_len, &header);
    assert(err == SECURE_OTA_SUCCESS);
    
    // Try to verify using the wrong key
    err = secure_ota_verify_signature(image_data, image_len, &header, wrong_pub_key);
    assert(err == SECURE_OTA_ERR_INVALID_SIGNATURE);
    
    free(wrong_pub_key);
    EVP_PKEY_free(wrong_pkey);
    free(image_data);
    printf("PASS test_secure_ota_wrong_key\n");
    return 0;
}

// Test 7: Truncated or empty inputs result in out of bounds error
static int test_secure_ota_bounds(void) {
    uint8_t small_buf[10] = {0};
    secure_ota_header_t header;
    
    secure_ota_err_t err = secure_ota_parse_image(small_buf, 10, &header);
    assert(err == SECURE_OTA_ERR_OUT_OF_BOUNDS);
    
    err = secure_ota_parse_image(small_buf, 0, &header);
    assert(err == SECURE_OTA_ERR_OUT_OF_BOUNDS);
    
    printf("PASS test_secure_ota_bounds\n");
    return 0;
}

// Test 8: Null parameters checks
static int test_secure_ota_null_params(void) {
    secure_ota_header_t header;
    
    secure_ota_err_t err = secure_ota_parse_image(NULL, 100, &header);
    assert(err == SECURE_OTA_ERR_NULL_PARAM);
    
    err = secure_ota_parse_image((const uint8_t *)"data", 100, NULL);
    assert(err == SECURE_OTA_ERR_NULL_PARAM);
    
    err = secure_ota_verify_signature(NULL, 100, &header, "key");
    assert(err == SECURE_OTA_ERR_NULL_PARAM);
    
    err = secure_ota_check_rollback(NULL, 5);
    assert(err == SECURE_OTA_ERR_NULL_PARAM);
    
    printf("PASS test_secure_ota_null_params\n");
    return 0;
}

int main(void) {
    printf("=== Secure OTA Unit Tests ===\n");
    int failures = 0;
    
    char *pub_key_pem = NULL;
    EVP_PKEY *pkey = NULL;
    
    int key_res = generate_key_pair(&pub_key_pem, &pkey);
    if (key_res != 0) {
        printf("CRITICAL FAIL: Could not generate ECDSA test keys\n");
        return 1;
    }
    
    failures += test_secure_ota_valid(pkey, pub_key_pem);
    failures += test_secure_ota_invalid_magic(pkey, pub_key_pem);
    failures += test_secure_ota_tampered_payload(pkey, pub_key_pem);
    failures += test_secure_ota_tampered_version(pkey, pub_key_pem);
    failures += test_secure_ota_rollback(pkey, pub_key_pem);
    failures += test_secure_ota_wrong_key(pkey);
    failures += test_secure_ota_bounds();
    failures += test_secure_ota_null_params();
    
    free(pub_key_pem);
    EVP_PKEY_free(pkey);
    
    printf("\n=== Results: %d failures ===\n", failures);
    return failures;
}
