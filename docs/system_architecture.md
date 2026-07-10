# System Architecture Document: PhysEdge-Cloud

This document establishes the official technical architecture for the **PhysEdge-Cloud** platform—a physics-informed, uncertainty-calibrated edge-to-cloud cascade for real-time video anomaly detection. The system divides compute, reasoning, and storage across three distinct topological tiers (Edge, Regional, Cloud) organized into a 9-layer pipeline.

---

## 1. System Topology Overview

```mermaid
graph TD
    subgraph Tier 1: Microcontroller Edge (Sub-Watt)
        L1[Layer 1: Physics Edge Gate - ESP32-S3]
    end
    subgraph Tier 2: Regional Edge Nodes (Local Network)
        L2[Layer 2: Regional Probabilistic Validation Node]
    end
    subgraph Tier 3: Central Cloud (Scalable GPU Clusters)
        L3[Layer 3: Hybrid Cloud Risk Engine]
        L4[Layer 4: Adaptive Compute Orchestrator]
        L5[Layer 5: Model Registry & Drift Tracking]
        L6[Layer 6: Governed Storage System]
        L7[Layer 7: Shadow Retraining Pipeline]
        L8[Layer 8: Canary Deployment Controller]
        L9[Layer 9: Secure OTA Edge Update]
    end

    L1 -- Trigger: Skeletal/Kinematic Stream & Pre-Trigger Buffer --> L2
    L2 -- Escalation Decision: Posterior Probability + Variance --> L3
    L3 <--> L4
    L7 -- Retrained Models / Constraints --> L5
    L5 -- Release Candidate --> L8
    L8 -- Validated Firmware/Weights --> L9
    L9 -- OTA Updates --> L1
    L3 -- Closed-Loop Negative Constraints --> L1
```

---

## 2. The 9-Layer Pipeline Specification

### Layer 1: Physics-Based Edge Detection Unit (ESP32-S3)
*   **Hardware Profile:** ESP32-S3 (Dual-core Xtensa LX7 @ 240 MHz, 8 MB PSRAM, 384 KB SRAM).
*   **Role:** Acts as the primary wake-gate filter, discarding 80–90% of normal/static video frames without utilizing neural networks.
*   **Core Logic:**
    1.  **Downscaling:** Resizes input video stream from raw sensor resolution to $160 \times 120$ in fixed-point.
    2.  **Optical Flow:** Computes block-based fixed-point optical flow $v(x,y)$ to construct velocity fields.
    3.  **Perspective Normalization:** Applies a stored $3 \times 3$ homography matrix $H$ mapping pixel-space positions to ground-plane metric positions; velocity, acceleration, and jerk are computed as temporal derivatives of the mapped positions in SI units ($m/s$, $m/s^2$, $m/s^3$).
    4.  **Kinematic Gating:** Evaluates rolling Z-scores of metric jerk against a statistical baseline (exponentially weighted moving average / variance) maintained per camera and per time-of-day bucket.
    5.  **Directional Entropy:** Tracks Shannon entropy of motion vectors to flag coordinated panic behavior.
    6.  **Temporal Conflict Buffer:** Maintains a 5–10 second circular ring buffer of skeletal joint positions and motion vectors to transmit preceding context upon trigger firing.

### Layer 2: Regional Probabilistic Validation Node
*   **Hardware Profile:** NVIDIA Jetson Orin Nano / Local x86 server.
*   **Role:** Validates L1 triggers by evaluating semantic elements (human bodies, poses, vehicles) in the local network segment.
*   **Core Logic:**
    1.  **Semantic Inference:** Runs YOLOv8n (INT8 quantized) and BlazePose to identify objects, crowd density, and joint coordinate matrices.
    2.  **Calibrated Recursive Fusion:** Applies temperature scaling to detector confidences, combining them with L1 kinematics via a time-recursive log-odds filter:
        $$\ell_t = \gamma \ell_{t-1} + \sum_s \beta_s \log LR_s(z_s)$$
        where $\beta_s$ represents the learned per-source reliability weight and $LR_s$ represents the likelihood ratio.
    3.  **Abstain/Defer Action:** If pose detector confidence falls below a noise threshold, the node abstains from rejecting the trigger and escalates to L3, prioritizing safety over cost.

### Layer 3: Hybrid Cloud Risk Engine
*   **Hardware Profile:** Cloud GPU Clusters (NVIDIA L4/T4 instances).
*   **Role:** Performs deep contextual, global, and multi-camera behavioral analysis.
*   **Core Logic:**
    1.  **Graph Interaction Model:** Represents people as nodes in a proximity-motion graph. Analyzes structural stability changes via the algebraic connectivity (Fiedler value $\lambda_2$) of the graph Laplacian:
        $$\Delta \lambda_2 = \lambda_2(\mathcal{L}_{t-1}) - \lambda_2(\mathcal{L}_t)$$
    2.  **Memory-Augmented Reconstruction:** Utilizes a Memory-AE trained solely on normal behavior. Computes anomaly scores using normalized reconstruction error combined with latent Mahalanobis distance.
    3.  **Calibrated Risk Opinion Pool (CROP):** Integrates individual risk scores in log space, weighted by precision (inverse variance):
        $$\log R \propto \sum_k \pi_k \log P_k \quad \text{where} \quad \pi_k = \frac{1}{\sigma_k^2}$$
    4.  **Conformal Prediction:** Wraps the pooled risk in a time-adaptive conformal prediction framework, outputting distribution-free risk intervals that guarantee false-alarm bounds $\alpha$ under exchangeability.

### Layer 4: Adaptive Compute Orchestrator
*   **Role:** Minimizes operating expenses (OPEX) by gating GPU compute usage based on risk levels.
*   **Core Logic:** Formulates routing as a cost-constrained optimization problem:
    $$\min_{\pi} \mathbb{E}[\text{cost}(\pi)] \quad \text{s.t.} \quad \mathbb{E}[\text{miss-risk}(\pi)] \le \delta$$
    This determines whether to bypass L3 modules, run partial pipelines, or execute the full suite. Provides a graceful degradation mode (edge-only fallback) if cloud connectivity is lost.

### Layer 5: Model Registry & Drift Tracking
*   **Role:** Governs model lifecycles and monitors operational drift.
*   **Core Logic:** Separates input drift (covariate shift via KL divergence on input features) from concept drift (posterior distribution shift $P(Y|X)$). concept drift triggers Layer 7 retraining, whereas input drift alerts operators to environmental changes. Every prediction is bound to a model-version hash.

### Layer 6: Governed Storage System
*   **Role:** Secure, compliant, and query-optimized data retention.
*   **Database Stack:** PostgreSQL with `pgvector` for embedding searches.
*   **Tiers:**
    *   *Tier A (Edge/Regional):* Raw temporary video rings (90-day retention).
    *   *Tier B (Cloud Secure):* Triggered event clips (1–3 years retention) protected by a cryptographic hash chain (Merkle log) binding clip data, model version, and triggering kinematics.
    *   *Tier C (Metadata):* Anonymized embeddings and structural coordinates (5+ years retention).

### Layer 7: Shadow Retraining Pipeline
*   **Role:** Continuous, offline model optimization.
*   **Core Logic:** Collects false-positive datasets, retrains models offline, and evaluates them using a Champion/Challenger framework. Promotion to staging requires a statistically significant improvement margin on a frozen validation set.

### Layer 8: Canary Deployment Controller
*   **Role:** Safe rollout of model updates.
*   **Core Logic:** Deploys updates to 5–10% of the camera fleet. Uses sequential probability ratio testing (SPRT) to monitor false-alarm rates per camera-hour, triggering automatic rollback if guardrails are violated.

### Layer 9: Secure OTA Edge Update
*   **Role:** Secure deployment of firmware and weights.
*   **Core Logic:** Implements signed weight packages, secure boot verification, and anti-rollback counters to mitigate Man-In-The-Middle (MITM) and model-poisoning vectors.

---

## 3. Explainability and Telemetry Tags

Every trigger packet emitted by Layer 1 contains a **Dominant-Cause Tag** explaining why the gate was tripped:
*   `CAUSE_JERK_SURPRISE`: Spike in third derivative of ground-plane displacement.
*   `CAUSE_PANIC_INDEX`: Rapid rise in directional motion entropy.
*   `CAUSE_COLLISION_TTC`: Low time-to-collision estimate from rapid convergence of local object bounding boxes.

This telemetry flows into Regional and Cloud dashboards, allowing operators to audit false alarms and analyze the exact physical triggers initiating escalations.
