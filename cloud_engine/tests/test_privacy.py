import numpy as np
import pytest
from privacy import CoordinateObfuscator

def test_coordinate_coarsening():
    # Setup obfuscator with grid size 64
    obfuscator = CoordinateObfuscator(grid_size=64)
    
    # Generate coordinates spread across [0, 1]
    np.random.seed(42)
    coords = np.random.uniform(0.0, 1.0, (100, 2))
    
    # Coarsen
    coarsened = obfuscator.coarsen(coords, bounds=(0.0, 1.0))
    
    # Verify shape
    assert coarsened.shape == (100, 2)
    
    # Verify that coarsened coordinates map exactly to the 64 levels
    # i.e., val * 63 should be integers
    for val in coarsened.ravel():
        scaled_val = val * 63.0
        assert np.isclose(scaled_val, np.round(scaled_val)), f"Value {val} is not mapped to grid level"


def test_laplace_noise_distribution():
    epsilon = 0.5
    sensitivity = 1.0
    b = sensitivity / epsilon  # scale parameter b = 2.0
    
    obfuscator = CoordinateObfuscator(epsilon=epsilon, sensitivity=sensitivity)
    
    # Sample a large number of Laplace noise values
    np.random.seed(42)
    samples = [obfuscator.sample_laplace() for _ in range(5000)]
    
    # Theoretical mean of Laplace distribution is 0
    # Theoretical variance of Laplace distribution is 2 * (b^2) = 2 * (2^2) = 8.0
    empirical_mean = np.mean(samples)
    empirical_var = np.var(samples)
    
    # Assert empirical mean is close to 0 and variance is close to 8.0
    assert abs(empirical_mean) < 0.25, f"Empirical mean deviated too much: {empirical_mean}"
    # Tolerance of 10% for variance
    assert abs(empirical_var - 8.0) < 0.8, f"Empirical variance deviated too much: {empirical_var}"


def test_obfuscation_bounds_clamping():
    # Setup obfuscator with very small epsilon -> high noise
    min_val, max_val = 10.0, 50.0
    obfuscator = CoordinateObfuscator(epsilon=0.01, sensitivity=1.0)
    
    # Test coordinates
    coords = [[20.0, 30.0], [40.0, 45.0]]
    
    # Obfuscate multiple times to ensure high noise gets generated
    for _ in range(20):
        obfuscated = obfuscator.obfuscate(coords, bounds=(min_val, max_val))
        
        # Verify shape
        assert obfuscated.shape == (2, 2)
        
        # Verify that all outputs are strictly clamped within the bounds
        assert np.all(obfuscated >= min_val)
        assert np.all(obfuscated <= max_val)


def test_openssf_input_validation():
    # 1. Invalid Grid Size
    with pytest.raises(ValueError, match="Grid size must be greater than 1"):
        CoordinateObfuscator(grid_size=1)
        
    # 2. Invalid Epsilon
    with pytest.raises(ValueError, match="Epsilon.*positive"):
        CoordinateObfuscator(epsilon=0.0)
        
    with pytest.raises(ValueError, match="Epsilon.*positive"):
        CoordinateObfuscator(epsilon=-1.5)
        
    # 3. Invalid Sensitivity
    with pytest.raises(ValueError, match="Sensitivity must be strictly positive"):
        CoordinateObfuscator(sensitivity=-0.5)
        
    # 4. Invalid Bounds in coarsen
    obfuscator = CoordinateObfuscator()
    with pytest.raises(ValueError, match="Invalid bounds"):
        obfuscator.coarsen([[0.5, 0.5]], bounds=(5.0, 2.0))

def test_dimension_sequential_composition():
    obfuscator = CoordinateObfuscator(epsilon=1.0, sensitivity=1.0)
    coords = np.zeros((17, 2))
    # Vectorized obfuscation with dimension composition should generate scaled noise
    obfuscated_composed = obfuscator.obfuscate(coords, bounds=(-100.0, 100.0), compose_dimension=True)
    assert obfuscated_composed.shape == (17, 2)
    assert not np.allclose(obfuscated_composed, coords)

