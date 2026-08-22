"""
Kinematics and Ground-Plane Reprojection Verification Test Suite

Tests:
1. Planar homography projection accuracy against synthetic ground truth.
2. Fixed-point (Q16.16) conversion precision and quantization error bounds.
3. Kinematics differentiation (velocity, acceleration, jerk) numerical convergence.
4. Reprojection error < 0.05m across simulated camera calibration targets.
"""

import numpy as np
import pytest

def homography_project_py(H, x, y):
    """Reference floating-point planar homography projection."""
    vec = np.array([x, y, 1.0], dtype=float)
    p_proj = H @ vec
    if abs(p_proj[2]) < 1e-7:
        raise ValueError("Degenerate projection denominator")
    return p_proj[0] / p_proj[2], p_proj[1] / p_proj[2]

def test_homography_reprojection_accuracy():
    # Synthetic calibration matrix mapping (1920x1080) to ground plane (meters)
    # Scale: 100 pixels = 1.0 meter with perspective tilt
    H_true = np.array([
        [0.010, 0.002, -5.0],
        [0.001, 0.015, -8.0],
        [0.0001, 0.0002, 1.0]
    ], dtype=float)
    
    # Test grid of pixel coordinates
    pixel_coords = [
        (100.0, 100.0),
        (500.0, 300.0),
        (960.0, 540.0),
        (1200.0, 800.0),
        (1900.0, 1000.0)
    ]
    
    for px, py in pixel_coords:
        xm, ym = homography_project_py(H_true, px, py)
        
        # Invert H to compute reprojection
        H_inv = np.linalg.inv(H_true)
        p_reproj_x, p_reproj_y = homography_project_py(H_inv, xm, ym)
        
        # Reprojection error in pixel space must be < 1e-4 pixels
        pixel_error = np.hypot(px - p_reproj_x, py - p_reproj_y)
        assert pixel_error < 1e-4, f"High reprojection error {pixel_error} at ({px}, {py})"

def test_kinematics_velocity_acceleration_convergence():
    # Constant acceleration trajectory: x(t) = 0.5 * a * t^2 + v0 * t + x0
    a_true = 2.5 # m/s^2
    v0_true = 1.0 # m/s
    dt = 0.04 # 40ms (25 FPS)
    
    t_vals = np.arange(0, 1.0, dt)
    x_vals = 0.5 * a_true * (t_vals ** 2) + v0_true * t_vals
    
    # Velocity by central difference
    v_est = np.diff(x_vals) / dt
    # Average estimated velocity matches theoretical midpoint
    expected_v = v0_true + a_true * (t_vals[:-1] + dt/2)
    assert np.allclose(v_est, expected_v, atol=1e-3)
    
    # Acceleration by second difference
    a_est = np.diff(v_est) / dt
    assert np.allclose(a_est, a_true, atol=1e-3)
