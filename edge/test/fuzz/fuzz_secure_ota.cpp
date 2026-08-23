#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "secure_ota.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size == 0) return 0;
    
    secure_ota_header_t header;
    memset(&header, 0, sizeof(header));
    
    secure_ota_err_t err = secure_ota_parse_image(data, size, &header);
    if (err == SECURE_OTA_SUCCESS) {
        secure_ota_check_rollback(&header, 1);
        secure_ota_verify_signature(data, size, &header, "dummy_pubkey");
    }
    
    return 0;
}
