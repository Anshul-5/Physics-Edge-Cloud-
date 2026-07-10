# Production Runbook: Deployment, Drift and Operations

This runbook defines the operational procedures for deploying updates, monitoring performance drift, and managing disaster recovery/graceful degradation modes in the PhysEdge-Cloud network.

---

## 1. Canary Deployment & Automated Rollback

All model weight updates and firmware revisions must undergo a canary deployment phase.

### Canary Strategy
1.  **Stage 1:** Deploy to $5\%$ of the target camera fleet for $72$ hours.
2.  **Stage 2:** Scale deployment to $20\%$ of the fleet for another $48$ hours.
3.  **Stage 3:** Rollout to $100\%$ of cameras.

### Automated Rollback Trigger: SPRT Formula
We use the **Sequential Probability Ratio Test (SPRT)** to evaluate whether the false-alarm rate (FAR) exceeds the baseline threshold $p_0$ to trigger a rollback to the backup firmware.

Let $x_i \in \{0, 1\}$ represent the classification outcome of a trigger validation (where $1$ is a False Alarm). We test:
*   $H_0: p = p_0$ (Acceptable FAR, e.g. $0.01$)
*   $H_1: p = p_1$ (Unacceptable FAR, e.g. $0.05$)

The log-likelihood ratio $S_n$ for $n$ events is calculated as:
$$S_n = \sum_{i=1}^n \log \frac{P(x_i | H_1)}{P(x_i | H_0)} = k \log \frac{p_1}{p_0} + (n - k) \log \frac{1 - p_1}{1 - p_0}$$
where $k$ is the number of false alarms observed.

*   **Rollback Condition:** If $S_n \ge B$, immediately abort rollout and rollback.
*   **Approval Condition:** If $S_n \le A$, accept candidate and escalate deployment.
*   **Threshold Parameters:**
    *   $A = \log \frac{\beta}{1 - \alpha}$
    *   $B = \log \frac{1 - \beta}{\alpha}$
    *   $\alpha$ (False Positive rate limit) = $0.05$
    *   $\beta$ (Missed Detection rate limit) = $0.10$

---

## 2. Drift Detection & Shadow Retraining

The model registry monitors telemetry packets to calculate population stability.

### Input Drift (Covariate Shift)
*   **Metric:** Kullback-Leibler (KL) Divergence on the incoming optical flow velocity distributions $P(X)$ versus baseline validation sets $Q(X)$:
    $$D_{\text{KL}}(P \mathbin{\Vert} Q) \approx \sum_{i} P(b_i) \log \frac{P(b_i)}{Q(b_i)} \cdot \Delta v$$
    where $b_i$ are velocity bins of width $\Delta v$ (discretized approximation of the continuous KL divergence).
*   **Threshold:** If $D_{\text{KL}} > 0.5$ for $24$ consecutive hours, raise a low-priority telemetry alarm. No retraining is triggered.

### Concept Drift
*   **Metric:** Shift in the label-conditional distribution $P(Y|X)$.
*   **Action:** Triggers offline compilation of the retraining dataset and initiates Layer 7.

### Model Promotion Gate
To promote a challenger model from the shadow retraining pipeline to production:
1.  Verify performance on the frozen benchmark validation set.
2.  The challenger must exceed the champion’s frame-level Area Under the Precision-Recall curve (AUPRC) by a statistically significant margin:
    $$\text{AUPRC}_{\text{challenger}} - \text{AUPRC}_{\text{champion}} \ge 1.645 \times \text{SE}_{\text{diff}}$$
    where $\text{SE}_{\text{diff}} = \sqrt{\text{SE}_{\text{challenger}}^2 + \text{SE}_{\text{champion}}^2}$ is the combined standard error of the difference (one-sided test at $\alpha = 0.05$), with each SE estimated via 1000-fold bootstrap on the frozen validation set.

---

## 3. Orchestration Policies & Disaster Fallback

### Compute Orchestrator Optimization
Layer 4 operates a Lagrangian threshold policy balancing cloud compute cost against missed anomaly risks:
$$\mathcal{L}(\theta) = \frac{\mathbb{E}[\text{Cloud Cost}]}{C_{\text{ref}}} + \lambda \big(\mathbb{E}[\text{Missed Detection Rate}] - \delta\big)$$
where $C_{\text{ref}}$ is a reference cost (e.g., baseline cloud-only pipeline cost) that normalizes the cost term to a dimensionless ratio, ensuring dimensional consistency with the probability-based risk term.
*   **High Risk Event:** If L2 escalates a posterior risk $\ge 0.70$, run the full Cloud suite (L3-Graph + AE).
*   **Medium Risk Event:** Posterior risk $[0.30, 0.70)$, run L3-AE but bypass Graph Spectral analysis.
*   **Low Risk Event:** Posterior risk $< 0.30$, terminate execution, archive local metadata, and skip cloud processing.

### Disaster Fallback (Edge-Only Mode)
If cloud connectivity is lost (HTTP 5xx errors or connection timeouts exceeding 1500 ms):
1.  **L1 Edge Gate** switches from sleep duty cycles to continuous processing.
2.  **L2 Regional Node** bypasses Cloud validation and acts as the primary decision node.
3.  Telemetry alerts are queued in regional SQLite transaction log files, flushing to the cloud once connectivity is restored.
