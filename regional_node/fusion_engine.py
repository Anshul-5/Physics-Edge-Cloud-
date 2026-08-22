import math

class FusionEngine:
    def __init__(self, temperature=1.5):
        """
        Initializes the fusion engine with a static temperature parameter.
        The Temperature parameter T scales the logits to calibrate the probabilities.
        """
        if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
            raise TypeError(f"temperature must be numeric, got {type(temperature).__name__}")
        if not math.isfinite(temperature) or temperature <= 0.0:
            raise ValueError(f"temperature must be finite and > 0, got {temperature!r}")
        self.temperature = float(temperature)

    def apply_temperature_calibration(self, confidence):
        """
        Applies Temperature Scaling to raw YOLOv8 confidence probabilities.
        Converts probability to logit, scales by T, and converts back to probability.
        """
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise TypeError(f"confidence must be numeric, got {type(confidence).__name__}")
        if not math.isfinite(confidence):
            raise ValueError(f"confidence must be finite, got {confidence!r}")

        # Clamp confidence to prevent log(0) or log(1)
        confidence = min(max(float(confidence), 1e-7), 1.0 - 1e-7)
        
        # Convert to logit
        logit = math.log(confidence / (1.0 - confidence))
        
        # Apply temperature scaling
        scaled_logit = logit / self.temperature
        
        # Convert back to probability via numerically stable sigmoid
        calibrated_prob = 0.5 * (1.0 + math.tanh(scaled_logit / 2.0))
        return float(calibrated_prob)

    def fuse_log_odds(self, edge_prob, l2_prob):
        """
        Fuses Edge Kinematic suspicion probability and L2 YOLOv8 probability 
        using naive Bayesian Recursive Log-Odds updating.
        L_fused = L_edge + L_l2
        """
        return self.fuse_log_odds_multi([edge_prob, l2_prob])

    def fuse_log_odds_multi(self, probabilities):
        """
        Fuses a list of independent probabilities using Bayesian Log-Odds updating.
        Filters out non-finite or invalid values to prevent alert suppression.
        L_fused = sum(L_i)
        """
        if not probabilities:
            return 0.5

        l_fused = 0.0
        used = 0
        for prob in probabilities:
            if prob is None or isinstance(prob, bool) or not isinstance(prob, (int, float)) or not math.isfinite(prob):
                continue
            prob_clamped = min(max(float(prob), 1e-7), 1.0 - 1e-7)
            l_fused += math.log(prob_clamped / (1.0 - prob_clamped))
            used += 1
            
        if used == 0:
            return 0.5

        fused_prob = 0.5 * (1.0 + math.tanh(l_fused / 2.0))
        return float(fused_prob)
