# PhysEdge-Cloud

An Uncertainty-Calibrated, Physics-Informed Edge-to-Cloud Cascade for Real-Time Video Anomaly Detection.

---

## About

**PhysEdge-Cloud** is an enterprise-grade, 9-layer video anomaly detection framework that optimizes the trade-offs between real-time detection latency, cloud bandwidth costs, and strict privacy regulations. By leveraging lightweight physics-based algorithms (such as metric kinematics and directional motion entropy) directly on sub-watt microcontroller edge devices (ESP32-S3) as a gatekeeper, the system filters out 80–90% of normal scene activity. Suspicious events are escalated to a regional validation tier (NVIDIA Jetson) for posture and pose estimation before final contextual adjudication in the cloud using a Graph Spectral Instability model and conformal prediction.

```
+------------------------------------------+
|  Tier 1: ESP32-S3 Microcontroller Edge   | ---> Discards 80-90% of normal frames
|  (Metric Kinematics & Panic Gating)      |      Zero-PII Egress boundary
+------------------------------------------+
                     | (Skeletal Stream & Kinematics)
                     v
+------------------------------------------+
|  Tier 2: Regional Edge (Jetson Nano)     | ---> Validates semantic posture/poses
|  (Calibrated Recursive Log-Odds Fusion)  |      Abstains & defers on low confidence
+------------------------------------------+
                     | (Escalated Events)
                     v
+------------------------------------------+
|  Tier 3: Central Cloud (GPU Clusters)    | ---> Deep context, Graph Spectral Instability,
|  (Hybrid Cloud Risk Engine - CROP)       |      Memory-AE & Conformal Prediction
+------------------------------------------+
```

---

## Core System Highlights

*   **Metric Kinematics Gate (L1):** Homography-normalized calculation mapping pixel-level movement to ground-plane velocity ($v_m$), acceleration ($a_m$), and jerk ($j_m$) in SI units ($m/s^3$).
*   **Privacy-by-Architecture:** Enforces a Zero-PII Egress Contract. Video frames never leave the local edge boundary; only anonymized coordinate skeletons and kinematics vectors are sent to the cloud.
*   **Calibrated Risk Opinion Pool (CROP):** Precision-weighted log-opinion fusion of multi-source anomaly indicators.
*   **Closed-Loop Negative Feedback:** Cloud-adjudicated false triggers send real-time negative constraints back to edge devices to auto-tune detection baselines.
*   **Forensic Auditing:** Video clips are chained in a Merkle log signature binding them to model versions and kinematic provenance.

---

## Repository Structure

```
├── .git/
├── docs/                                  # Production Specifications
│   ├── system_architecture.md            # Detailed 9-layer cascade design
│   ├── api_specification.md              # gRPC, JSON schemas & update payloads
│   ├── security_and_privacy.md          # Threat models, linkage mitigation & DP
│   ├── production_runbook.md            # Canary rollouts, SPRT rollbacks & drift
│   └── development_roadmap.md            # Milestones, verification rigs & KPIs
├── README.md                              # Repository entry point
```

---

## Documentation Registry

To deep-dive into specific system components, refer to our comprehensive documentation suite:

*   **[System Architecture Specification](file:///d:/Physics-Cloud/docs/system_architecture.md):** Detailed breakdown of Layers 1–9, hardware profiles, graph spectral instability equations, and explanation tags.
*   **[API Interface Definitions](file:///d:/Physics-Cloud/docs/api_specification.md):** Complete schemas for Edge-to-Regional gRPC payloads, Cloud REST payloads, and MQTT Negative Constraint topics.
*   **[Security and Privacy Specifications](file:///d:/Physics-Cloud/docs/security_and_privacy.md):** Re-identification linkage attack analysis, differential privacy noise variables, and forensic hash Merkle-chain logic.
*   **[Production Operations Runbook](file:///d:/Physics-Cloud/docs/production_runbook.md):** Canary deployment phases, Sequential Probability Ratio Test (SPRT) rollback criteria, and drift monitoring instructions.
*   **[Roadmap & Verification Plan](file:///d:/Physics-Cloud/docs/development_roadmap.md):** 12-month development gantt schedule, testing rig configurations, and target KPIs (FPS, power, bandwidth).