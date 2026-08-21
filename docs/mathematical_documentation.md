# Mathematical Specifications & Formulations: PhysEdge-Cloud

**Document Reference:** PEC-MATH-SPEC-V1.0  
**Status:** Approved  
**Domain:** Embedded Signal Processing, Bayesian Fusion, Graph Spectral Theory, Conformal Inference  

---

## 1. Document Control & Notation Conventions

This document establishes the mathematical foundation for the **PhysEdge-Cloud** anomaly detection framework. 

### 1.1 Typographical Conventions
*   **Scalars:** Lowercase italic letters (e.g., $x, y, \alpha$).
*   **Vectors:** Bold lowercase letters (e.g., $\mathbf{x}, \mathbf{v}, \mathbf{j}$), assumed to be column vectors unless transposed ($\mathbf{x}^T$).
*   **Matrices:** Bold uppercase letters (e.g., $\mathbf{H}, \mathbf{A}, \boldsymbol{\mathcal{L}}$).
*   **Sets:** Calligraphic uppercase letters (e.g., $\mathcal{S}, \mathcal{V}, \mathcal{E}$).
*   **Estimates & Outputs:** Accent symbols denote estimators (e.g., $\hat{x}$ is the reconstruction of $x$).

### 1.2 Mathematical Notation Glossary

| Symbol | Mathematical Representation | Metric Units | Type |
| :--- | :--- | :--- | :--- |
| $\mathbf{X}_p(t)$ | Projective position coordinate of entity $p$ at time $t$ | Meters ($m$) | $2 \times 1$ Vector |
| $\mathbf{H}$ | Projective planar homography operator | Dimensionless | $3 \times 3$ Matrix |
| $\mathbf{j}(t)$ | Third-order temporal derivative of displacement (Jerk) | $m/s^3$ | $2 \times 1$ Vector |
| $S_j(t)$ | Standardized statistical anomaly surprise value | Dimensionless | Scalar |
| $\Pi(t)$ | Directional motion entropy rate (Panic Index) | $m/s^2$ | Scalar |
| $\ell_t$ | Logarithmic odds of anomaly probability | Nat / Log-Odds | Scalar |
| $\lambda_2$ | Algebraic connectivity of graph Laplacian (Fiedler value)| Dimensionless | Scalar |
| $q_{1-\alpha}$ | Conformal error margin quantile threshold | Probability | Scalar |
| $S_n$ | Sequential Probability Ratio Test value | Nat / Log-Odds | Scalar |

---

## 2. Layer 1: Embedded Kinematics (ESP32-S3)

### 2.1 Planar Projective Homography Mapping
The camera sensor outputs raw pixel positions $\mathbf{p} = [x, y]^T$. To map these to ground-plane metric coordinates $\mathbf{X}_m = [X_m, Y_m]^T$ (SI units), we apply a projective transformation $\pi: \mathbb{P}^2 \to \mathbb{R}^2$:

$$\begin{bmatrix} X_w \\ Y_w \\ W_w \end{bmatrix} = \mathbf{H} \cdot \begin{bmatrix} x \\ y \\ 1 \end{bmatrix} = \begin{bmatrix} h_{11} & h_{12} & h_{13} \\ h_{21} & h_{22} & h_{23} \\ h_{31} & h_{32} & h_{33} \end{bmatrix} \begin{bmatrix} x \\ y \\ 1 \end{bmatrix}$$

$$X_m(x,y) = \frac{h_{11}x + h_{12}y + h_{13}}{h_{31}x + h_{32}y + h_{33}}$$

$$Y_m(x,y) = \frac{h_{21}x + h_{22}y + h_{23}}{h_{31}x + h_{32}y + h_{33}}$$

#### Algorithmic Implementation (Q16.16 Fixed-Point)
For microcontroller execution, floating-point math is replaced by fixed-point representation where $x \cdot 2^{16} = \bar{x}$.
1.  **Numerator Computations:**
    $$\bar{N}_x = (h_{11}\bar{x} \gg 16) + (h_{12}\bar{y} \gg 16) + h_{13}$$
    $$\bar{N}_y = (h_{21}\bar{x} \gg 16) + (h_{22}\bar{y} \gg 16) + h_{23}$$
2.  **Denominator Computation:**
    $$\bar{D} = h_{31}\bar{x} + h_{32}\bar{y} + h_{33}\cdot 2^{16}$$
3.  **Numerical Stability Guard:**
    $$\text{if } \lvert\bar{D}\rvert < \text{THRESHOLD} \quad \text{then} \quad \text{abort-projection}()$$
4.  **Bilinear Division:**
    $$\bar{X}_m = (\bar{N}_x \ll 16) / \bar{D}, \quad \bar{Y}_m = (\bar{N}_y \ll 16) / \bar{D}$$

---

### 2.2 Numerical Derivatives & Smoothing
High-frequency noise is amplified during sequential differentiation. To prevent signal breakdown, a weighted smoothing filter is applied over a 3-frame rolling window.

#### Step 1: Discrete Finite Velocity Difference
$$\mathbf{v}(t) = \frac{\mathbf{X}_m(t) - \mathbf{X}_m(t-1)}{\Delta t}$$

#### Step 2: Smoothing Convolution
$$\mathbf{v}_{\text{smooth}}(t) = \sum_{k=0}^2 c_k \mathbf{v}(t-k) \quad \text{where} \quad c_0 = \frac{1}{2}, c_1 = \frac{1}{3}, c_2 = \frac{1}{6}$$

#### Step 3: Second and Third Derivatives
$$\mathbf{a}(t) = \frac{\mathbf{v}_{\text{smooth}}(t) - \mathbf{v}_{\text{smooth}}(t-1)}{\Delta t}$$

$$\mathbf{j}(t) = \frac{\mathbf{a}(t) - \mathbf{a}(t-1)}{\Delta t}$$

---

### 2.3 Statistical Surprise Gating
We define the standardized surprise metric $S_j(t)$ using rolling baseline parameters $(\mu_t, \sigma_t^2)$ maintained per device:

$$\mu_t = (1 - \alpha)\mu_{t-1} + \alpha \|\mathbf{j}(t)\|_2$$

$$\sigma^2_t = (1 - \alpha)\sigma^2_{t-1} + \alpha \left(\|\mathbf{j}(t)\|_2 - \mu_{t-1}\right)^2$$

$$S_j(t) = \frac{\|\mathbf{j}(t)\|_2 - \mu_t}{\sqrt{\sigma^2_t + \epsilon_0}} \quad \text{where} \quad \alpha = 0.05, \epsilon_0 = 10^{-4}$$

The binary trigger output $T(t)$ is defined as:

$$T(t) = \mathbb{I}\left( \sum_{i=0}^{4} \mathbb{I}(S_j(t-i) > 3.5) \ge 3 \right)$$

---

### 2.4 Shannon Motion Entropy
Let the velocity vectors be binned into $B=8$ angular sectors $\theta_b \in [0, 2\pi)$. The probability density $p_b$ of each sector is:

$$p_b = \frac{\sum_{i=1}^{N_{\text{flow}}} \|\mathbf{v}_i\|_2 \cdot \mathbb{I}(\text{Angle}(\mathbf{v}_i) \in \theta_b)}{\sum_{k=1}^B \sum_{i=1}^{N_{\text{flow}}} \|\mathbf{v}_i\|_2 \cdot \mathbb{I}(\text{Angle}(\mathbf{v}_i) \in \theta_k)}$$

The Shannon entropy is computed as:

$$H_t = -\sum_{b=1}^B p_b \log_2 (p_b + \delta_0) \quad \text{where} \quad \delta_0 = 10^{-6}$$

The **Panic Index** $\Pi_t$ tracking the rate of rise (weighted by mean flow velocity) is:

$$\Pi_t = \max\left(0, \frac{H_t - H_{t-1}}{\Delta t}\right) \cdot \left( \frac{1}{N_{\text{flow}}}\sum_{j=1}^{N_{\text{flow}}} \|\mathbf{v}_j\|_2 \right)$$

> **Note:** The notation table lists $\Pi(t)$ units as $m/s^2$: the entropy rate ($s^{-1}$) multiplied by mean velocity ($m/s$) yields acceleration-scale units.

---

### 2.5 Flow-Confidence-Weighted Motion Energy
To calculate the overall motion activity level in the scene while accounting for optical flow confidence, we define a non-dimensionalized Motion Energy ($E$) score. The motion energy $E$ at time $t$ aggregates the kinetic terms (velocity, acceleration, and jerk) of each active flow block, weighted by their respective block confidence score $w_i$:

$$E(t) = \frac{\sum_i w_i \left( \lambda_1 \frac{\|\mathbf{v}_{m,i}(t)\|_2^2}{v^2_{\text{ref}}} + \lambda_2 \frac{\|\mathbf{a}_{m,i}(t)\|_2^2}{a^2_{\text{ref}}} + \lambda_3 \frac{\|\mathbf{j}_{m,i}(t)\|_2^2}{j^2_{\text{ref}}} \right)}{\sum_i w_i}$$

where:
*   $w_i$: Optical flow block confidence score ($w_i \in [0, 255]$).
*   $\mathbf{v}_{m,i}(t), \mathbf{a}_{m,i}(t), \mathbf{j}_{m,i}(t)$: Metric velocity ($m/s$), acceleration ($m/s^2$), and jerk ($m/s^3$) vectors of block $i$ on the ground plane.
*   $v_{\text{ref}}, a_{\text{ref}}, j_{\text{ref}}$: Scaling/normalization constants used to ensure dimensional consistency.
*   $\lambda_1, \lambda_2, \lambda_3$: Weighting hyperparameters.

---

## 3. Layer 2: Regional Calibrated Fusion

### 3.1 Platt Calibration (Temperature Scaling)
Raw logits $f_s$ from semantic models (YOLOv8n, BlazePose) are mapped to calibrated probabilities:

$$P(z_s) = \frac{1}{1 + \exp\left(A_s f_s + B_s\right)}$$

where parameters $A_s, B_s$ are optimized via cross-entropy minimization on validation datasets:

$$\min_{A_s, B_s} -\frac{1}{M}\sum_{i=1}^M \left[ y_i \ln P(z_{s,i}) + (1 - y_i) \ln (1 - P(z_{s,i})) \right]$$

### 3.2 Time-Recursive Bayesian Log-Odds Fusion
Incoming probabilities are mapped to log-odds $\ell_t = \ln \left( \frac{P_t}{1 - P_t} \right)$. The state transition update is:

$$\ell_t = \gamma \ell_{t-1} + \sum_{s \in \mathcal{S}} \beta_s \ln \left( \frac{P(z_{s,t})}{1 - P(z_{s,t})} \right)$$

where:
*   $\gamma \in [0, 1]$ is the temporal decay factor ($0.95$).
*   $\beta_s$ represents the sensor reliability weights, optimized using regularized ECE minimization:

$$\min_{\boldsymbol{\beta}} \text{ECE}(\sigma(\boldsymbol{\ell}); \mathbf{y}) + \lambda_r \|\boldsymbol{\beta}\|^2_2$$

$$\text{ECE} = \sum_{m=1}^M \frac{\lvert B_m\rvert}{N} \left\lvert \text{acc}(B_m) - \text{conf}(B_m) \right\rvert$$

---

## 4. Layer 3: Cloud Risk Engine

### 4.1 Spectral Graph Instability
We define the spatiotemporal human interaction graph $G = (V, E)$. Let $p$ and $q$ be detected human nodes. The adjacency matrix $\mathbf{A} \in \mathbb{R}^{N \times N}$ is defined as:

$$A_{pq} = \exp\left(-\sigma_1 \|\mathbf{X}_p - \mathbf{X}_q\|^2_2\right) \cdot \max\left(0, \cos \theta_{pq}\right)$$

where $\theta_{pq}$ represents the angle between the velocity vectors $\mathbf{v}_p$ and $\mathbf{v}_q$:

$$\cos \theta_{pq} = \begin{cases} \frac{\mathbf{v}_p \cdot \mathbf{v}_q}{\|\mathbf{v}_p\|_2 \|\mathbf{v}_q\|_2} & \text{if } \|\mathbf{v}_p\|_2 > \epsilon \text{ and } \|\mathbf{v}_q\|_2 > \epsilon \\ 0 & \text{otherwise (stationary node)} \end{cases}$$

The Degree matrix $\mathbf{D}$ is diagonal: $D_{ii} = \sum_{j} A_{ij}$. The Normalized Laplacian $\mathcal{L}$ is:

$$\mathcal{L} = \mathbf{I} - \mathbf{D}^{-1/2} \mathbf{A} \mathbf{D}^{-1/2}$$

The eigenvalues are ordered: $0 = \lambda_1 \le \lambda_2 \le \dots \le \lambda_N$. The second smallest eigenvalue $\lambda_2$ (Fiedler value) measures algebraic connectivity. The Instability Index $\Delta \lambda_2$ is computed as:

$$\Delta \lambda_2 = \lambda_2(\mathcal{L}_{t-1}) - \lambda_2(\mathcal{L}_t)$$

### 4.2 Memory Autoencoder (Mem-AE) Score
The autoencoder maps input features $\mathbf{X}$ to latent vector $\mathbf{z}$ and queries a memory bank $\mathbf{M} \in \mathbb{R}^{C \times D}$ containing normal behavior templates:

$$\hat{\mathbf{z}} = \mathbf{w} \cdot \mathbf{M} = \sum_{c=1}^C w_c \mathbf{M}_c$$

where $w_c$ is calculated via softmax over cosine similarity scores:

$$w_c = \frac{\exp(d(\mathbf{z}, \mathbf{M}_c))}{\sum_{j=1}^C \exp(d(\mathbf{z}, \mathbf{M}_j))} \quad \text{where} \quad d(\mathbf{a},\mathbf{b}) = \frac{\mathbf{a} \cdot \mathbf{b}}{\|\mathbf{a}\|_2 \|\mathbf{b}\|_2}$$

The reconstruction error $r$ and latent Mahalanobis distance $m$ are combined into the anomaly score $A$:

$$A = \rho \frac{\|\mathbf{X} - \hat{\mathbf{X}}\|^2_2}{\text{dim}(\mathbf{X})} + (1 - \rho)\left(1 - \exp\left(-0.5 (\mathbf{z} - \boldsymbol{\mu}_z)^T \boldsymbol{\Sigma}_z^{-1} (\mathbf{z} - \boldsymbol{\mu}_z)\right)\right)$$

where $\psi(m) = 1 - \exp(-m)$ is a monotone bounded transform applied to the Mahalanobis distance $m = \sqrt{(\mathbf{z} - \boldsymbol{\mu}_z)^T \boldsymbol{\Sigma}_z^{-1} (\mathbf{z} - \boldsymbol{\mu}_z)}$.

### 4.3 Calibrated Risk Opinion Pool (CROP)
Individual risk outputs $P_k$ (from graph, pose, and autoencoder channels) are aggregated:

$$\log R = \sum_{k=1}^K \pi_k \log P_k - \log Z$$

where $\pi_k = \frac{1}{\sigma_k^2}$ represents the precision (inverse variance) of source $k$. The normalizing constant $Z$ ensures $R$ is a valid probability:

$$Z = \sum_{C'} \exp\left(\sum_{k=1}^K \pi_k \log P_k(C')\right)$$

summing over all risk classes $C'$, so that $R = \frac{1}{Z}\prod_k P_k^{\pi_k}$ is properly normalized to $[0, 1]$.

### 4.4 Adaptive Conformal Prediction
Let $E_i = \lvert Y_i - R_i \rvert$ be the calibration residuals. The adaptive threshold is updated using a rolling history of size $N_c$:

$$q_{1-\alpha} = \inf \left\lbrace q : \frac{1}{N_c}\sum_{i=t-N_c}^{t-1} \mathbb{I}(E_i \le q) \ge 1 - \alpha \right\rbrace$$

An alarm is triggered if:

$$R_t \ge q_{1-\alpha}$$

---

## 5. Layer 4: Adaptive Compute Orchestrator

### 5.1 Cost-Risk Lagrangian Optimization
The orchestrator routes events to minimize expected cloud cost while maintaining safety constraints:

$$\min_{\pi} \mathbb{E}[\text{Cost}(\pi)] \quad \text{s.t.} \quad \mathbb{E}[\text{Miss-Risk}(\pi)] \le \delta$$

We write the Lagrangian optimization as:

$$\mathcal{L}(\pi, \lambda) = \sum_{j} P_j \text{Cost}(\text{tier}_j) + \lambda \left( \sum_{j} P_j \text{Risk}(\text{tier}_j) - \delta \right)$$

Solving for the optimal policy routing bounds via the KKT conditions:

$$\frac{\partial \text{Cost}/\partial \pi_j}{\partial \text{Risk}/\partial \pi_j} = -\lambda \quad \text{(for all active policy variables } j\text{)}$$

This dictates the threshold boundaries for routing decisions: at optimality, the marginal cost increase per unit risk increase equals $\lambda$.

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
