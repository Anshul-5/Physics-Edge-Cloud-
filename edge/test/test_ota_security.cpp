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

int main()
{
    printf("=== OTA Security & Anti-Rollback Unit Tests ===\n");
    test_anti_rollback_valid();
    test_anti_rollback_violation();
    test_header_magic_validation();
    printf("=== Results: 0 failures ===\n");
    return 0;
}
