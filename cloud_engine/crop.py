import numpy as np
import time

class WelfordVarianceTracker:
    def __init__(self, min_variance=1e-6, default_variance=1.0):
        """
        Numerically stable online variance tracker using Welford's algorithm.
        """
        self.min_variance = min_variance
        self.default_variance = default_variance
        self.n = 0
        self.mean = 0.0
        self.S = 0.0

    def update(self, val):
        self.n += 1
        d = val - self.mean
        self.mean += d / self.n
        self.S += d * (val - self.mean)

    @property
    def variance(self):
        if self.n < 2:
            return self.default_variance
        var = self.S / (self.n - 1)  # Sample variance
        return max(var, self.min_variance)


class EMAVarianceTracker:
    def __init__(self, decay=0.99, min_variance=1e-6, default_variance=1.0):
        """
        Online variance tracker using Exponential Moving Average (EMA).
        Adapts dynamically to recent noise levels in the source.
        """
        self.decay = decay
        self.min_variance = min_variance
        self.default_variance = default_variance
        self.mean = None
        self.var = None

    def update(self, val):
        if self.mean is None:
            self.mean = val
            self.var = self.default_variance
        else:
            d = val - self.mean
            self.mean += (1 - self.decay) * d
            # EMA variance update
            self.var = self.decay * (self.var + (1 - self.decay) * d**2)

    @property
    def variance(self):
        if self.var is None:
            return self.default_variance
        return max(self.var, self.min_variance)


class CROP:
    def __init__(self, sources, tracker_type="welford", decay=0.99, min_variance=1e-6, epsilon=1e-7, normalize_weights=True):
        """
        Precision-Weighted Risk Opinion Pool (CROP).
        Aggregates multiple risk scores P_k into a single pooled risk probability.
        
        Args:
            sources (list of str): List of source names/identifiers.
            tracker_type (str): "welford" or "ema" for variance tracking.
            decay (float): Decay factor for EMA variance tracker (if used).
            min_variance (float): Minimum variance clamp to avoid division by zero.
            epsilon (float): Small constant to clamp probabilities before log.
            normalize_weights (bool): Whether to normalize weights to sum to 1.
        """
        self.sources = list(sources)
        self.epsilon = epsilon
        self.min_variance = min_variance
        self.normalize_weights = normalize_weights
        
        self.trackers = {}
        for src in sources:
            if tracker_type == "welford":
                self.trackers[src] = WelfordVarianceTracker(min_variance=min_variance)
            elif tracker_type == "ema":
                self.trackers[src] = EMAVarianceTracker(decay=decay, min_variance=min_variance)
            else:
                raise ValueError("Invalid tracker_type. Choose 'welford' or 'ema'.")

    def update_variance(self, source, score, label=None):
        """
        Updates the running variance for a given source.
        If a label (ground truth) is provided, computes variance of prediction error (MSE).
        Otherwise, computes variance of the score itself.
        """
        if source not in self.trackers:
            return
        
        if label is not None:
            val_to_track = (score - label) ** 2
        else:
            val_to_track = score
            
        self.trackers[source].update(val_to_track)

    def pool_risks(self, scores):
        """
        Aggregates risk scores using precision-weighted log pooling.
        
        Args:
            scores (dict): Dictionary mapping source names to current risk scores P_k.
            
        Returns:
            float: Pooled risk probability R.
        """
        t_start = time.perf_counter()
        
        log_p_anomaly = []
        log_p_normal = []
        weights = []
        
        # Gather available scores and calculate precision weights
        active_sources = []
        for src in self.sources:
            if src in scores:
                active_sources.append(src)
                var_k = self.trackers[src].variance
                weight_k = 1.0 / var_k
                weights.append(weight_k)
                
        if not weights:
            # Fallback if no scores are provided
            return 0.5
            
        # Normalize weights if required
        if self.normalize_weights:
            sum_weights = sum(weights)
            weights = [w / sum_weights for w in weights]
            
        # Compute precision-weighted log pools
        for idx, src in enumerate(active_sources):
            p_k = scores[src]
            # Clamp to prevent log(0) or log(1) errors
            p_k = np.clip(p_k, self.epsilon, 1.0 - self.epsilon)
            
            weight_k = weights[idx]
            log_p_anomaly.append(weight_k * np.log(p_k))
            log_p_normal.append(weight_k * np.log(1.0 - p_k))
            
        # Log-space pooling: log R = sum_k (w_k log P_k) - log Z
        # Normalization: Z = exp(sum_k w_k log P_k) + exp(sum_k w_k log(1 - P_k))
        # Log-sum-exp stabilization:
        s_anomaly = sum(log_p_anomaly)
        s_normal = sum(log_p_normal)
        
        # log_Z = log(exp(s_anomaly) + exp(s_normal))
        max_s = max(s_anomaly, s_normal)
        log_Z = max_s + np.log(np.exp(s_anomaly - max_s) + np.exp(s_normal - max_s))
        
        log_R = s_anomaly - log_Z
        R = np.exp(log_R)
        
        # Performance check (Acceptance Criteria is <= 2 ms)
        t_elapsed = (time.perf_counter() - t_start) * 1000  # ms
        
        return float(R)
