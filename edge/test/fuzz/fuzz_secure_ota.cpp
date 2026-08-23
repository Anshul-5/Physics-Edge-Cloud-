#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "secure_ota.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size == 0) return 0;
    
    secure_ota_header_t header;
    memset(&header, 0, sizeof(header));
    
    secure_ota_err_t err = secure_ota_parse_image(data, size, &header);
    (void)err;
    
    if (size > sizeof(secure_ota_header_t)) {
        size_t seg_offset = sizeof(secure_ota_header_t);
        size_t seg_len = size - seg_offset;
        secure_ota_verify_segment(data, size, seg_offset, data + seg_offset, seg_len);
    }
    
    return 0;
}
