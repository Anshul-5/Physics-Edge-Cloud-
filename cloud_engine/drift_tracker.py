import numpy as np
import time
from collections import deque

class FeatureDriftTracker:
    def __init__(self, bin_edges, baseline_counts, window_seconds=86400, epsilon=1e-5):
        """
        Tracks data distribution drift of a feature using KL Divergence.
        
        Args:
            bin_edges (list or np.ndarray): Edges defining the histogram bins.
            baseline_counts (list or np.ndarray): Counts/frequencies for the baseline distribution.
            window_seconds (int): Rolling window duration in seconds (default 86400 for 24h).
            epsilon (float): Laplace smoothing parameter to avoid zero probabilities.
        """
        self.bin_edges = np.array(bin_edges)
        self.num_bins = len(self.bin_edges) - 1
        self.window_seconds = window_seconds
        self.epsilon = epsilon
        
        # Build reference distribution Q from baseline counts
        base_counts = np.array(baseline_counts, dtype=float)
        assert len(base_counts) == self.num_bins, "Baseline counts size must match number of bins."
        
        # Apply Laplace smoothing to reference distribution Q
        self.Q = (base_counts + epsilon) / (np.sum(base_counts) + self.num_bins * epsilon)
        
        # Active rolling window buffer: holds tuples of (timestamp, value)
        self.samples = deque()
        
    def add_sample(self, value, timestamp=None):
        """
        Adds a new feature sample to the rolling active window.
        """
        if timestamp is None:
            timestamp = time.time()
        self.samples.append((timestamp, value))
        self._prune_old_samples(timestamp)
        
    def _prune_old_samples(self, current_time):
        """
        Removes samples older than the rolling window duration.
        """
        cutoff = current_time - self.window_seconds
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()
            
    def compute_active_distribution(self):
        """
        Computes the normalized and smoothed probability distribution P from active samples.
        """
        if not self.samples:
            # If no samples, return uniform distribution as a fallback
            return np.ones(self.num_bins) / self.num_bins
            
        values = [val for _, val in self.samples]
        
        # Compute histogram counts
        counts, _ = np.histogram(values, bins=self.bin_edges)
        counts = counts.astype(float)
        
        # Apply Laplace smoothing to distribution P
        P = (counts + self.epsilon) / (np.sum(counts) + self.num_bins * self.epsilon)
        return P
        
    def compute_kl_divergence(self):
        """
        Computes the KL Divergence D_KL(P || Q) between the active distribution P
        and the baseline distribution Q.
        """
        P = self.compute_active_distribution()
        
        # D_KL(P || Q) = sum_i P_i * log(P_i / Q_i)
        kl_div = np.sum(P * np.log(P / self.Q))
        return float(kl_div)
        
    def check_drift_alert(self, threshold=0.5):
        """
        Returns True if KL divergence exceeds the threshold, signaling distribution drift.
        """
        kl_div = self.compute_kl_divergence()
        return kl_div > threshold, kl_div
        
    def get_prometheus_metrics(self, name_prefix="feature_drift"):
        """
        Exposes metrics formatted for Prometheus telemetry endpoints.
        """
        kl_div = self.compute_kl_divergence()
        alert_triggered, _ = self.check_drift_alert()
        
        lines = [
            f"# HELP {name_prefix}_kl_divergence Kullback-Leibler divergence measuring feature distribution drift.",
            f"# TYPE {name_prefix}_kl_divergence gauge",
            f"{name_prefix}_kl_divergence {kl_div:.6f}",
            f"# HELP {name_prefix}_alert_active Binary flag indicating if drift alert is active (D_KL > 0.5).",
            f"# TYPE {name_prefix}_alert_active gauge",
            f"{name_prefix}_alert_active {1.0 if alert_triggered else 0.0}"
        ]
        return "\n".join(lines)
