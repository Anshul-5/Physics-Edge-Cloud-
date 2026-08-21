# Reproducibility & Verification Report: PhysEdge-Cloud L1

This document provides a cryptographic and test-validation transcript of the physical kinematic components running on local host-emulated hardware. It verifies mathematical correctness, performance benchmarks, and compilation compatibility.

---

## 💻 System Configuration & Environment
- **Operating System:** Darwin (25.5.0)
- **Architecture:** arm64
- **Compiler Version:** Apple clang version 17.0.0 (clang-1700.6.4.2)
- **Python Version:** 3.9.6
- **Verification Timestamp:** 2026-08-21 12:10:43 UTC

---

## 📊 Verification & Latency Matrix

| Component Layer | Compilation | Tests Passed | Tests Failed | Execution Latency | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Downscaler** | ✓ Success | 5 | 0 | 549.424 ms | 🟢 PASS |
| **Optical Flow** | ✓ Success | 7 | 0 | 482.886 ms | 🟢 PASS |
| **Homography** | ✓ Success | 10 | 0 | 440.394 ms | 🟢 PASS |

### Overall Verification Summary: **PASSED**
- **Total Test Cases Executed:** 22
- **Total Passed:** 22
- **Total Failed:** 0

---

## 🧪 Detailed Execution Transcript

### Downscaler Unit Test Log
```text
=== Downscaler Unit Tests ===
PASS test_solid_color
PASS test_gradient_corners
PASS test_buffer_size
PASS test_null_input
PASS test_pixel_range

=== Results: 0 failures ===
```

### Optical Flow Unit Test Log
```text
=== Optical Flow Unit Tests ===
PASS test_stationary
PASS test_shifted_block
PASS test_grid_dims
PASS test_textureless_confidence
PASS test_textured_confidence
PASS test_null_inputs
PASS test_num_blocks

=== Results: 0 failures ===
```

### Homography Unit Test Log
```text
=== Homography & Kinematics Unit Tests ===
PASS test_fixed_point_conversions
PASS test_fixed_point_arith
PASS test_identity_projection
PASS test_scale_projection
PASS test_perspective_projection
PASS test_denominator_guard
PASS test_constant_velocity
PASS test_acceleration
PASS test_ewma_smoothing
PASS test_null_inputs

=== Results: 0 failures ===
```


---

## 🔬 How to Reproduce Locally
To recreate this report and re-verify all mathematical derivations, execute the following command at the root of the workspace:
```bash
python3 reproduce.py
```

This verification suite compiles raw C source files with maximum compiler optimization (`-O3`) to simulate actual deployment execution times, verifying the kinematics mathematical pipelines.
