import math
import secrets
import numpy as np

class CoordinateObfuscator:
    def __init__(self, grid_size=64, epsilon=1.0, sensitivity=1.0):
        """
        Manages coordinate grid coarsening and Laplace differential privacy.
        
        Args:
            grid_size (int): Quantization grid size (default 64 for 64x64 grid).
            epsilon (float): Privacy budget parameter. Smaller values mean more privacy/noise.
            sensitivity (float): Maximum coordinate deviation (L1 sensitivity of coordinate query).
        """
        if grid_size <= 1:
            raise ValueError("Grid size must be greater than 1.")
        if epsilon <= 0:
            raise ValueError("Epsilon (privacy budget) must be strictly positive.")
        if sensitivity <= 0:
            raise ValueError("Sensitivity must be strictly positive.")
            
        self.grid_size = grid_size
        self.epsilon = epsilon
        self.sensitivity = sensitivity
        
        # Laplace noise scale parameter: b = sensitivity / epsilon
        self.b = sensitivity / epsilon
        self.sys_random = secrets.SystemRandom()

    def sample_laplace(self, mu=0.0):
        """
        Samples a value from a Laplace distribution Lap(mu, b) using a CSPRNG.
        Ensures the noise is cryptographically unpredictable to fulfill OpenSSF standard.
        """
        u = 0.0
        # Sample uniform float in (0, 1) to avoid log(0)
        while u == 0.0 or u == 1.0:
            u = self.sys_random.random()
            
        u_shifted = u - 0.5
        sgn = 1.0 if u_shifted >= 0 else -1.0
        
        # Inverse transform sampling: X = mu - b * sgn(u) * ln(1 - 2*|u|)
        noise = mu - self.b * sgn * math.log(1.0 - 2.0 * abs(u_shifted))
        return noise

    def coarsen(self, coords, bounds=(0.0, 1.0)):
        """
        Quantizes coordinates to a discrete grid of size (grid_size x grid_size).
        
        Args:
            coords (list or np.ndarray): Input coordinates of shape (N, D) where D is coordinate dimension.
            bounds (tuple): Coordinate boundaries (min_val, max_val).
            
        Returns:
            np.ndarray: Quantized/coarsened coordinates.
        """
        coords_arr = np.array(coords, dtype=float)
        min_val, max_val = bounds
        
        if min_val >= max_val:
            raise ValueError("Invalid bounds: min_val must be strictly less than max_val.")
            
        # Scale to [0, 1] range
        scaled = (coords_arr - min_val) / (max_val - min_val)
        # Clamp to [0, 1] to handle any floating point boundaries
        scaled = np.clip(scaled, 0.0, 1.0)
        
        # Map to quantized grid levels: from 0 to grid_size - 1
        quantized = np.round(scaled * (self.grid_size - 1))
        
        # Re-scale back to the original range but restricted to grid levels
        coarsened = min_val + (quantized / (self.grid_size - 1)) * (max_val - min_val)
        return coarsened

    def obfuscate(self, coords, bounds=(0.0, 1.0)):
        """
        Applies coordinate coarsening followed by Laplace noise addition.
        Clamps outputs to the original boundaries to ensure validity.
        
        Args:
            coords (list or np.ndarray): Input coordinates of shape (N, D).
            bounds (tuple): Coordinate boundaries (min_val, max_val).
            
        Returns:
            np.ndarray: Obfuscated coordinates.
        """
        min_val, max_val = bounds
        
        # 1. Coordinate Grid Coarsening
        coarsened = self.coarsen(coords, bounds=bounds)
        
        # 2. Generate and Add Laplace Noise
        obfuscated = np.zeros_like(coarsened)
        
        # Iterate over all dimensions of each coordinate to add independent noise
        flat_coarsened = coarsened.ravel()
        flat_obfuscated = np.zeros_like(flat_coarsened)
        
        for idx in range(len(flat_coarsened)):
            noise = self.sample_laplace()
            flat_obfuscated[idx] = flat_coarsened[idx] + noise
            
        obfuscated = flat_obfuscated.reshape(coarsened.shape)
        
        # 3. Clamp to original bounds to ensure mathematical and system validity
        obfuscated = np.clip(obfuscated, min_val, max_val)
        
        return obfuscated
