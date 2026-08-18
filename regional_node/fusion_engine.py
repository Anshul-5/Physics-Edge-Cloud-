import math

class FusionEngine:
    def __init__(self, temperature=1.5):
        """
        Initializes the fusion engine with a static temperature parameter.
        The Temperature parameter T scales the logits to calibrate the probabilities.
        """
        self.temperature = temperature

    def apply_temperature_calibration(self, confidence):
        """
        Applies Temperature Scaling to raw YOLOv8 confidence probabilities.
        Converts probability to logit, scales by T, and converts back to probability.
        """
        # Clamp confidence to prevent log(0) or log(1)
        confidence = max(1e-7, min(confidence, 1 - 1e-7))
        
        # Convert to logit
        logit = math.log(confidence / (1.0 - confidence))
        
        # Apply temperature scaling
        scaled_logit = logit / self.temperature
        
        # Convert back to probability (expit)
        calibrated_prob = 1.0 / (1.0 + math.exp(-scaled_logit))
        return float(calibrated_prob)

    def fuse_log_odds(self, edge_prob, l2_prob):
        """
        Fuses Edge Kinematic suspicion probability and L2 YOLOv8 probability 
        using naive Bayesian Recursive Log-Odds updating.
        L_fused = L_edge + L_l2
        """
        # Clamp inputs
        edge_prob = max(1e-7, min(edge_prob, 1 - 1e-7))
        l2_prob = max(1e-7, min(l2_prob, 1 - 1e-7))
        
        # Calculate log-odds
        l_edge = math.log(edge_prob / (1.0 - edge_prob))
        l_l2 = math.log(l2_prob / (1.0 - l2_prob))
        
        # Fuse log-odds
        l_fused = l_edge + l_l2
        
        # Convert back to probability
        fused_prob = 1.0 / (1.0 + math.exp(-l_fused))
        return float(fused_prob)
