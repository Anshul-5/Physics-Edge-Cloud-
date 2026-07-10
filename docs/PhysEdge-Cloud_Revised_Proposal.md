**PhysEdge-Cloud**

**A Physics-Informed, Uncertainty-Calibrated Edge-to-Cloud Cascade for Real-Time Video Anomaly Detection**

*Revised Research Proposal (publication- and patent-oriented)*

*The original 9-layer architecture, ordering, and all layers are preserved. Additions are marked [NEW].*

# Abstract

Continuous video surveillance for safety-critical events (assaults, falls, collisions, crowd panic) faces a three-way tension between detection latency, energy/bandwidth cost, and privacy. Cloud-centric pipelines are accurate but expensive and privacy-invasive; edge-only pipelines are cheap but miss contextual anomalies. We propose **PhysEdge-Cloud**, a nine-layer edge-to-cloud cascade that uses inexpensive, explainable physics on a microcontroller-class device as a wake-gate, escalates only suspicious events through a calibrated probabilistic validation node, and reserves cloud reasoning for contextual adjudication. The central scientific claim is not any single detector but an **uncertainty-calibrated cascade** that attains a favorable accuracy/energy/cost Pareto while emitting distribution-free risk intervals.   **[NEW]** We add on-device perspective-normalized metric kinematics, a calibrated multi-source risk fusion (a log-opinion pool with conformal calibration), a closed-loop federated negative-constraint feedback mechanism, and a structural privacy contract that prevents image frames from leaving the edge boundary.

**Keywords:** video anomaly detection; edge computing; physics-informed sensing; uncertainty calibration; conformal prediction; sensor fusion; privacy-preserving surveillance; federated correction.

# 1. Introduction

## 1.1 Motivation

Most deployed anomaly-detection systems either stream all video to the cloud (high cost, bandwidth, and privacy exposure) or run a single edge model (limited context, brittle thresholds). Rare, safety-critical events make the economics worse: 24 hours of “nothing” is paid for to catch seconds of “something.” The design goal is to spend compute and bandwidth in proportion to suspicion.

**[NEW]**  Our premise is that the cheapest reliable evidence of physical danger is **kinematic**: violent or accidental events violate the smooth-motion prior of ordinary human activity (a punch, fall, or collision produces a jerk transient; panic produces a rapid rise in directional disorder). A sub-watt device can compute these cues and act as a near-zero-cost gate, so heavier semantic and contextual reasoning runs only when physics warrants it.

## 1.2 Problem statement

Given a stream of frames from a fixed camera, detect intervals containing safety-critical anomalies in (near) real time, subject to: (i) a hard edge energy/compute budget; (ii) a bounded cloud cost per camera-hour; (iii) a bounded false-alarm rate; and (iv) a privacy constraint that no raw imagery leaves the edge boundary. Formally, choose a per-frame decision and an escalation policy minimizing expected operating cost subject to a constraint on expected missed-detection risk and on false-alarm rate.

## 1.3 Research questions

- **RQ1.** Can microcontroller-class physics features (metric velocity/acceleration/jerk, motion entropy, interaction geometry) gate a cascade so that 80–90% of normal scenes are filtered at the edge without losing critical-event recall?

- **RQ2.** Does calibrated, uncertainty-weighted multi-source fusion improve the precision/recall and the reliability (calibration) of the final risk over an ad-hoc weighted sum?

- **RQ3.** Does the cascade achieve a better accuracy/energy/$ Pareto than edge-only and cloud-only baselines at matched accuracy?

- **RQ4.** Does closed-loop federated negative-constraint feedback reduce per-camera false-alarm rate over time without degrading recall, and what is the re-identification risk of the privacy-preserving uplink?

## 1.4 Hypotheses

- **H1:** metric (homography-normalized) kinematics yield camera-independent thresholds, reducing cross-scene false alarms vs pixel-space features.

- **H2:** a conformally-calibrated log-opinion pool achieves target false-alarm coverage within tolerance under mild non-stationarity.

- **H3:** negative-constraint feedback monotonically reduces a camera’s false-alarm rate across deployment time.

## 1.5 Contributions

We preserve the original nine-layer architecture and strengthen it with the following contributions, ordered by defensibility:

- **C1** (systems). A physics-gated edge→cloud cascade with measured edge feasibility and a documented accuracy/energy/cost Pareto.

- **C2**   **[NEW]** (method). A calibrated multi-source risk fusion (recursive log-odds + uncertainty-weighted log-opinion pool + conformal intervals).

- **C3**   **[NEW]** (mechanism). Closed-loop federated negative-constraint feedback from cloud adjudication to a specific edge device.

- **C4**   **[NEW]** (privacy). A structural egress contract: only skeletons/vectors/embeddings cross the edge boundary, with a quantified re-identification risk analysis.

- **C5**   **[NEW]** (formalism). On-device perspective-normalized metric kinematics and an adaptive-baseline jerk-surprise trigger.

# 2. Related work and research gap

Reconstruction- and prediction-based video anomaly detection (autoencoders, memory-augmented variants, future-frame prediction) and weakly-supervised multiple-instance methods on UCF-Crime/XD-Violence dominate accuracy benchmarks but assume cloud-scale compute. Crowd-anomaly methods use optical-flow statistics, motion entropy, and social-force models. Skeleton-based detectors offer privacy benefits and competitive accuracy. Graph/spectral methods model group interactions. MLOps practice contributes drift tracking, canary rollout, and signed OTA.

**[NEW]**  **Gap.** Three gaps persist. (1) These methods are evaluated for accuracy, rarely for the joint accuracy/energy/cost/latency Pareto under a real edge budget. (2) Final anomaly scores are typically uncalibrated point estimates with no distribution-free error control. (3) Feedback from high-tier adjudication back to a specific low-tier device, and a structurally enforced privacy boundary, are largely absent. PhysEdge-Cloud targets exactly these gaps; it does not claim a new low-level detector.

# 3. System overview (nine-layer pipeline, preserved)

The pipeline and its ordering are unchanged. Compute is escalated in proportion to suspicion: Edge (“something moved fast and weird”) → Regional (“it is a person and they fell”) → Cloud (“this is anomalous here; alert and preserve evidence”). Layers 4–9 govern cost, lifecycle, storage, learning, deployment, and updates.

| Layer | Role | Primary upgrade in this revision |
| --- | --- | --- |
| L1 | Physics edge gate (ESP32-S3) | Metric kinematics + adaptive jerk-surprise + panic index [NEW] |
| L2 | Regional probabilistic validation | Calibrated recursive log-odds fusion + abstain/defer [NEW] |
| L3 | Hybrid cloud risk engine | Spectral instability + memory-AE + CROP + conformal [NEW] |
| L4 | Adaptive compute orchestrator | Cost–risk Lagrangian policy + graceful degradation [NEW] |
| L5 | Model registry & drift | Input vs concept drift separation; version-bound predictions |
| L6 | Governed storage | Hash-chained forensic evidence tier [NEW] |
| L7 | Shadow retraining | Promotion gate + federated negative constraints [NEW] |
| L8 | Canary controller | Sequential-test auto-rollback on false-alarm guardrail [NEW] |
| L9 | Secure OTA | Signed weights + anti-rollback + explicit threat model |

# 4. Layer specifications

## Layer 1 — Physics-based edge detection unit (ESP32-S3)

**Objective:** detect motion abnormality using physics, not heavy AI. Frames are downscaled (160×120) and a sparse/block optical-flow field is computed in fixed-point. The unit emits scores and compressed keyframes only on a trigger, so the radio sleeps otherwise.

**[NEW]**  **Perspective-normalized metric kinematics.** A one-time guided 4-point homography H maps image points to the ground plane, so derivatives are in SI units and thresholds are camera-independent (addresses H1).

**[NEW-Eq 1]**   *X = π(H·[x,y,1]ᵀ);  vₘ = ΔX/Δt;  aₘ = Δvₘ/Δt;  jₘ = Δaₘ/Δt   (m/s, m/s², m/s³)*

**[NEW]**  **Adaptive jerk-surprise trigger.** Fire on a standardized deviation of metric jerk from a per-camera, per-time-of-day EWMA baseline (μₜ,σₜ), held over k-of-m frames (hysteresis). This is the self-tuning replacement for fixed thresholds.

**[NEW-Eq 3]**   *Sⱼ = (‖jₘ‖ − μₜ)/√(σ²ₜ+ε);  trigger if Sⱼ > κ for k-of-m frames*

**Motion energy** (flow-confidence-weighted; replaces the ad-hoc v²+a²):

**[NEW-Eq 4]**   *E = Σᵢ wᵢ(λ₁‖vₘ,ᵢ‖²/v²_ref + λ₂‖aₘ,ᵢ‖²/a²_ref + λ₃‖jₘ,ᵢ‖²/j²_ref)/Σᵢ wᵢ   (non-dimensionalized)*

**Directional motion entropy and panic index.** Entropy of magnitude-weighted flow-direction histogram; the panic index uses its rate of rise.

**[NEW-Eq 5]**   *Hₜ = −Σ_b p_b log₂ p_b ;  Πₜ = max(0, dHₜ/dt)·(1/N_flow)Σ‖vⱼ‖   (panic index [NEW], units: m/s²)*

**Interaction geometry** for blob pairs (convergence and time-to-collision proxy): rapid collision and aggressive approach are flagged.

**[NEW-Eq 6]**   *C_{pq} = −d‖X_p−X_q‖/dt ;  TTC_{pq} = ‖X_p−X_q‖/C_{pq} if C_{pq} > 0, else ∞*

**Outputs:** motion_energy_score, interaction_instability_score, entropy/panic score, suspicion_probability, compressed keyframes, plus a **dominant-cause tag** [NEW] for explainability. **Rationale:** low power, no GPU, reduced bandwidth, explainable, filters 80–90% of normal scenes (RQ1).

## Layer 2 — Regional probabilistic validation node

**Objective:** semantic confirmation — is this motion anomaly actually dangerous? Lightweight object detection (YOLOv8n, INT8) and pose estimation (BlazePose) extract person/vehicle presence, crowd density, arm angles, body lean, hand extension, and fall posture; a small CNN/GRU captures short escalation patterns.

**[NEW]**  **Calibrated recursive fusion.** Detector/pose confidences are temperature-scaled, then fused as a recursive log-odds filter with learned per-source reliabilities — evidence accumulates over time rather than per-frame, and posteriors are calibrated (addresses RQ2).

**[NEW-Eq 7]**   *ℓₜ = γℓₜ₋₁ + Σ_s β_s log LR_s(z_s);  P(anomaly|z₁:ₜ)=σ(ℓₜ)*

**[NEW-Eq 8]**   *min_β  ECE(σ(ℓ);y) + λ‖β‖²   (reliabilities calibrated, not raw softmax)*

**[NEW]**  **Abstain/defer action.** When pose/detector confidence is low, the node escalates rather than deciding, trading cloud cost for lower false negatives on the dangerous tail.

**Output:** posterior event probability (with variance). **Rationale:** fewer false positives, filters normal running/dancing, reduces cloud GPU usage, improves subtle-aggression detection.

## Layer 3 — Hybrid cloud risk engine (math + light ML)

**Objective:** deep contextual behavioral reasoning on a moderate-GPU server.

**Graph interaction model.** People are nodes; edges encode proximity and motion similarity. 

**[NEW]**  Instability is quantified by the change in algebraic connectivity (graph fragmentation → fights/dispersal) and the normalized-Laplacian spectral shift from a learned normal spectrum, with a permutation-invariant readout.

**[NEW-Eq 9]**   *Δλ₂ = λ₂(ℒₜ₋₁)−λ₂(ℒₜ);  Δ_spec = ‖λ(ℒₜ)−λ̄_normal‖₂*

**Reconstruction model.** A memory-augmented autoencoder trained only on normal behavior; the anomaly score combines normalized reconstruction error with latent Mahalanobis distance to avoid the “reconstructs anomalies too well” failure.

**[NEW-Eq 10]**   *r=‖X−X̂‖²/d;  m=√((z−μ_z)ᵀΣ_z⁻¹(z−μ_z));  A=ρr+(1−ρ)(1−exp(−m))  (ψ(m)=1−exp(−m), monotone bounded transform)*

**[NEW]**  **Risk aggregation — calibrated opinion pool (replaces the weighted sum of W1…W4).** Each instability source (motion, graph, pose, reconstruction) contributes a probability weighted by its inverse variance (precision), combined in log space; the result is wrapped in conformal prediction for a distribution-free risk interval.

**[NEW-Eq 11]**   *log R ∝ Σ_k π_k log P_k ,  π_k = 1/σ²_k   (CROP, normalized via Z = Σ_C' exp(Σ_k π_k log P_k(C')))*

**[NEW-Eq 12]**   *Alarm iff R ≥ q_{1−α};  P(false alarm) ≤ α on exchangeable data   (conformal)*

**Outputs:** final_risk_probability, confidence_interval, event_type, 256-dim embedding, model_version. **Rationale:** contextual reasoning, crowd-level monitoring, false-positive reduction, long-term behavioral analysis, audit-grade reliability.

## Layer 4 — Adaptive compute orchestrator

**Objective:** control cloud cost. Low risk → skip heavy modules; medium → partial analysis; high → full pipeline. Uses priority queues, batched GPU inference, and autoscaling.

**[NEW]**  **Formal policy.** Select compute tier to minimize expected cloud cost subject to a bound on expected missed-detection risk — a Lagrangian/threshold policy with an explicit cost–risk trade-off (addresses RQ3). Adds a graceful-degradation mode (edge-only fallback) when the cloud is unavailable.

**[NEW-Eq 13]**   *π* = argmin_π E[cost(π)] s.t. E[miss-risk(π)] ≤ δ  ⇔  threshold on calibrated risk + its CI*

## Layers 5, 6, 7 — governance and training

### Layer 5 — Model registry & tracking

- Tracks: model version, training-dataset hash, drift score, deployment timeline; supports rollback, audit trace, compliance proof.

- **[NEW]** Separates input drift (population stability / KL on feature distributions) from concept drift (label-conditional); only the latter triggers L7. Every prediction is bound to a model-version hash for reproducibility.

### Layer 6 — Governed storage system

- Tier A raw video = 90 days; Tier B event clips = 1–3 years (SHA-256 + timestamp signature); Tier C metadata = 5+ years (embeddings, risk score, model version). Database: PostgreSQL + pgvector.

- **[NEW]** Tier B is a hash chain / Merkle log binding each clip to its model version and triggering kinematics, giving tamper-evident chain-of-custody. Long-tier records contain only embeddings/skeletons, consistent with the privacy contract.

### Layer 7 — Shadow retraining pipeline

- Objective: safe continual learning, no real-time unstable learning. Collect metadata → retrain offline → compare → approve if improved.

- **[NEW]** Champion/challenger with a pre-registered promotion gate (improvement must exceed a statistically significant margin on a frozen validation set). Cloud-adjudicated false positives enter as negative-constraint supervision.

## Layers 8, 9 — deployment and updates

### Layer 8 — Canary deployment controller

- Deploy new model to 5–10% of cameras; monitor false-positive and drift metrics; then expand.

- **[NEW]** Automatic rollback on a guardrail (false alarms per camera-hour) using a sequential test, so rollback is statistically principled rather than eyeballed.

### Layer 9 — Secure OTA edge update

- Encrypted firmware update, signed model weights, rollback support; ensures field scalability, security, controlled evolution.

- **[NEW]** Explicit threat model: man-in-the-middle, version downgrade, and model-poisoning, mitigated by secure boot, signature verification, and an anti-rollback counter.

# 5. Cross-cutting enhancements

The five original recommendations are integrated as system-wide mechanisms (all marked [NEW]).

### 5.1 Perspective-aware kinematics

**[NEW]**  Homography calibration (Eq 1) converts pixel-jerk to m/s³ so thresholds are universal across mounting geometry; re-projection error is reported to the registry as a calibration health check.

### 5.2 Dynamic entropy/energy baselines

**[NEW]**  Per-camera, per-time-of-day EWMA baselines for entropy and energy (Eq 3) make the system self-tuning: triggers fire only on chaos significantly above the usual chaos for that place and time.

### 5.3 Privacy-preserving uplink

**[NEW]**  Above L2, only skeletal joints, vectorized motion paths, and embeddings cross the boundary — never frames. This is an enforced egress contract, not a convention. The cloud sees a mathematical skeleton, supporting a near-zero-PII claim; Section 8 quantifies residual re-identification risk honestly.

### 5.4 Federated negative-constraint correction

**[NEW]**  When the cloud adjudicates a trigger as a false positive (e.g., an insect on the lens), it returns a per-device negative constraint that re-tunes that camera’s baseline/threshold and feeds L7. This closed loop is the system’s strongest novel mechanism (addresses RQ4).

### 5.5 Temporal conflict buffer

**[NEW]**  A 5–10 s circular buffer of pre-trigger kinematics is uplinked with the event, letting L3 see the escalation (“calm before the storm”) and distinguish a sudden hug from a sudden tackle — kinematics, not video, are buffered, preserving privacy.

# 6. Theoretical and complexity analysis

## 6.1 Complexity

| Layer | Time (per frame/event) | Space / footprint |
| --- | --- | --- |
| L1 edge | O(N_flow) sparse flow + O(B) entropy + O(P²) pairwise geometry for P blobs | KB-scale; INT8; fits MCU SRAM/flash |
| L2 regional | O(detector) + O(pose) + O(GRU window) | Quantized models, tens of MB |
| L3 cloud | Graph eig: O(P³) dense or O(P·k) sparse top-k; AE forward O(model) | GPU-resident |
| L4–L9 | O(1)–O(log fleet) bookkeeping | Registry/DB |

P (people per frame) is small for typical scenes; for crowds, top-k sparse spectral methods keep L3 tractable.

## 6.2 The one formal guarantee

**[NEW]**  We make a single, honest formal claim: under exchangeability, conformal calibration (Eq 12) bounds the false-alarm rate at α. Surveillance streams are non-stationary and temporally correlated, so we use a **time-adaptive** conformal variant and report empirical coverage rather than asserting the bound unconditionally. No “theorem” beyond this is claimed.

# 7. Evaluation protocol

**Datasets:** UCF-Crime, XD-Violence, ShanghaiTech, CUHK Avenue, UBnormal, NWPU Campus, plus a multi-camera deployment set (≥50 cameras, ≥2 weeks) for systems metrics. **Metrics:** frame-AUC/AP/ROC/EER; ECE and conformal empirical coverage; false alarms per camera-hour; detection latency; edge mJ/inference, fps, footprint, mAh/day; network kb/event and % vs raw; cloud GPU-s/event and $/1k-events; OOD AUROC; drift-recovery time.

**Baselines:** MNAD, MemAE, future-frame prediction; Sultani-MIL, RTFM, MGFN, S3R; skeleton STG-NF (fair comparison for the privacy path); and edge-only / cloud-only / naive-cascade ablations.

**Ablations:** remove each layer L1–L9; metric vs pixel kinematics; ±panic index; ±TTC; weighted-sum vs CROP; ±conformal; ±temporal recursion; feedback loop on/off (false-alarm rate over deployment time — the headline systems result).

**Rigor:** fixed splits; mean ± 95% CI over ≥5 seeds; leave-one-scene-out for cross-scene generalization; pre-registered promotion gate. **Hardware:** ESP32-S3 (+ Cortex-M / Jetson-Nano reference) with measured power (INA219/Otii); Jetson Orin regional; one mid-class GPU cloud. **Stress:** spoof triggers, feedback-channel poisoning, OTA downgrade, burst/mass-panic load, cloud-outage fallback.

# 8. Limitations, threats to validity, ethics, privacy, security

## 8.1 Limitations & failure cases

- Optical flow on an MCU is low-resolution and sparse; jerk (a third difference) amplifies noise — we report the noise floor, smoothing, and the resulting flow-quality/accuracy trade-off.

- Single fixed camera without persistent multi-object tracking limits graph identity; we state this and treat spectral features as scene-level, not identity-level.

- Scene-specific baselines risk site overfitting; cross-scene results are reported even though they typically degrade.

## 8.2 Threats to validity

- **Internal:** trigger noise and detector jitter may drive spectral features; controlled with ablations and noise analysis.

- **External:** benchmark scenes differ from deployment; cross-scene and field results address this.

- **Construct:** “anomaly” labels are context-dependent; we report per-category results.

## 8.3 Privacy (honest)

**[NEW]**  The egress contract removes raw imagery, but skeletons, gait, and trajectories remain partially re-identifiable. We therefore **quantify** re-identification risk (e.g., linkage attacks on trajectories/gait) and describe mitigations (coarsening, k-anonymity on paths, on-device differential-privacy noise) rather than claiming absolute anonymity. “Near-zero-PII” is the defensible framing; “zero-PII” is not.

## 8.4 Security

- Threat model spans OTA (MITM, downgrade, poisoning), the feedback channel (constraint poisoning), and storage tampering; mitigations are signed/anti-rollback OTA, authenticated feedback with rate limits and outlier rejection, and hash-chained evidence.

## 8.5 Ethics & fairness

**[NEW]**  Surveillance carries real harms. We discuss deployment governance, demographic-fairness auditing of triggers (does jerk/pose-based triggering fire unequally across groups?), human-in-the-loop adjudication for any action, and the dual-use risk — reported transparently rather than ignored.

# 9. Conclusion and future work

PhysEdge-Cloud preserves a pragmatic nine-layer edge→cloud architecture and elevates it from an engineering sketch toward a research contribution by adding metric on-device kinematics, calibrated uncertainty-aware fusion with distribution-free risk control, a closed-loop federated correction mechanism, and a structural privacy boundary. The defensible scientific claim is the calibrated physics-gated cascade and its accuracy/energy/cost Pareto, not any single detector.

**Future work:** persistent multi-camera tracking for identity-aware graphs; learned (not hand-tuned) escalation policies via constrained RL; broader federated learning beyond negative constraints; formal privacy accounting (differential privacy budgets) for the uplink; and real multi-site deployment studies.

**[NEW]**  **Honesty statement.** This document is a proposal. Its central claims are empirical and require the experiments in Section 7 — measured edge power/fps, benchmark results with baselines and confidence intervals, calibration under non-stationarity, quantified re-identification risk, and cross-scene generalization — before any venue or examiner should be persuaded.
