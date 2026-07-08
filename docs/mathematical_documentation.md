# Mathematical Specifications & Formulations: PhysEdge-Cloud

This document contains the comprehensive mathematical specifications, step-by-step algorithms, variable dictionaries, dimensional representations, and fixed-point scale factor definitions for all components of the PhysEdge-Cloud system.

---

## 1. Toplogical Hierarchy & Variable Dictionary

### 1.1 Variable Specification Table

| Symbol | Representation | Data Type | Dimensions / Shape | Scale / Range |
| :--- | :--- | :--- | :--- | :--- |
| $(x, y)$ | Pixel Coordinates (2D) | `int16_t` | Vector $2 \times 1$ | $x \in [0, 160]$, $y \in [0, 120]$ |
| $(X_m, Y_m)$ | Metric Coordinates (2D) | `float32_t` | Vector $2 \times 1$ | $[-\infty, \infty]$ meters |
| $H$ | Homography Matrix | `float32_t` | Matrix $3 \times 3$ | Defined during calibration |
| $\mathbf{v}$ | Metric Velocity Vector | `float32_t` | Vector $2 \times 1$ | $m/s$ |
| $\mathbf{a}$ | Metric Acceleration Vector| `float32_t` | Vector $2 \times 1$ | $m/s^2$ |
| $\mathbf{j}$ | Metric Jerk Vector | `float32_t` | Vector $2 \times 1$ | $m/s^3$ |
| $S_j$ | Standardized Jerk Surprise | `float32_t` | Scalar | $[0, \infty]$ (dimensionless) |
| $\Pi_t$ | Panic Index | `float32_t` | Scalar | $[0, \infty]$ (dimensionless) |
| $C_{pq}$ | Convergence Rate | `float32_t` | Scalar | $m/s$ |
| $\text{TTC}_{pq}$ | Time-to-Collision Proxy | `float32_t` | Scalar | $[0, \infty]$ seconds |
| $\ell_t$ | Recursive Log-Odds | `float32_t` | Scalar | $[-\infty, \infty]$ |
| $\mathbf{A}$ | Adjacency Matrix | `float32_t` | Matrix $N \times N$ | $A_{pq} \in [0, 1]$ |
| $\mathcal{L}$ | Normalized Laplacian | `float32_t` | Matrix $N \times N$ | Eigenvalues $\lambda \in [0, 2]$ |
| $q_{1-\alpha}$ | Conformal Quantile Bound | `float32_t` | Scalar | $[0, 1]$ |
| $S_n$ | SPRT Cumulative Likelihood | `float32_t` | Scalar | $[-\infty, \infty]$ |

---

## 2. Layer 1: Embedded Kinematics (ESP32-S3)

### 2.1 Perspective Homography Projection
The 2D camera coordinates $(x_i, y_i)$ are transformed to ground-plane coordinates $(X_{m}, Y_{m})$ through the perspective homography projection. The coordinate vector in projective space $\mathbf{x} = [x, y, 1]^T$ is mapped to ground-plane coordinates as:

$$\begin{bmatrix} X_w \\ Y_w \\ W_w \end{bmatrix} = \mathbf{H} \cdot \begin{bmatrix} x \\ y \\ 1 \end{bmatrix} = \begin{bmatrix} H_{11} & H_{12} & H_{13} \\ H_{21} & H_{22} & H_{23} \\ H_{31} & H_{32} & H_{33} \end{bmatrix} \begin{bmatrix} x \\ y \\ 1 \end{bmatrix}$$

$$X_m = \frac{X_w}{W_w} = \frac{H_{11}x + H_{12}y + H_{13}}{H_{31}x + H_{32}y + H_{33}}$$

$$Y_m = \frac{Y_w}{W_w} = \frac{H_{21}x + H_{22}y + H_{23}}{H_{31}x + H_{32}y + H_{33}}$$

#### Fixed-Point Implementation (Q16.16 Format)
On the ESP32-S3, float arithmetic is replaced by fixed-point operations to conserve clock cycles:
$$\bar{x} = x \cdot 2^{16}, \quad \bar{y} = y \cdot 2^{16}$$
$$\bar{W}_w = \left( (H_{31} \cdot x + H_{32} \cdot y) \cdot 2^{-16} + H_{33} \cdot 2^{16} \right)$$
$$\bar{X}_m = \text{div\_q16}\left( H_{11} \cdot x + H_{12} \cdot y + H_{13} \cdot 2^{16}, \bar{W}_w \right)$$

### 2.2 Metric Derivatives & Filtering
To calculate velocity $\mathbf{v}$, acceleration $\mathbf{a}$, and jerk $\mathbf{j}$, finite difference calculations are performed. Let $\Delta t$ be the frame interval (typically $33.33 \\text{ ms}$ for $30 \\text{ FPS}$):

$$\mathbf{v}(t) = \frac{\mathbf{X}(t) - \mathbf{X}(t-1)}{\Delta t}$$

To eliminate noise amplification caused by consecutive differentiations, a 3-tap Savitzky-Golay smoothing window is applied to the velocity vectors:

$$\mathbf{v}_{\text{smooth}}(t) = \frac{3\mathbf{v}(t) + 2\mathbf{v}(t-1) + \mathbf{v}(t-2)}{6}$$

Acceleration and jerk vectors are computed sequentially from this smoothed velocity:

$$\mathbf{a}(t) = \frac{\mathbf{v}_{\text{smooth}}(t) - \mathbf{v}_{\text{smooth}}(t-1)}{\Delta t}$$

$$\mathbf{j}(t) = \frac{\mathbf{a}(t) - \mathbf{a}(t-1)}{\Delta t}$$

### 2.3 Statistical Surprise Gating
We keep track of normal patterns using a dynamic Exponentially Weighted Moving Average (EWMA) and variance baseline updated on non-triggering frames:

$$\mu_t = (1 - \alpha)\mu_{t-1} + \alpha \|\mathbf{j}_t\|$$

$$\sigma^2_t = (1 - \alpha)\sigma^2_{t-1} + \alpha (\|\mathbf{j}_t\| - \mu_t)^2$$

where $\alpha$ is set to $0.05$ (equivalent to a 20-frame observation window). Standardized surprise is calculated as:

$$S_j = \frac{\|\mathbf{j}_t\| - \mu_t}{\sqrt{\sigma^2_t + \epsilon}} \quad \text{where} \quad \epsilon = 10^{-4}$$

The trigger condition is defined as:

$$T_t = \begin{cases} 1 & \text{if } \sum_{i=0}^{m-1} \mathbb{I}(S_{j, t-i} > \kappa) \ge k \\ 0 & \text{otherwise} \end{cases}$$

For the target implementation, parameters are set to: $\kappa = 3.5$, $m = 5$, and $k = 3$.

### 2.4 Shannon Motion Entropy
Let $B$ be the number of directional bins ($B=8$, covering $45^\circ$ sectors). Let $C_b$ be the count of flow vectors in bin $b$, and $V_b$ be the sum of velocity magnitudes in bin $b$. The probability of flow in direction $b$ is:

$$p_b = \frac{C_b \cdot V_b}{\sum_{i=1}^B C_i \cdot V_i}$$

The Shannon entropy is calculated as:

$$H_t = -\sum_{b=1}^B p_b \log_2 (p_b + \delta_0) \quad \text{where} \quad \delta_0 = 10^{-6}$$

The **Panic Index** $\Pi_t$ tracking the rate of rise is:

$$\Pi_t = \max\left(0, \frac{H_t - H_{t-1}}{\Delta t}\right) \cdot \left( \frac{1}{N_{\text{flow}}}\sum_{j=1}^{N_{\text{flow}}} \|\mathbf{v}_j\| \right)$$

---

## 3. Layer 2: Regional Calibrated Fusion

### 3.1 Platt Calibration
Softmax confidence outputs $f_s$ of semantic detectors are calibrated using Platt temperature scaling to produce reliable probabilities:

$$P(z_s) = \frac{1}{1 + \exp(A_s f_s + B_s)}$$

### 3.2 Time-Recursive Bayesian Log-Odds Fusion
Let $\mathcal{S}$ be the set of active sensor sources $\mathcal{S} = \{\text{Kinematics}, \text{Object}, \text{Pose}, \text{Temporal}\}$.

For each sensor $s$, the log-likelihood ratio $LR_s(z_s)$ is computed as:

$$\ln LR_s(z_{s,t}) = \ln \left( \frac{P(z_{s,t} | \text{Anomaly})}{P(z_{s,t} | \text{Normal})} \right)$$

The recursive log-odds accumulator $\ell_t$ is defined as:

$$\ell_t = \gamma \ell_{t-1} + \sum_{s \in \mathcal{S}} \beta_s \ln LR_s(z_{s,t})$$

where:
*   $\gamma \in [0.90, 0.98]$ represents the temporal decay factor.
*   $\beta_s$ represents the learned reliability weights.

The final posterior probability is computed via the sigmoid function:

$$P(\text{Anomaly} | z_{1:t}) = \sigma(\ell_t) = \frac{1}{1 + e^{-\ell_t}}$$

The reliability weights $\boldsymbol{\beta}$ are optimized using regularized ECE minimization:

$$\min_{\boldsymbol{\beta}} \frac{1}{M}\sum_{m=1}^M \left| \text{conf}(B_m) - \text{acc}(B_m) \right| + \lambda_{\text{reg}} \|\boldsymbol{\beta}\|^2_2$$

---

## 4. Layer 3: Cloud Risk Engine

### 4.1 Spectral Graph Instability
We define the spatiotemporal human interaction graph $G = (V, E)$. Let $p$ and $q$ be detected human nodes. The adjacency matrix $\mathbf{A} \in \mathbb{R}^{N \times N}$ is defined as:

$$A_{pq} = \exp\left(-\sigma_1 \|\mathbf{X}_p - \mathbf{X}_q\|^2\right) \cdot \max\left(0, \cos \theta_{pq}\right)$$

where $\theta_{pq}$ represents the angle between the velocity vectors $\mathbf{v}_p$ and $\mathbf{v}_q$:

$$\cos \theta_{pq} = \frac{\mathbf{v}_p \cdot \mathbf{v}_q}{\|\mathbf{v}_p\| \|\mathbf{v}_q\|}$$

The Degree matrix $\mathbf{D}$ is diagonal: $D_{ii} = \sum_{j} A_{ij}$. The Normalized Laplacian $\mathcal{L}$ is:

$$\mathcal{L} = \mathbf{I} - \mathbf{D}^{-1/2} \mathbf{A} \mathbf{D}^{-1/2}$$

The eigenvalues are ordered: $0 = \lambda_1 \le \lambda_2 \le \dots \le \lambda_N$. The second smallest eigenvalue $\lambda_2$ (Fiedler value) measures algebraic connectivity. The Instability Index $\Delta \lambda_2$ is computed as:

$$\Delta \lambda_2 = \lambda_2(\mathcal{L}_{t-1}) - \lambda_2(\mathcal{L}_t)$$

### 4.2 Memory Autoencoder (Mem-AE) Score
The autoencoder maps input features $\mathbf{X}$ to latent vector $\mathbf{z}$ and queries a memory bank $\mathbf{M} \in \mathbb{R}^{C \times D}$ containing normal behavior templates:

$$\hat{\mathbf{z}} = \mathbf{w} \cdot \mathbf{M} = \sum_{c=1}^C w_c \mathbf{M}_c$$

where $w_c$ is calculated via softmax over cosine similarity scores:

$$w_c = \frac{\exp(d(\mathbf{z}, \mathbf{M}_c))}{\sum_{j=1}^C \exp(d(\mathbf{z}, \mathbf{M}_j))} \quad \text{where} \quad d(\mathbf{a},\mathbf{b}) = \frac{\mathbf{a} \cdot \mathbf{b}}{\|\mathbf{a}\| \|\mathbf{b}\|}$$

The reconstruction error $r$ and latent Mahalanobis distance $m$ are combined into the anomaly score $A$:

$$A = \rho \frac{\|\mathbf{X} - \hat{\mathbf{X}}\|^2_2}{\text{dim}(\mathbf{X})} + (1 - \rho)\left(1 - \exp\left(-0.5 (\mathbf{z} - \boldsymbol{\mu}_z)^T \boldsymbol{\Sigma}_z^{-1} (\mathbf{z} - \boldsymbol{\mu}_z)\right)\right)$$

### 4.3 Calibrated Risk Opinion Pool (CROP)
Individual probabilities $P_k$ (from graph, pose, and autoencoder channels) are aggregated:

$$\log R = \sum_{k=1}^K \pi_k \log P_k - \log Z$$

where $\pi_k = \frac{1}{\sigma_k^2}$ represents the precision (inverse variance) of source $k$. The partition normalizing constant $Z$ is:

$$Z = \int_{0}^{1} \exp\left(\sum_{k=1}^K \pi_k \log P\right) dP = \int_{0}^{1} P^{\sum \pi_k} dP = \frac{1}{\sum_k \pi_k + 1}$$

### 4.4 Adaptive Conformal Prediction
Let $E_i = |Y_i - R_i|$ be the calibration residuals. The adaptive threshold is updated using a rolling history of size $N_c$:

$$q_{1-\alpha} = \inf \left\{ q : \frac{1}{N_c}\sum_{i=t-N_c}^{t-1} \mathbb{I}(E_i \le q) \ge 1 - \alpha \right\}$$

An alarm is triggered if:

$$R_t \ge q_{1-\alpha}$$

---

## 5. Layer 4: Adaptive Compute Orchestrator

### 5.1 Cost-Risk Lagrangian Optimization
The orchestrator routes events to minimize expected cloud cost while maintaining safety constraints:

$$\min_{\pi} \mathbb{E}[\text{Cost}(\pi)] \quad \text{s.t.} \quad \mathbb{E}[\text{Miss-Risk}(\pi)] \le \delta$$

We write the Lagrangian optimization as:

$$\mathcal{L}(\pi, \lambda) = \sum_{j} P_j \text{Cost}(tier_j) + \lambda \left( \sum_{j} P_j \text{Risk}(tier_j) - \delta \right)$$

Solving for the optimal policy routing bounds:

$$\theta^* = \frac{\partial \text{Cost}}{\partial \text{Risk}} = -\lambda$$

This dictates the threshold boundaries for routing decisions.

---

## 6. Layer 8: Canary Deployment Controller

### 6.1 Sequential Probability Ratio Test (SPRT)
During rollout, we monitor the False Alarm Rate (FAR) $p$. We formulate the hypotheses:
*   $H_0: p = p_0$ (Acceptable FAR, $0.01$)
*   $H_1: p = p_1$ (Unacceptable FAR, $0.05$)

The cumulative log-likelihood ratio $S_n$ for $n$ observations containing $k$ false alarms is:

$$S_n = k \ln \left(\frac{p_1}{p_0}\right) + (n - k) \ln \left(\frac{1 - p_1}{1 - p_0}\right)$$

#### Decision Boundaries
*   **Abstain (Continue Rollout):** $A < S_n < B$
*   **Trigger Rollback (Abort):** $S_n \ge B \quad \text{where} \quad B = \ln \left( \frac{1 - \beta}{\alpha} \right)$
*   **Confirm Success (Escalate Rollout):** $S_n \le A \quad \text{where} \quad A = \ln \left( \frac{\beta}{1 - \alpha} \right)$

where $\alpha = 0.05$ represents Type I error, and $\beta = 0.10$ represents Type II error.
