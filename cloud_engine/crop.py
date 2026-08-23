import numpy as np
import time
import math
import logging

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
        if val is None or isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
            return
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
        if val is None or isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
            return
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
        self.logger = logging.getLogger("physedge.crop")
        
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
            
        if score is None or isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
            self.logger.warning(f"CROP: dropping non-finite score update from source {source}: {score!r}")
            return
            
        if label is not None:
            if isinstance(label, bool) or not isinstance(label, (int, float)) or not math.isfinite(label):
                self.logger.warning(f"CROP: dropping non-finite label update from source {source}: {label!r}")
                return
            val_to_track = (float(score) - float(label)) ** 2
        else:
            val_to_track = float(score)
            
        self.trackers[source].update(val_to_track)

    def pool_risks(self, scores):
        """
        Aggregates risk scores using precision-weighted log pooling.
        Filters out non-finite or invalid values to prevent alert suppression.
        
        Args:
            scores (dict): Dictionary mapping source names to current risk scores P_k.
            
        Returns:
            float: Pooled risk probability R.
        """
        if not isinstance(scores, dict):
            return 0.5
            
        log_p_anomaly = []
        log_p_normal = []
        weights = []
        
        # Gather available scores and calculate precision weights (filter non-finite)
        active_sources = []
        valid_scores = []
        for src in self.sources:
            if src in scores:
                p_k = scores[src]
                if p_k is None or isinstance(p_k, bool) or not isinstance(p_k, (int, float)) or not math.isfinite(p_k):
                    self.logger.warning(f"CROP: dropping non-finite risk score from source {src}: {p_k!r}")
                    continue
                active_sources.append(src)
                valid_scores.append(float(p_k))
                var_k = self.trackers[src].variance
                weight_k = 1.0 / var_k if var_k > 0 else 1.0
                weights.append(weight_k)
                
        if not weights:
            # Fallback if no valid scores are available
            return 0.5
            
        # Normalize weights if required
        if self.normalize_weights:
            sum_weights = sum(weights)
            weights = [w / sum_weights for w in weights]
            
        # Compute precision-weighted log pools
        for idx, src in enumerate(active_sources):
            p_k = valid_scores[idx]
            # Clamp to prevent log(0) or log(1) errors
            p_k = min(max(p_k, self.epsilon), 1.0 - self.epsilon)
            
            weight_k = weights[idx]
            log_p_anomaly.append(weight_k * math.log(p_k))
            log_p_normal.append(weight_k * math.log(1.0 - p_k))
            
        # Log-space pooling: log R = sum_k (w_k log P_k) - log Z
        # Normalization: Z = exp(sum_k w_k log P_k) + exp(sum_k w_k log(1 - P_k))
        # Log-sum-exp stabilization:
        s_anomaly = sum(log_p_anomaly)
        s_normal = sum(log_p_normal)
        
        max_s = max(s_anomaly, s_normal)
        log_Z = max_s + math.log(math.exp(s_anomaly - max_s) + math.exp(s_normal - max_s))
        
        log_R = s_anomaly - log_Z
        R = math.exp(log_R)
        
        return float(R)
