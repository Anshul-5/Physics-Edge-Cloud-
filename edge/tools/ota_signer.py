"""
ESP32-S3 OTA Firmware Signing & Anti-Rollback Packaging Utility (L9 OTA Layer)

Provides tools to:
1. Pack firmware binaries with the packed OTA header struct (magic, security_version, payload_size, sha256_digest, signature).
2. Validate monotonic version counters against hardware rollback thresholds.
3. Verify cryptographic SHA-256 payload digests.
"""

import struct
import hashlib
from typing import Tuple, Optional, Dict, Any

OTA_MAGIC_HEADER = 0x50485953  # "PHYS"
OTA_HEADER_FORMAT = "<III32s64s"  # magic, security_version, payload_size, sha256[32], sig[64]
OTA_HEADER_SIZE = struct.calcsize(OTA_HEADER_FORMAT)


def pack_ota_image(
    payload: bytes,
    security_version: int,
    signature: Optional[bytes] = None
) -> bytes:
    """
    Packs a firmware binary with the standard PhysEdge OTA security header.
    
    Args:
        payload: Raw binary payload (firmware image).
        security_version: Monotonic anti-rollback security counter.
        signature: 64-byte signature (if omitted, filled with zeros for unsigned staging).
        
    Returns:
        bytes: Packed binary with anti-rollback header.
    """
    if security_version < 0:
        raise ValueError("Security version counter must be non-negative.")
        
    payload_size = len(payload)
    sha256_digest = hashlib.sha256(payload).digest()
    
    sig_bytes = (signature or b"\x00" * 64)[:64].ljust(64, b"\x00")
    
    header = struct.pack(
        OTA_HEADER_FORMAT,
        OTA_MAGIC_HEADER,
        security_version,
        payload_size,
        sha256_digest,
        sig_bytes
    )
    return header + payload


def unpack_and_verify_ota_image(
    data: bytes,
    current_hardware_counter: int
) -> Tuple[bool, Dict[str, Any], bytes]:
    """
    Parses and verifies an OTA image against anti-rollback and integrity constraints.
    
    Args:
        data: Packed binary with header.
        current_hardware_counter: Current monotonic security counter burned in hardware.
        
    Returns:
        Tuple of (is_valid, header_info_dict, raw_payload)
    """
    if len(data) < OTA_HEADER_SIZE:
        return False, {"error": "Image smaller than OTA header size"}, b""
        
    magic, security_version, payload_size, sha256_digest, signature = struct.unpack(
        OTA_HEADER_FORMAT,
        data[:OTA_HEADER_SIZE]
    )
    
    header_info = {
        "magic": magic,
        "security_version": security_version,
        "payload_size": payload_size,
        "sha256_digest": sha256_digest.hex(),
        "signature": signature.hex()
    }
    
    # 1. Check Magic Header
    if magic != OTA_MAGIC_HEADER:
        header_info["error"] = f"Invalid magic header: {hex(magic)}"
        return False, header_info, b""
        
    # 2. Check Anti-Rollback Monotonic Counter
    if security_version < current_hardware_counter:
        header_info["error"] = f"Anti-rollback violation: image version {security_version} < hardware counter {current_hardware_counter}"
        return False, header_info, b""
        
    # 3. Check Payload Size
    payload = data[OTA_HEADER_SIZE:]
    if len(payload) != payload_size:
        header_info["error"] = f"Payload size mismatch: expected {payload_size}, got {len(payload)}"
        return False, header_info, b""
        
    # 4. Check SHA-256 Digest Integrity
    actual_digest = hashlib.sha256(payload).digest()
    if actual_digest != sha256_digest:
        header_info["error"] = "SHA-256 payload digest mismatch (corrupted binary)"
        return False, header_info, b""
        
    return True, header_info, payload
