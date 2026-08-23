from collections import deque
import numpy as np
import time
import math
import logging

class AdaptiveConformalPredictor:
    def __init__(self, alpha=0.05, gamma=0.005, max_buffer_size=1000, default_quantile=0.5):
        """
        Time-Adaptive Conformal Prediction for distribution-free risk intervals.
        
        Args:
            alpha (float): Nominal significance level (target error rate is alpha, coverage 1 - alpha).
            gamma (float): Learning rate / step size for adaptive updates of alpha_t.
            max_buffer_size (int): Size of the rolling calibration buffer.
            default_quantile (float): Initial quantile value if the buffer is empty.
        """
        self.alpha_0 = float(alpha)
        self.gamma = float(gamma)
        self.max_buffer_size = int(max_buffer_size)
        self.default_quantile = float(default_quantile)
        self.logger = logging.getLogger("physedge.conformal")
        
        self.residuals = deque(maxlen=max_buffer_size)
        self.alpha_t = float(alpha)  # Adapted significance level
        
    def get_quantile(self):
        """
        Computes the current quantile threshold q_{1-alpha_t} from the rolling residuals.
        Uses an O(N) selection algorithm (np.partition) instead of an O(N log N) full sort.
        """
        if not self.residuals:
            return self.default_quantile
        
        arr = np.fromiter(self.residuals, dtype=float)
        n = arr.size
        idx = int(np.ceil((1.0 - self.alpha_t) * n)) - 1
        idx = max(0, min(n - 1, idx))
        return float(np.partition(arr, idx)[idx])

    def check_boundary(self, pooled_risk, quantile_threshold=None):
        """
        Checks if pooled risk triggers an alert (pooled_risk >= quantile_threshold).
        Fails closed (returns True) on non-finite or invalid risk scores to protect safety.
        
        Args:
            pooled_risk (float): Aggregated risk score from CROP.
            quantile_threshold (float, optional): Custom threshold, defaults to current q_{1-alpha_t}.
            
        Returns:
            bool: True if pooled_risk >= quantile_threshold (or non-finite/NaN), False otherwise.
        """
        if pooled_risk is None or isinstance(pooled_risk, bool) or not isinstance(pooled_risk, (int, float)) or not math.isfinite(pooled_risk):
            self.logger.error(f"Conformal: non-finite or invalid pooled risk {pooled_risk!r} - failing closed (escalating alert).")
            return True

        if quantile_threshold is None:
            quantile_threshold = self.get_quantile()
            
        alert = float(pooled_risk) >= float(quantile_threshold)
        return bool(alert)

    def update(self, pooled_risk, true_label):
        """
        Updates the calibration set and adjusts the adaptive alpha_t.
        
        Args:
            pooled_risk (float): Predicted risk score.
            true_label (float): Ground truth label (0.0 or 1.0).
        """
        if pooled_risk is None or isinstance(pooled_risk, bool) or not isinstance(pooled_risk, (int, float)) or not math.isfinite(pooled_risk):
            self.logger.warning(f"Conformal: dropping non-finite pooled_risk from calibration update: {pooled_risk!r}")
            return
            
        if true_label is None or isinstance(true_label, bool) or not isinstance(true_label, (int, float)) or not math.isfinite(true_label):
            self.logger.warning(f"Conformal: dropping non-finite true_label from calibration update: {true_label!r}")
            return

        # Calculate residual: E_i = |Y_i - P_hat_i|
        residual = abs(float(true_label) - float(pooled_risk))
        
        # Check current coverage error before updating the residuals buffer
        q_current = self.get_quantile()
        coverage_error = 1.0 if residual > q_current else 0.0
        
        # Update significance level alpha_t dynamically:
        # alpha_{t+1} = alpha_t + gamma * (alpha_0 - error_t)
        self.alpha_t += self.gamma * (self.alpha_0 - coverage_error)
        
        # Clamp alpha_t to stay within a reasonable range (0, 1)
        self.alpha_t = max(1e-4, min(1.0 - 1e-4, self.alpha_t))
        
        # Add the new residual to the rolling buffer
        self.residuals.append(residual)
