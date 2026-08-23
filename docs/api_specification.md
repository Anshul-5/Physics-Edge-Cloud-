# Communication Protocol & Interface Specification: PhysEdge-Cloud

**Document Reference:** PEC-API-SPEC-V2.9  
**Classification:** Interface Control Document (ICD) & Protocol Specification  
**Standard Compliance:** gRPC v1.70 / Protocol Buffers v5.29 / OpenAPI 3.1.0  

---

## 1. Network Topology & Interface Overview

PhysEdge-Cloud defines four formal communication interfaces across the three topological tiers:

1. **Interface 1 (IF-1: L1 Edge -> L2 Regional):** High-throughput binary telemetry via gRPC / mTLS streaming anonymized skeletal joint matrices and SI-unit kinematics.
2. **Interface 2 (IF-2: L2 Regional -> L3 Cloud):** HTTPS REST / gRPC endpoint for multi-modal risk escalation payloads.
3. **Interface 3 (IF-3: L7 Cloud -> L1 Edge Downlink):** Rate-limited MQTT / TLS downlink channel for negative constraint streaming and threshold adaptation.
4. **Interface 4 (IF-4: L8/L9 Operations -> Dispatcher):** Asynchronous Webhook / PagerDuty / Prometheus exporter interface for security operations centers.

---

## 2. Interface 1: Edge-to-Regional Telemetry (`edge_uplink.proto`)

- **Protocol:** gRPC over HTTP/2 with Mutual TLS (mTLS).
- **Compression:** Snappy / zstandard for low-latency serialization.
- **Service Contract:**

```protobuf
syntax = "proto3";

package physedge.uplink.v1;

enum AnomalyTriggerCause {
  CAUSE_UNSPECIFIED = 0;
  CAUSE_JERK_SURPRISE = 1;
  CAUSE_PANIC_INDEX = 2;
  CAUSE_COLLISION_TTC = 3;
  CAUSE_POSTURE_DEFORMATION = 4;
}

message JointCoordinate2D {
  float x = 1;           // Ground-plane normalized coordinate [0.0, 1.0]
  float y = 2;           // Ground-plane normalized coordinate [0.0, 1.0]
  float confidence = 3;  // Keypoint detector confidence [0.0, 1.0]
}

message SkeletalEntity {
  int32 entity_id = 1;
  map<string, JointCoordinate2D> keypoints = 2;
  float velocity_mps = 3;
  float acceleration_mpss = 4;
  float jerk_mpsss = 5;
}

message KinematicTelemetryFrame {
  int64 timestamp_ns = 1;
  float motion_energy = 2;
  float directional_entropy = 3;
  repeated SkeletalEntity entities = 4;
}

message EdgeEscalationPayload {
  string camera_uuid = 1;
  string model_version_hash = 2;
  int64 trigger_timestamp_ns = 3;
  AnomalyTriggerCause primary_cause = 4;
  
  // Rolling historical context buffer (5 to 10 seconds prior to trigger)
  repeated KinematicTelemetryFrame historical_buffer = 5;
  
  // Real-time active kinematic telemetry post-trigger
  repeated KinematicTelemetryFrame active_frames = 6;
}

message EdgeEscalationAck {
  string camera_uuid = 1;
  int64 acknowledged_timestamp_ns = 2;
  bool backpressure_shed = 3;
}

service EdgeTelemetryService {
  rpc StreamEscalation(stream EdgeEscalationPayload) returns (stream EdgeEscalationAck);
}
```

---

## 3. Interface 2: Regional-to-Cloud Escalation REST API

- **Protocol:** HTTPS POST
- **Endpoint:** `/api/v1/escalations/evaluate`
- **Headers:** `Content-Type: application/json`, `X-Camera-UUID: <uuid>`, `X-Model-Hash: <sha256>`

### Request Payload Schema:

```json
{
  "escalation_id": "esc-904b-48af-91c2",
  "camera_uuid": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "model_version_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "timestamp_ns": 1783492812000000000,
  "primary_cause": "CAUSE_JERK_SURPRISE",
  "regional_evaluation": {
    "posterior_anomaly_probability": 0.8425,
    "confidence_variance": 0.0124,
    "abstain_status": false,
    "detected_objects": [
      {
        "class": "person",
        "confidence": 0.945,
        "bounding_box": [110, 45, 140, 92]
      }
    ],
    "pose_fall_probability": 0.782
  },
  "kinematic_history": [
    {
      "time_delta_ms": -1000,
      "motion_energy": 4.12,
      "directional_entropy": 0.45,
      "active_entities_count": 2
    }
  ]
}
```

### Response Payload Schema:

```json
{
  "escalation_id": "esc-904b-48af-91c2",
  "decision": "DISPATCH_ALERT",
  "fused_anomaly_score": 0.8912,
  "conformal_quantile_threshold": 0.8500,
  "conformal_alarm": true,
  "routing_action": "FULL",
  "spectral_divergence": 0.4120,
  "block_hash": "4a5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c",
  "processing_latency_ms": 0.3301
}
```

---

## 4. Interface 3: Closed-Loop Negative Constraint Downlink (MQTT)

- **Topic Format:** `physedge/control/v1/{camera_uuid}/constraints`
- **QoS Level:** QoS 1 (At least once delivery)
- **Downlink Payload Schema:**

```json
{
  "constraint_id": "nc-a0eebc99-1783492812",
  "timestamp_ms": 1783492812000,
  "action": "ADJUST_THRESHOLDS",
  "parameters": {
    "jerk_surprise_threshold_factor": 1.15,
    "entropy_threshold_base": 0.68,
    "rolling_window_override_sec": 12,
    "suppression_duration_sec": 3600
  },
  "reason": "FALSE_POSITIVE_CAMERA_JITTER"
}
```

---

## 5. Interface 4: Operations Alert Dispatcher & Metrics Exporter

- **Prometheus Metrics Endpoint:** `/metrics`
- **Exported Gauges & Counters:**
  - `physedge_end_to_end_latency_ms`: Gauge tracking 95th percentile cascade latency.
  - `physedge_edge_fps`: Gauge tracking frame ingestion rate per camera.
  - `physedge_edge_discard_ratio`: Gauge tracking percentage of frames filtered at Tier 1.
  - `physedge_conformal_coverage_rate`: Gauge tracking empirical prediction interval coverage.
  - `physedge_sprt_false_alarm_rate`: Gauge tracking online Wald SPRT error statistics.
  - `physedge_alerts_dispatched_total`: Counter tracking security alerts dispatched.
