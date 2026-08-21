import numpy as np
import pytest
import time
import os
import sys

# Ensure edge/tools is on pythonpath for ota_signer import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../edge/tools")))

from closed_loop import (
    NegativeConstraintRecord,
    NegativeConstraintPool,
    EdgeParameterStreamer,
    ClosedLoopAdjudicator
)
from dispatcher import (
    AlertSeverity,
    AlertPayload,
    AlertDispatcher,
    FleetMetricsCollector
)
from ota_signer import (
    pack_ota_image,
    unpack_and_verify_ota_image,
    OTA_MAGIC_HEADER
)


# =====================================================================
# Tests: Closed-Loop Telemetry & Negative Constraints (L7 Retraining)
# =====================================================================

def test_negative_constraint_pool_and_export():
    pool = NegativeConstraintPool(max_size=100)
    
    # Ingest 5 false positive records
    for i in range(5):
        rec = NegativeConstraintRecord(
            event_id=f"event-{i}",
            camera_id="camera-north",
            features=np.random.normal(0, 1, 10),
            jerk_peak=180.0 + i * 10,
            optical_flow_mag=1.5,
            adjudication_reason="wind_vibration"
        )
        pool.add_record(rec)
        
    assert pool.size() == 5
    
    x, y, metadata = pool.export_dataset()
    assert x.shape == (5, 10)
    assert len(y) == 5
    assert np.all(y == 0)  # Negative labels
    assert len(metadata) == 5


def test_edge_parameter_streamer_adaptation():
    streamer = EdgeParameterStreamer(
        default_jerk_threshold=150.0,
        learning_rate=0.2,
        max_jerk_threshold=300.0
    )
    
    # Record with jerk peak exceeding current threshold (e.g. 200 > 150)
    rec = NegativeConstraintRecord(
        event_id="fp-101",
        camera_id="cam-gate-1",
        features=np.zeros(5),
        jerk_peak=200.0,
        optical_flow_mag=1.2,
        adjudication_reason="tree_shadow"
    )
    
    # 1st adaptation: delta = 0.2 * (200 - 150) = 10.0 -> new threshold = 160.0
    payload = streamer.adapt_thresholds(rec)
    assert np.isclose(payload["jerk_threshold"], 160.0)
    assert payload["camera_id"] == "cam-gate-1"
    
    # 2nd adaptation with even higher peak (e.g. 260.0)
    # delta = 0.2 * (260 - 160) = 20.0 -> new threshold = 180.0
    rec2 = NegativeConstraintRecord(
        event_id="fp-102",
        camera_id="cam-gate-1",
        features=np.zeros(5),
        jerk_peak=260.0,
        optical_flow_mag=1.2,
        adjudication_reason="tree_shadow"
    )
    payload2 = streamer.adapt_thresholds(rec2)
    assert np.isclose(payload2["jerk_threshold"], 180.0)


def test_closed_loop_adjudicator_workflow():
    adjudicator = ClosedLoopAdjudicator()
    
    res = adjudicator.adjudicate_false_positive(
        event_id="evt-99",
        camera_id="cam-south",
        features=np.ones(8),
        jerk_peak=220.0,
        optical_flow_mag=2.0,
        adjudication_reason="cloud_shadow_flicker"
    )
    
    assert res["pool_size"] == 1
    assert res["downlink_payload"]["jerk_threshold"] > 150.0
    assert len(adjudicator.adjudication_history) == 1


# =====================================================================
# Tests: Alert Dispatcher & Prometheus Metrics (L8/L9 Operations)
# =====================================================================

def test_alert_payload_formatting():
    alert = AlertPayload(
        alert_id="alert-001",
        camera_id="cam-01",
        severity=AlertSeverity.CRITICAL,
        anomaly_score=0.92,
        kinematics={"jerk": 250.0, "speed": 18.2},
        description="High speed anomalous trajectory detected"
    )
    
    # 1. Slack payload
    slack = alert.format_slack_message()
    assert "CRITICAL" in slack["text"]
    assert slack["attachments"][0]["color"] == "#e01e5a"
    
    # 2. PagerDuty payload
    pd = alert.format_pagerduty_event()
    assert pd["payload"]["severity"] == "critical"
    assert pd["dedup_key"] == "alert-001"


def test_alert_dispatcher_latency_sla():
    dispatcher = AlertDispatcher()
    alert = AlertPayload(
        alert_id="alert-002",
        camera_id="cam-02",
        severity=AlertSeverity.WARNING,
        anomaly_score=0.65,
        kinematics={"jerk": 120.0},
        description="Minor jerk threshold breach"
    )
    
    res = dispatcher.dispatch(alert, channel="webhook")
    # Dispatching in-memory must complete well under 100 ms SLA
    assert res["sla_met"] is True
    assert res["latency_ms"] <= 100.0


def test_fleet_metrics_prometheus_exporter():
    metrics = FleetMetricsCollector()
    metrics.record_e2e_latency(12.5)
    metrics.record_e2e_latency(14.5)
    metrics.record_camera_fps("cam-01", 30.0)
    metrics.record_buffer_watermark("cam-01", 0.42)
    metrics.record_alert(is_false_alarm=False)
    metrics.record_alert(is_false_alarm=True)
    
    prom_text = metrics.get_prometheus_metrics()
    assert "physedge_e2e_latency_ms 13.500" in prom_text
    assert 'physedge_camera_fps{camera_id="cam-01"} 30.00' in prom_text
    assert 'physedge_buffer_watermark_ratio{camera_id="cam-01"} 0.4200' in prom_text
    assert "physedge_alerts_dispatched_total 2" in prom_text
    assert "physedge_false_alarm_rate 0.5000" in prom_text


# =====================================================================
# Tests: OTA Signing & Anti-Rollback Packaging (L9 OTA Layer)
# =====================================================================

def test_ota_image_packing_and_verification_success():
    payload = b"test_firmware_binary_content_12345"
    security_ver = 3
    current_hw_counter = 2
    
    # Pack image
    packed = pack_ota_image(payload, security_version=security_ver)
    
    # Unpack and verify against hw counter 2 (image version 3 >= 2)
    is_valid, header_info, unpacked_payload = unpack_and_verify_ota_image(
        packed,
        current_hardware_counter=current_hw_counter
    )
    
    assert is_valid is True
    assert header_info["security_version"] == 3
    assert header_info["payload_size"] == len(payload)
    assert unpacked_payload == payload


def test_ota_image_anti_rollback_violation():
    payload = b"old_vulnerability_firmware_payload"
    security_ver = 1
    current_hw_counter = 3  # Hardware has counter 3
    
    packed = pack_ota_image(payload, security_version=security_ver)
    
    # Attempting to flash older version (1 < 3)
    is_valid, header_info, _ = unpack_and_verify_ota_image(
        packed,
        current_hardware_counter=current_hw_counter
    )
    
    assert is_valid is False
    assert "Anti-rollback violation" in header_info["error"]


def test_ota_image_tamper_detection():
    payload = b"authentic_firmware_payload"
    packed = bytearray(pack_ota_image(payload, security_version=5))
    
    # Tamper with 1 byte in the payload area
    packed[-1] ^= 0xFF
    
    is_valid, header_info, _ = unpack_and_verify_ota_image(
        bytes(packed),
        current_hardware_counter=1
    )
    
    assert is_valid is False
    assert "digest mismatch" in header_info["error"]
