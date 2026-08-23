import time
import uuid
import json
import logging
import math
from collections import deque

_PARAM_SPEC = {
    "jerk_surprise_threshold_factor": (float, 0.75, 1.25),
    "entropy_threshold_base":         (float, 0.0,  1.0),
    "rolling_window_override_sec":    (int,   1,    300),
    "suppression_duration_sec":       (int,   1,    86400),
}

def _require_uuid(camera_uuid) -> str:
    """
    Validates and canonicalizes a camera UUID to prevent MQTT topic injection and namespace escape.
    """
    if isinstance(camera_uuid, uuid.UUID):
        return str(camera_uuid)
    try:
        parsed = uuid.UUID(str(camera_uuid))
        return str(parsed)
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"camera_uuid is not a valid UUID: {camera_uuid!r}")


class AdjudicationExporter:
    """
    Exports cloud-tagged false positive events as negative constraints
    for L1 Edge baseline tuning.
    """
    def __init__(self):
        self.logger = logging.getLogger("physedge.feedback")

    def export_false_positive(self, camera_uuid, reason="FALSE_POSITIVE_ENVIRONMENTAL_NOISE", parameters=None):
        """
        Formats a false positive adjudication into a negative constraint payload.
        """
        cam_id = _require_uuid(camera_uuid)
        timestamp_ms = int(time.time() * 1000)
        constraint_id = f"nc-{cam_id[:8]}-{timestamp_ms}"
        
        # Default parameter recommendations for baseline adjustment
        default_params = {
            "jerk_surprise_threshold_factor": 1.25,
            "entropy_threshold_base": 0.68,
            "rolling_window_override_sec": 12,
            "suppression_duration_sec": 3600
        }
        
        if parameters:
            for k, v in parameters.items():
                if k not in _PARAM_SPEC:
                    raise ValueError(f"Unknown constraint parameter: {k!r}")
                typ, lo, hi = _PARAM_SPEC[k]
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise TypeError(f"{k} must be numeric, got {type(v).__name__}")
                if not math.isfinite(v) or not (lo <= v <= hi):
                    raise ValueError(f"{k} must be between {lo} and {hi} to prevent feedback poisoning, got {v!r}")
                default_params[k] = typ(v)
        else:
            # Validate default factor as sanity check
            factor = default_params["jerk_surprise_threshold_factor"]
            if not (0.75 <= factor <= 1.25):
                raise ValueError("jerk_surprise_threshold_factor must be between 0.75 and 1.25")
            
        payload = {
            "constraint_id": constraint_id,
            "timestamp": timestamp_ms,
            "action": "ADJUST_THRESHOLDS",
            "parameters": default_params,
            "reason": reason
        }
        
        return payload


class ConstraintRateLimiter:
    """
    Enforces rate-limiting and outlier rejection (OpenSSF Standard)
    to protect the feedback channel from constraint poisoning.
    Caps aggregate adjustment to +/- 25% within any 24-hour window.
    """
    def __init__(self):
        # Maps camera_uuid -> list of (timestamp, factor)
        self.history = {}

    def is_adjustment_allowed(self, camera_uuid, factor):
        """
        Checks if applying this adjustment factor is within rate limits.
        """
        cam_key = _require_uuid(camera_uuid)
        if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not math.isfinite(factor):
            return False
            
        factor = float(factor)
        now = time.time()
        
        # Clean history older than 24 hours (86400 seconds) and prune dead keys
        if cam_key in self.history:
            pruned = [
                (t, f) for t, f in self.history[cam_key] if now - t < 86400
            ]
            if pruned:
                self.history[cam_key] = pruned
            else:
                self.history.pop(cam_key, None)
            
        # Calculate product of all factors applied in the last 24 hours
        cumulative_factor = 1.0
        for _, f in self.history.get(cam_key, []):
            cumulative_factor *= f
            
        new_cumulative = cumulative_factor * factor
        
        # OpenSSF constraint: aggregate adjustment must be within [0.75, 1.25]
        if 0.75 <= new_cumulative <= 1.25:
            return True
        return False

    def record_adjustment(self, camera_uuid, factor):
        """
        Records an adjustment event for rate-limiting tracking.
        """
        cam_key = _require_uuid(camera_uuid)
        if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not math.isfinite(factor):
            raise ValueError(f"Invalid adjustment factor: {factor!r}")
        factor = float(factor)
        if cam_key not in self.history:
            self.history[cam_key] = []
        self.history[cam_key].append((time.time(), factor))


class MQTTConstraintBroadcaster:
    """
    Emulates the MQTT broadcast pipeline from Cloud (L3) to Edge (L1).
    """
    def __init__(self, client=None, max_history=1000):
        self.client = client
        self.published_messages = deque(maxlen=max_history)

    def publish_constraint(self, camera_uuid, payload):
        """
        Publishes the negative constraint payload to the device's constraints topic.
        """
        cam_id = _require_uuid(camera_uuid)
        topic = f"physedge/devices/{cam_id}/constraints"
        serialized = json.dumps(payload)
        
        # Record locally in bounded deque for validation/mocking purposes
        self.published_messages.append((topic, serialized))
        
        # If a real MQTT client is provided, publish the message
        if self.client:
            self.client.publish(topic, serialized, qos=1)
            
        return topic, serialized
