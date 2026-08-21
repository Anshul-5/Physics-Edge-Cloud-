import uuid
import pytest
from feedback import AdjudicationExporter, ConstraintRateLimiter, MQTTConstraintBroadcaster

def test_adjudication_exporter_valid():
    exporter = AdjudicationExporter()
    camera_id = uuid.uuid4()
    
    payload = exporter.export_false_positive(camera_id)
    
    assert payload["action"] == "ADJUST_THRESHOLDS"
    assert "constraint_id" in payload
    assert payload["parameters"]["jerk_surprise_threshold_factor"] == 1.25
    assert payload["reason"] == "FALSE_POSITIVE_ENVIRONMENTAL_NOISE"


def test_adjudication_exporter_poisoning_validation():
    exporter = AdjudicationExporter()
    camera_id = uuid.uuid4()
    
    # Valid parameters (OpenSSF standard bounds check)
    exporter.export_false_positive(camera_id, parameters={"jerk_surprise_threshold_factor": 1.15})
    
    # Too large adjustment (exceeds 1.25)
    with pytest.raises(ValueError, match="must be between 0.75 and 1.25"):
        exporter.export_false_positive(camera_id, parameters={"jerk_surprise_threshold_factor": 1.50})
        
    # Too small adjustment (less than 0.75)
    with pytest.raises(ValueError, match="must be between 0.75 and 1.25"):
        exporter.export_false_positive(camera_id, parameters={"jerk_surprise_threshold_factor": 0.50})


def test_constraint_rate_limiter():
    limiter = ConstraintRateLimiter()
    camera_id = uuid.uuid4()
    
    # Apply valid adjustments
    assert limiter.is_adjustment_allowed(camera_id, 1.10)
    limiter.record_adjustment(camera_id, 1.10)
    
    # Cumulative is 1.10. Applying 1.10 again yields 1.21. Allowed.
    assert limiter.is_adjustment_allowed(camera_id, 1.10)
    limiter.record_adjustment(camera_id, 1.10)
    
    # Cumulative is 1.21. Applying 1.10 again yields 1.33. Exceeds 1.25 limit. Should be blocked!
    assert not limiter.is_adjustment_allowed(camera_id, 1.10)
    
    # Applying 0.80 yields 1.21 * 0.80 = 0.968. Allowed.
    assert limiter.is_adjustment_allowed(camera_id, 0.80)


def test_mqtt_broadcaster():
    broadcaster = MQTTConstraintBroadcaster()
    camera_id = uuid.uuid4()
    payload = {"constraint_id": "nc-test", "timestamp": 12345}
    
    topic, serialized = broadcaster.publish_constraint(camera_id, payload)
    
    assert topic == f"physedge/devices/{str(camera_id)}/constraints"
    assert "nc-test" in serialized
    assert len(broadcaster.published_messages) == 1


def test_adjudication_exporter_invalid_uuid():
    exporter = AdjudicationExporter()
    with pytest.raises(ValueError, match="Invalid camera_uuid format."):
        exporter.export_false_positive(12345)


def test_constraint_rate_limiter_camera_isolation():
    limiter = ConstraintRateLimiter()
    cam_a = uuid.uuid4()
    cam_b = uuid.uuid4()
    
    assert limiter.is_adjustment_allowed(cam_a, 1.10)
    limiter.record_adjustment(cam_a, 1.10)
    assert limiter.is_adjustment_allowed(cam_a, 1.10)
    limiter.record_adjustment(cam_a, 1.10)
    assert not limiter.is_adjustment_allowed(cam_a, 1.10)
    
    assert limiter.is_adjustment_allowed(cam_b, 1.10)
    limiter.record_adjustment(cam_b, 1.10)
    assert limiter.is_adjustment_allowed(cam_b, 1.10)


def test_constraint_rate_limiter_sliding_window(monkeypatch):
    import time
    limiter = ConstraintRateLimiter()
    camera_id = uuid.uuid4()
    
    current_time = time.time()
    assert limiter.is_adjustment_allowed(camera_id, 1.20)
    limiter.record_adjustment(camera_id, 1.20)
    
    # Simulate 25 hours passing (90,000 seconds)
    monkeypatch.setattr(time, "time", lambda: current_time + 90000)
    
    assert limiter.is_adjustment_allowed(camera_id, 1.20)
