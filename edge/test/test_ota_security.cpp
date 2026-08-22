/**
 * @file test_ota_security.cpp
 * @brief Unit tests for ESP32-S3 OTA Anti-Rollback and Header Validation.
 */

#include "ota_security.h"
#include <cassert>
#include <cstdio>
#include <cstring>

static void test_anti_rollback_valid()
{
    // Same version
    assert(ota_validate_rollback_version(1, 1) == 0);
    // Upgraded version
    assert(ota_validate_rollback_version(1, 2) == 0);
    assert(ota_validate_rollback_version(5, 10) == 0);
    printf("PASS: test_anti_rollback_valid\n");
}

static void test_anti_rollback_violation()
{
    // Attempting to flash older version
    assert(ota_validate_rollback_version(2, 1) == -1);
    assert(ota_validate_rollback_version(10, 5) == -1);
    printf("PASS: test_anti_rollback_violation\n");
}

static void test_header_magic_validation()
{
    ota_header_t valid_header;
    memset(&valid_header, 0, sizeof(valid_header));
    valid_header.magic = OTA_MAGIC_HEADER;
    valid_header.security_version = 3;

    assert(ota_validate_header_magic(&valid_header) == true);

    ota_header_t invalid_header;
    memset(&invalid_header, 0, sizeof(invalid_header));
    invalid_header.magic = 0xDEADBEEF;

    assert(ota_validate_header_magic(&invalid_header) == false);
    assert(ota_validate_header_magic(nullptr) == false);
    printf("PASS: test_header_magic_validation\n");
}

static void test_full_header_validation()
{
    ota_header_t hdr;
    memset(&hdr, 0, sizeof(hdr));
    hdr.magic = OTA_MAGIC_HEADER;
    hdr.security_version = 1;
    hdr.payload_size = 500;

    // Valid header and sufficient buffer
    size_t valid_image_len = sizeof(ota_header_t) + 500;
    assert(ota_validate_header(&hdr, valid_image_len) == OTA_HDR_OK);

    // NULL header
    assert(ota_validate_header(nullptr, valid_image_len) == OTA_HDR_ERR_NULL);

    // Buffer smaller than header struct
    assert(ota_validate_header(&hdr, sizeof(ota_header_t) - 1) == OTA_HDR_ERR_OUT_OF_BOUNDS);

    // Bad magic
    hdr.magic = 0x12345678;
    assert(ota_validate_header(&hdr, valid_image_len) == OTA_HDR_ERR_BAD_MAGIC);
    hdr.magic = OTA_MAGIC_HEADER;

    // Zero payload size
    hdr.payload_size = 0;
    assert(ota_validate_header(&hdr, valid_image_len) == OTA_HDR_ERR_BAD_SIZE);

    // Payload size exceeds available buffer
    hdr.payload_size = 600;
    assert(ota_validate_header(&hdr, valid_image_len) == OTA_HDR_ERR_BAD_SIZE);

    printf("PASS: test_full_header_validation\n");
}

int main()
{
    printf("=== OTA Security & Anti-Rollback Unit Tests ===\n");
    test_anti_rollback_valid();
    test_anti_rollback_violation();
    test_header_magic_validation();
    test_full_header_validation();
    printf("=== Results: 0 failures ===\n");
    return 0;
}
