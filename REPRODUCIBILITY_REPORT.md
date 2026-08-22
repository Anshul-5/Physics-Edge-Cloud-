# Reproducibility & Verification Report: PhysEdge-Cloud L1

This document provides a cryptographic and test-validation transcript of the physical kinematic components running on local host-emulated hardware. It verifies mathematical correctness, performance benchmarks, and compilation compatibility.

---

## 💻 System Configuration & Environment
- **Operating System:** Windows (11)
- **Architecture:** AMD64
- **Compiler Version:** gcc (MinGW.org GCC-6.3.0-1) 6.3.0
- **Python Version:** 3.13.14
- **Verification Timestamp:** 2026-08-21 19:32:58 UTC

---

## 📊 Verification & Latency Matrix

| Component Layer | Compilation | Tests Passed | Tests Failed | Execution Latency | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Downscaler** | ✓ Success | 5 | 0 | 315.600 ms | 🟢 PASS |
| **Optical Flow** | ✓ Success | 7 | 0 | 1047.453 ms | 🟢 PASS |
| **Homography** | ✓ Success | 12 | 0 | 264.642 ms | 🟢 PASS |
| **Jerk Baseline** | ✓ Success | 1 | 0 | 230.689 ms | 🟢 PASS |

### Overall Verification Summary: **PASSED**
- **Total Test Cases Executed:** 25
- **Total Passed:** 25
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
PASS test_motion_energy
PASS test_time_to_collision

=== Results: 0 failures ===
```

### Jerk Baseline Unit Test Log
```text
Running jerk baseline tests...
Single spike handled correctly (surprise=237.42)
PASS: Jerk Baseline Tests
```


---

## 🔬 How to Reproduce Locally
To recreate this report and re-verify all mathematical derivations, execute the following command at the root of the workspace:
```bash
python3 reproduce.py
```

This verification suite compiles raw C source files with maximum compiler optimization (`-O3`) to simulate actual deployment execution times, verifying the kinematics mathematical pipelines.
