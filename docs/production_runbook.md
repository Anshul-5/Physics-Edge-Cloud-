# Production Operations & Deployment Runbook: PhysEdge-Cloud

**Document Reference:** PEC-OPS-RUNBOOK-V2.9  
**Classification:** Operational Governance, Reliability Engineering & SRE Manual  
**Target Availability SLA:** 99.99% Uptime / Latency SLA < 50.0 ms  

---

## 1. Progressive Canary Deployment & Safety Rollbacks

To prevent model regressions and out-of-distribution hallucinations from entering production fleets, PhysEdge-Cloud executes deterministic progressive rollouts governed by Wald's Sequential Probability Ratio Test (SPRT).

### 1.1 Progressive Staged Rollout Schedule
- **Stage 0 (Canary 5%):** Deployed to 5% of cameras for 72 operational hours.
- **Stage 1 (Extended Canary 20%):** Deployed to 20% of cameras for 48 operational hours upon Stage 0 approval.
- **Stage 2 (Fleetwide 100%):** Promoted to 100% of production devices.

### 1.2 Wald's Sequential Probability Ratio Test (SPRT) Formulation
During canary execution, streaming alert verification outcomes $x_i \in \{0, 1\}$ ($1 = \text{False Positive}$, $0 = \text{True Anomaly}$) are evaluated against statistical hypotheses:
- $H_0: p = p_0$ (Acceptable Baseline False Alarm Rate, $p_0 = 0.01$)
- $H_1: p = p_1$ (Unacceptable Elevated False Alarm Rate, $p_1 = 0.05$)

The cumulative log-likelihood ratio $S_n$ for $n$ observations containing $k$ false positives is:

$$S_n = k \ln \left(\frac{p_1}{p_0}\right) + (n - k) \ln \left(\frac{1 - p_1}{1 - p_0}\right)$$

### 1.3 Decision Boundaries & Automatic Rollback Action
- **Upper Abort Bound ($B$):** Trigger automated instant rollback to champion model:
  $$S_n \ge B = \ln \left( \frac{1 - \beta}{\alpha} \right)$$
- **Lower Accept Bound ($A$):** Confirm baseline safety and escalate rollout to next stage:
  $$S_n \le A = \ln \left( \frac{\beta}{1 - \alpha} \right)$$
- **Continue Monitoring:** $A < S_n < B$
- **Significance Parameters:** $\alpha = 0.05$ (Type I error probability), $\beta = 0.05$ (Type II error probability).

---

## 2. Statistical Drift Tracking & Shadow Retraining

### 2.1 Covariate Shift (Input Feature Drift)
The cloud engine continuously calculates the symmetric Kullback-Leibler (KL) divergence over a 24-hour sliding window against baseline reference distributions:

$$D_{\text{KL}}(P \parallel Q) = \sum_{b=1}^B P(b) \ln \left(\frac{P(b)}{Q(b)}\right)$$

- If $D_{\text{KL}} > 0.5$ for 24 consecutive hours, a telemetry warning is emitted to SRE dashboards. No model retraining is initiated.

### 2.2 Concept Drift & Shadow Retraining Initiation
- **Trigger:** A statistically significant shift in the posterior distribution $P(Y \mid X)$ derived from operator false-positive feedback triggers the Layer 7 shadow retraining pipeline.
- **Champion / Challenger Promotion Gate:** A challenger model is promoted only if it achieves a statistically significant improvement in Area Under the Precision-Recall Curve (AUPRC):
  $$\text{AUPRC}_{\text{challenger}} - \text{AUPRC}_{\text{champion}} \ge 1.96 \cdot \text{SE}_{\text{diff}}$$
  where $\text{SE}_{\text{diff}} = \sqrt{\text{SE}_{\text{challenger}}^2 + \text{SE}_{\text{champion}}^2}$ is computed via 1,000-fold bootstrap resampling on a frozen benchmark validation set.

---

## 3. High-Availability & Disaster Recovery Modes

### 3.1 Graceful Degradation (Edge-Autonomous Mode)
If central cloud connectivity is interrupted ($> 1500\text{ ms}$ latency timeout or HTTP 5xx errors):
1. **Tier 1 (ESP32-S3):** Switches from opportunistic wake-gating to continuous streaming mode.
2. **Tier 2 (NVIDIA Jetson):** Assumes full autonomous decision authority, evaluating CROP log-odds locally without cloud escalation.
3. **Local Queuing:** Escalated telemetry is written to regional SQLite write-ahead log (WAL) storage and flushed upon cloud reconnection.

### 3.2 Recovery & Health Checklist
- Verify PostgreSQL `pgvector` index responsiveness ($< 5\text{ ms}$ query latency).
- Validate Merkle hash-chain continuity via `hash_chain.validate_chain()`.
- Check Prometheus metric exporters for buffer depths and CPU/GPU memory watermarks.
