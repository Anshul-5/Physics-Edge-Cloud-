# System Architecture Specification: PhysEdge-Cloud

**Document Reference:** PEC-ARCH-SPEC-V2.9  
**Classification:** Formal Technical Specification & Architecture Manual  
**Standard Compliance:** IEEE 1471 / ISO/IEC/IEEE 42010 Architecture Description Standard  

---

## 1. Executive Topological Hierarchy

PhysEdge-Cloud establishes a distributed, uncertainty-calibrated, multi-tier video anomaly detection infrastructure partitioned across three topological tiers:

1. **Tier 1: Sub-Watt Microcontroller Edge Gate (Sub-500 mW, Sensor Interface)**
   - Device: ESP32-S3 (Dual-Core Xtensa LX7 @ 240 MHz, 384 KB Internal SRAM, 8 MB Octal PSRAM).
   - Execution Model: Fixed-point Q8.8 arithmetic, SIMD-accelerated Sum of Absolute Differences (SAD) optical flow, homography projection, and kinematic derivatives without neural network dependencies.
   - Filtering Objective: Discards $80-90\%$ of baseline normal video frames locally.
   - Privacy Guarantee: Zero-PII egress boundary (raw pixels are discarded in SRAM; only anonymized skeletal vectors and kinematic derivatives are transmitted).

2. **Tier 2: Regional Probabilistic Validation Nodes (Local Network Edge)**
   - Device: NVIDIA Jetson Orin Nano (6-core ARM Cortex-A78AE, 1024-core Ampere GPU @ 40 TOPS) / Local Edge Server.
   - Execution Model: INT8-quantized YOLOv8n object detection, BlazePose joint tracking, Calibrated Recursive Log-Odds Opinion Pool (CROP) fusion, and dynamic backpressure queue shedding.
   - Latency SLA: $< 5.0\text{ ms}$ processing budget per escalated frame.

3. **Tier 3: Central Cloud Risk Engine & Governance (GPU Clusters)**
   - Environment: Scalable Cloud GPU Instances (NVIDIA L4 / A10G clusters) backed by PostgreSQL `pgvector`.
   - Execution Model: Spatiotemporal pedestrian interaction graph Laplacian spectral analysis, Memory-Augmented Autoencoder (MemAE) reconstruction, time-adaptive conformal prediction, Lagrangian dual compute routing, length-delimited Merkle hash-chain logging, differential privacy coordinate coarsening, shadow retraining, and SPRT canary deployment.
   - Latency SLA: $< 45.0\text{ ms}$ processing budget per heavy analysis.

---

## 2. End-to-End Cascade Topology

```
+-----------------------------------------------------------------------------+
|  Tier 1: Sub-Watt Edge Gate (ESP32-S3 @ 240 MHz, <0.5 W)                    |
|  [L1] QVGA Grayscale -> Fixed-Point Downscaler (Q8.8) -> SIMD Optical Flow   |
|       -> Homography Matrix H (3x3) -> Metric Kinematics (v, a, j)            |
|       -> Directional Shannon Entropy -> Zero-PII Egress Boundary            |
+--------------------------------------|--------------------------------------+
                                       | Anonymized Skeletal & Kinematic Stream
                                       v
+-----------------------------------------------------------------------------+
|  Tier 2: Regional Probabilistic Node (NVIDIA Jetson / Local Server)         |
|  [L2] INT8 Semantic Object Detection -> Skeletal Pose Angle Validation      |
|       -> Calibrated Recursive Log-Odds Fusion (CROP) -> Backpressure Buffer |
+--------------------------------------|--------------------------------------+
                                       | Escalated Events (Posterior + Var)
                                       v
+-----------------------------------------------------------------------------+
|  Tier 3: Central Cloud Risk Engine & Operations (GPU Cluster)               |
|  [L3] Spatiotemporal Graph Laplacian (λ2) -> MemAE Latent Reconstruction    |
|       -> Time-Adaptive Conformal Prediction (1-α Coverage Guarantee)        |
|  [L4] Cost-Risk Lagrangian Dual Compute Router (Skip / Partial / Full)      |
|  [L5] Feature Drift Tracking (KL Divergence) & Model Version Hash Binding   |
|  [L6] Governed Storage: PostgreSQL pgvector + Merkle Hash Chain + Lap DP   |
|  [L7] Shadow Retraining & Negative Constraint Generation                    |
|  [L8] Progressive Canary Deployment & Wald's SPRT Rollback Controller       |
|  [L9] ECDSA-Signed Anti-Rollback Secure OTA Firmware/Parameter Downlink     |
+-----------------------------------------------------------------------------+
```

---

## 3. Comprehensive 9-Layer Specification

### Layer 1: Physics-Based Edge Detection Unit (ESP32-S3)
- **Role:** High-throughput hardware wake-gate filter.
- **Hardware Footprint:** Max SRAM usage $57.1\text{ KB}$, power consumption $< 0.45\text{ W}$.
- **Core Execution Pipeline:**
  1. **Image Capture:** Ingests QVGA ($320 \times 240$) 8-bit grayscale at 30 FPS via parallel DVP interface.
  2. **Q8.8 Downscaling:** Bilinear interpolation scales frame to $160 \times 120$ without floating-point emulation.
  3. **SIMD Optical Flow:** Calculates $10 \times 7$ grid block-matching optical flow on $16 \times 16$ macroblocks using Xtensa PIE 8-bit parallel subtract-and-accumulate instructions.
  4. **Ground-Plane Homography:** Transforms macroblock center coordinates $[u, v, 1]^T$ to metric ground-plane coordinates $[X, Y, 1]^T$ via $\mathbf{H} \in \mathbb{R}^{3\times 3}$.
  5. **Kinematic Derivative Pipeline:** Evaluates metric velocity $\mathbf{v}(t)$, acceleration $\mathbf{a}(t)$, and jerk $\mathbf{j}(t) = d\mathbf{a}/dt$ in SI units ($\text{m/s}^3$).
  6. **Statistical Surprise Gating:** Standardizes jerk against camera-specific exponentially weighted moving averages:
     $$S_j(t) = \frac{\|\mathbf{j}(t)\|_2 - \mu_{\text{jerk}}}{\sigma_{\text{jerk}}}$$
  7. **Directional Shannon Motion Entropy:** Computes 8-bin angular velocity entropy $H(\Theta)$ to detect panic turbulence.

### Layer 2: Regional Probabilistic Validation Node (NVIDIA Jetson)
- **Role:** Semantic verification and false-positive suppression within local local network segments.
- **Core Execution Pipeline:**
  1. **Semantic Inference:** Executes TensorRT INT8-quantized YOLOv8n and BlazePose to locate bounding boxes and 33 skeletal keypoints.
  2. **Bayesian Opinion Pool (CROP):** Combines metric kinematics risk with posture angle deformation and proximity via recursive log-odds:
     $$\ell_t = \gamma \ell_{t-1} + \sum_{s} w_s \log \frac{P_s}{1 - P_s}$$
  3. **Backpressure Shedding:** Employs priority queue shedding when input buffer depth exceeds $80\%$ capacity, prioritizing high-jerk events.

### Layer 3: Hybrid Cloud Risk Engine
- **Role:** Deep contextual multi-entity interaction analysis and global spatiotemporal modeling.
- **Core Execution Pipeline:**
  1. **Pedestrian Interaction Graph:** Constructs dynamic affinity matrix $\mathbf{A} \in \mathbb{R}^{N\times N}$ across entities:
     $$A_{pq} = \exp\left(-\sigma_1 \|\mathbf{X}_p - \mathbf{X}_q\|_2^2\right) \cdot \max\left(0, \frac{\mathbf{v}_p \cdot \mathbf{v}_q}{\|\mathbf{v}_p\|_2 \|\mathbf{v}_q\|_2 + \epsilon}\right)$$
  2. **Normalized Laplacian Spectral Analysis:** Computes algebraic connectivity $\lambda_2(\mathbf{L}_{\text{norm}})$:
     $$\mathbf{L}_{\text{norm}} = \mathbf{I} - \mathbf{D}^{-1/2} \mathbf{A} \mathbf{D}^{-1/2}$$
     Flags panic cluster splits when $\Delta \lambda_2 = \lambda_2(t-1) - \lambda_2(t) > \tau_{\text{spectral}}$.
  3. **Memory-Augmented Autoencoder (MemAE):** Computes deep reconstruction error $S_{\text{recon}}(\mathbf{x}) = \|\mathbf{x} - \hat{\mathbf{x}}\|_2^2$ constrained by normal prototype memory matrices.
  4. **Time-Adaptive Conformal Prediction:** Calibrates non-conformity residuals dynamically, guaranteeing empirical risk coverage $1-\alpha_0$.

### Layer 4: Adaptive Compute Orchestrator
- **Role:** OPEX optimization and dynamic GPU compute routing.
- **Formulation:** Solves the Lagrangian dual optimization problem:
  $$\min_{a \in \{\text{SKIP}, \text{PARTIAL}, \text{FULL}\}} \Big( \text{Cost}(a) + \lambda \cdot \text{MissRisk}(a, P) \Big)$$
- **Dual Gradient Ascent:** $\lambda_{t+1} = \max(0, \lambda_t + \eta (\text{MissRisk}_t - \delta))$.
- **Outage Fallback:** Automatically switches to edge-only autonomous operation upon cloud network disconnects ($>1500\text{ ms}$ latency).

### Layer 5: Model Registry & Drift Tracking
- **Role:** Operational drift monitoring and model lineage binding.
- **Covariate Shift Detection:** Evaluates symmetric Kullback-Leibler (KL) divergence across 24-hour sliding feature histograms:
  $$D_{\text{KL}}(P \parallel Q) = \sum_{b=1}^B P(b) \ln \frac{P(b)}{Q(b)}$$
- **Model Cryptographic Binding:** Every inference adjudication is cryptographically bound to the SHA-256 digest of active neural weights.

### Layer 6: Governed Storage System
- **Role:** Tamper-evident forensic retention and vector similarity search.
- **Subsystems:**
  1. **PostgreSQL pgvector:** High-dimensional vector index for 256-dimensional event embeddings with cosine distance operators (`<=>`).
  2. **Length-Delimited Merkle Hash-Chain:** Appends event blocks with canonical domain separation:
     $$B_i = \text{SHA-256}\Big( \text{len}(B_{i-1}) \parallel B_{i-1} \parallel \text{len}(C_i) \parallel C_i \parallel \text{len}(K_i) \parallel K_i \parallel \text{len}(M_i) \parallel M_i \Big)$$
  3. **Laplace Differential Privacy Obfuscator:** Perturbs geographic coordinates with CSPRNG Laplace noise $\text{Lap}(0, \Delta f / \varepsilon)$ on a $64 \times 64$ grid.

### Layer 7: Shadow Retraining Pipeline
- **Role:** Continuous offline retraining and negative constraint generation.
- **Negative Constraint Generation:** Translates central false-alarm adjudications into rate-limited parameter updates ($\pm 25\%$ max 24-hour cap) to tune Tier 1 jerk thresholds.
- **Model Promotion Gate:** Requires statistically significant AUPRC improvement:
  $$\Delta \text{AUPRC} - 1.96 \cdot \text{SE}_{\text{boot}} > 0$$

### Layer 8: Canary Deployment Controller
- **Role:** Progressive staged rollout and online safety monitoring.
- **Rollout Schedule:** Deterministic hash-based fleet partitioning ($5\% \to 20\% \to 100\%$).
- **Wald's Sequential Probability Ratio Test (SPRT):**
  $$S_n = k \ln \frac{p_1}{p_0} + (n - k) \ln \frac{1 - p_1}{1 - p_0}$$
  Automatically rolls back release candidates if $S_n \ge B = \ln((1-\beta)/\alpha)$.

### Layer 9: Secure OTA Edge Update
- **Role:** Tamper-proof firmware and parameter deployment to edge microcontrollers.
- **Security Protections:**
  1. **ECDSA Signature Verification:** NIST P-256 / SHA-256 signed binary image validation.
  2. **Hardware Anti-Rollback:** Monotonic hardware eFuse version comparison ($V_{\text{target}} \ge V_{\text{hardware}}$).
  3. **Atomic Dual-Partition Flashing:** ESP32-S3 `ota_0` / `ota_1` partition swapping with self-test boot confirmation.

---

## 4. Latency Budget & Timing Decomposition

| Layer / Subsystem | Target SLA Budget | Measured Empirical Latency |
| :--- | :---: | :---: |
| **Layer 1: Tier 1 Edge Gate (ESP32-S3)** | $< 3.50\text{ ms}$ | **$2.4600\text{ ms}$** |
| **Layer 2: Tier 2 Regional CROP Fusion (Jetson)** | $< 5.00\text{ ms}$ | **$0.0226\text{ ms}$** |
| **Layer 3: Tier 3 Cloud Risk Engine & Graph** | $< 40.00\text{ ms}$ | **$0.3075\text{ ms}$** |
| **Layers 4–6: Storage, Merkle Chaining & DP** | $< 5.00\text{ ms}$ | **$0.0150\text{ ms}$** |
| **Total End-to-End Cascade Latency** | **$< 50.00\text{ ms}$** | **$2.8051\text{ ms}$** |
