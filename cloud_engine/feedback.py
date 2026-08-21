import time
import uuid
import json
import logging

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
        if not isinstance(camera_uuid, (str, uuid.UUID)):
            raise ValueError("Invalid camera_uuid format.")
            
        timestamp_ms = int(time.time() * 1000)
        constraint_id = f"nc-{str(camera_uuid)[:8]}-{timestamp_ms}"
        
        # Default parameter recommendations for baseline adjustment
        default_params = {
            "jerk_surprise_threshold_factor": 1.25,  # Decent threshold increase to reduce sensitivity
            "entropy_threshold_base": 0.68,
            "rolling_window_override_sec": 12,
            "suppression_duration_sec": 3600
        }
        
        if parameters:
            # Overwrite default parameters if custom parameters provided
            for k, v in parameters.items():
                default_params[k] = v
                
        # Validate parameters (OpenSSF Standard)
        factor = default_params["jerk_surprise_threshold_factor"]
        if not (0.75 <= factor <= 1.25):
            raise ValueError("jerk_surprise_threshold_factor must be between 0.75 and 1.25 to prevent feedback poisoning.")
            
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
        cam_key = str(camera_uuid)
        now = time.time()
        
        # Clean history older than 24 hours (86400 seconds)
        if cam_key in self.history:
            self.history[cam_key] = [
                (t, f) for t, f in self.history[cam_key] if now - t < 86400
            ]
        else:
            self.history[cam_key] = []
            
        # Calculate product of all factors applied in the last 24 hours
        cumulative_factor = 1.0
        for _, f in self.history[cam_key]:
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
        cam_key = str(camera_uuid)
        if cam_key not in self.history:
            self.history[cam_key] = []
        self.history[cam_key].append((time.time(), factor))


class MQTTConstraintBroadcaster:
    """
    Emulates the MQTT broadcast pipeline from Cloud (L3) to Edge (L1).
    """
    def __init__(self, client=None):
        self.client = client
        self.published_messages = []

    def publish_constraint(self, camera_uuid, payload):
        """
        Publishes the negative constraint payload to the device's constraints topic.
        """
        topic = f"physedge/devices/{str(camera_uuid)}/constraints"
        serialized = json.dumps(payload)
        
        # Record locally for validation/mocking purposes
        self.published_messages.append((topic, serialized))
        
        # If a real MQTT client is provided, publish the message
        if self.client:
            self.client.publish(topic, serialized, qos=1)
            
        return topic, serialized
