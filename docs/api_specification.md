# API Specification: PhysEdge-Cloud Communication Interfaces

This document defines the interface endpoints, protocol schemas, and payload specifications for data flowing across the three topological tiers in the PhysEdge-Cloud cascade.

---

## 1. Edge-to-Regional (L1 $\rightarrow$ L2) Interface

*   **Protocol:** gRPC / Protocol Buffers (fallback to WebSocket for lower-overhead stream initialization).
*   **Payload Type:** Binary-serialized message containing camera metadata, physical metrics, and structural skeletal joint points.
*   **Zero-PII Compliance:** Image frames are blocked at the edge. The uplink streams only raw scalar metrics and pose data.

### Protobuf Definition (`edge_uplink.proto`)

```protobuf
syntax = "proto3";

package physedge.l1;

enum TriggerCause {
  CAUSE_UNSPECIFIED = 0;
  CAUSE_JERK_SURPRISE = 1;
  CAUSE_PANIC_INDEX = 2;
  CAUSE_COLLISION_TTC = 3;
}

message Joint2D {
  float x = 1;     // Normalized coordinate [0.0, 1.0]
  float y = 2;     // Normalized coordinate [0.0, 1.0]
  float score = 3; // Model confidence score [0.0, 1.0]
}

message Skeleton {
  int32 person_id = 1;
  map<string, Joint2D> joints = 2; // Keyed by joint name (e.g. "nose", "left_shoulder")
}

message MetricFrame {
  int64 timestamp_ms = 1;
  float motion_energy = 2;      // Metric energy
  float directional_entropy = 3;// Motion entropy
  repeated Skeleton skeletons = 4;
}

message EdgeTriggerPayload {
  string camera_uuid = 1;
  string model_version_hash = 2;
  int64 trigger_timestamp_ms = 3;
  TriggerCause primary_cause = 4;
  
  // Historical context buffer (5-10 seconds of kinematics leading to trigger)
  repeated MetricFrame historical_buffer = 5;
  
  // Real-time stream of kinematic events post-trigger
  repeated MetricFrame active_frames = 6;
}
```

---

## 2. Regional-to-Cloud (L2 $\rightarrow$ L3) Interface

*   **Protocol:** HTTPS POST / REST API (or persistent gRPC channel).
*   **Endpoint:** `/api/v1/escalation/evaluate`
*   **Payload Type:** JSON.

### Payload Schema: Escalation Request

```json
{
  "escalation_id": "esc-89324-af89",
  "camera_uuid": "cam-device-esp32-0941",
  "model_version_hash": "ae274f88190debc49a374",
  "timestamp": 1783492812000,
  "escalation_cause": "CAUSE_JERK_SURPRISE",
  "regional_evaluation": {
    "posterior_anomaly_probability": 0.842,
    "confidence_variance": 0.012,
    "abstain_status": false,
    "detected_objects": [
      {
        "class": "person",
        "confidence": 0.91,
        "box": [110, 45, 140, 92]
      }
    ],
    "pose_fall_probability": 0.78
  },
  "kinematic_history": [
    {
      "time_delta_ms": -1000,
      "energy": 4.12,
      "entropy": 0.45,
      "active_skeletons_count": 1
    }
  ]
}
```

### Payload Schema: Escalation Response

```json
{
  "escalation_id": "esc-89324-af89",
  "adjudication": "EVALUATE_CLOUD_COMPLETE",
  "final_risk_score": 0.893,
  "confidence_interval": [0.85, 0.94],
  "action_required": "RAISE_ALERT",
  "event_type_prediction": "HUMAN_FALL"
}
```

---

## 3. Cloud-to-Edge (L3 $\rightarrow$ L1) Negative Constraint Loop

*   **Protocol:** MQTT (over secure TLS 1.3 connection).
*   **Topic Structure:** `physedge/devices/{camera_uuid}/constraints`
*   **Payload Type:** JSON.
*   **Purpose:** Closed-loop feedback adjusting detection sensitivity when false positives occur (e.g. insects on lens).

### Payload Schema: Negative Constraint Update

```json
{
  "constraint_id": "nc-98031-1b",
  "timestamp": 1783492900000,
  "action": "ADJUST_THRESHOLDS",
  "parameters": {
    "jerk_surprise_threshold_factor": 1.25,
    "entropy_threshold_base": 0.68,
    "rolling_window_override_sec": 12,
    "suppression_duration_sec": 3600
  },
  "reason": "FALSE_POSITIVE_ENVIRONMENTAL_NOISE"
}
```

---

## 4. Secure Over-The-Air Update (L9 $\rightarrow$ L1) Interface

*   **Protocol:** HTTPS GET / Secure Pull.
*   **Topic / Update Payload Schema:** Verification envelope for firmware or weight deployments.

### Payload Schema: OTA Update Manifest

```json
{
  "manifest_version": "1.4.0",
  "target_hardware": "ESP32-S3-WROOM-1",
  "firmware_checksum_sha256": "8f3b207df3a0937a0c8b3fb8127419e1",
  "model_weights_checksum_sha256": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
  "anti_rollback_counter": 12,
  "binary_url": "https://secure-ota.physedge.internal/firmware/v1.4.0.bin",
  "signature": "MEQCIF6cM9e8k02iM8d...[ECDSA Signature]"
}
```
