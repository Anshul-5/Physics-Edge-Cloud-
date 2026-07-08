# Mathematical Specifications & Formulations: PhysEdge-Cloud

This document contains the complete mathematical specifications, derivations, and algorithmic formulations used in the PhysEdge-Cloud architecture across all 9 layers.

---

## 1. Layer 1: Embedded Kinematics (ESP32-S3)

### 1.1 Perspective Homography Projection
To calculate velocity, acceleration, and jerk in physical units rather than pixel distances, we project 2D image plane coordinates $(x,y)$ to ground-plane coordinates $(X_m, Y_m)$ using a stored $3 \times 3$ homography matrix $H$:

$$H = \begin{bmatrix} H_{11} & H_{12} & H_{13} \\ H_{21} & H_{22} & H_{23} \\ H_{31} & H_{32} & H_{33} \end{bmatrix}$$

The projection mapping $\pi: \mathbb{R}^2 \to \mathbb{R}^2$ is calculated as:

$$X_m = \frac{H_{11}x + H_{12}y + H_{13}}{H_{31}x + H_{32}y + H_{33}}$$

$$Y_m = \frac{H_{21}x + H_{22}y + H_{23}}{H_{31}x + H_{32}y + H_{33}}$$

*Safety Guard:* Discard points where $|H_{31}x + H_{32}y + H_{33}| < \epsilon$ (where $\epsilon = 10^{-6}$) to prevent division by zero.

### 1.2 Metric Derivatives
From ground-plane coordinates $X(t) = [X_m(t), Y_m(t)]^T$, derivatives are computed using backward finite differences:

$$\mathbf{v}(t) = \frac{\mathbf{X}(t) - \mathbf{X}(t-1)}{\Delta t}$$

$$\mathbf{a}(t) = \frac{\mathbf{v}(t) - \mathbf{v}(t-1)}{\Delta t}$$

$$\mathbf{j}(t) = \frac{\mathbf{a}(t) - \mathbf{a}(t-1)}{\Delta t}$$

To mitigate high-frequency noise amplification from consecutive derivatives, we apply a 3-tap Exponentially Weighted Moving Average (EWMA) filter to the velocity vector before computing acceleration and jerk:

$$\mathbf{v}_{\text{smooth}}(t) = (1 - \lambda_{\text{smooth}})\mathbf{v}_{\text{smooth}}(t-1) + \lambda_{\text{smooth}}\mathbf{v}(t)$$

### 1.3 Statistical Surprise Gating
Instead of static thresholds, the edge gate triggers on the statistical surprise score of metric jerk $S_j$. We maintain rolling mean $\mu_t$ and variance $\sigma_t^2$ of jerk magnitudes:

$$\mu_t = (1 - \alpha_b)\mu_{t-1} + \alpha_b \|\mathbf{j}_t\|$$

$$\sigma^2_t = (1 - \alpha_b)\sigma^2_{t-1} + \alpha_b (\|\mathbf{j}_t\| - \mu_t)^2$$

where $\alpha_b$ is the baseline update rate. The standardized surprise is defined as:

$$S_j = \frac{\|\mathbf{j}_t\| - \mu_t}{\sqrt{\sigma^2_t + \epsilon_0}}$$

A trigger event is declared if:

$$\sum_{i=0}^{m-1} \mathbb{I}(S_{j, t-i} > \kappa) \ge k$$

representing a $k$-of-$m$ frame hysteresis condition.

### 1.4 Directional Motion Entropy & Panic Index
We partition moving optical flow vectors into $B$ directional histogram bins. Let $p_b$ be the probability of flow falling in direction bin $b$:

$$H_t = -\sum_{b=1}^B p_b \log_2 p_b$$

The **Panic Index** $\Pi_t$ tracks the rate of rise in entropy scaled by the mean speed $\bar{v}_t$:

$$\Pi_t = \max\left(0, \frac{dH_t}{dt}\right) \cdot \bar{v}_t \approx \max\left(0, \frac{H_t - H_{t-1}}{\Delta t}\right) \cdot \bar{v}_t$$

### 1.5 Time-to-Collision (TTC) Proxy
For any pair of tracked blobs $p$ and $q$ with coordinates $X_p$ and $X_q$:

$$\text{Distance } D_{pq}(t) = \|\mathbf{X}_p(t) - \mathbf{X}_q(t)\|$$

$$\text{Convergence Rate } C_{pq}(t) = -\frac{dD_{pq}}{dt} \approx \frac{D_{pq}(t-1) - D_{pq}(t)}{\Delta t}$$

$$\text{TTC}_{pq}(t) \approx \frac{D_{pq}(t)}{\max\left(C_{pq}(t), \epsilon_{\text{col}}\right)}$$

---

## 2. Layer 2: Regional Calibrated Fusion

### 2.1 Platt Calibration (Logit Normalization)
Outputs of YOLOv8n and BlazePose are calibrated to map raw scores $f$ to true probabilities:

$$P(y=1 | f) = \sigma(Af + B) = \frac{1}{1 + e^{Af + B}}$$

Parameters $A$ and $B$ are optimized by minimizing the negative log-likelihood on validation sets.

### 2.2 Time-Recursive Bayesian Log-Odds Fusion
Evidence is combined recursively across time. The log-odds $\ell_t = \ln\left(\frac{P_t}{1-P_t}\right)$ is updated as:

$$\ell_t = \gamma \ell_{t-1} + \sum_{s \in \mathcal{S}} \beta_s \ln LR_s(z_{s, t})$$

where:
*   $\gamma \in [0, 1]$ represents the temporal decay factor.
*   $\beta_s$ represents the learned reliability weight for sensor $s$.
*   $LR_s(z_{s, t}) = \frac{P(z_{s, t} | \text{Anomaly})}{P(z_{s, t} | \text{Normal})}$ is the likelihood ratio of observation $z_s$.

The weights $\boldsymbol{\beta}$ are learned by minimizing the regularized Expected Calibration Error (ECE):

$$\min_{\boldsymbol{\beta}} \text{ECE}(\sigma(\boldsymbol{\ell}); \mathbf{y}) + \lambda_r \|\boldsymbol{\beta}\|^2$$

---

## 3. Layer 3: Cloud Risk Engine

### 3.1 Spectral Graph Instability
We define the spatiotemporal human interaction graph $G = (V, E)$. The adjacency matrix $A$ has elements:

$$A_{pq} = \exp\left(-\sigma_1 \|\mathbf{X}_p - \mathbf{X}_q\|^2\right) \cdot \max\left(0, \cos \theta_{pq}\right)$$

where $\theta_{pq}$ represents the angle between the velocity vectors of $p$ and $q$. The Normalized Laplacian is:

$$\mathcal{L} = \mathbf{I} - \mathbf{D}^{-1/2} \mathbf{A} \mathbf{D}^{-1/2}$$

where $D_{ii} = \sum_j A_{ij}$. We calculate the second smallest eigenvalue (Fiedler value) $\lambda_2(\mathcal{L})$. Spectral instability is computed as:

$$\Delta \lambda_2 = \lambda_2(\mathcal{L}_{t-1}) - \lambda_2(\mathcal{L}_t)$$

A large positive shift indicates sudden graph fragmentation (people scattering) or clustering (fights/crowd compression).

### 3.2 Memory Autoencoder (Mem-AE) Score
The anomaly reconstruction score combines pixel reconstruction error and latent space Mahalanobis distance:

$$A_{\text{recon}} = \rho \frac{\|\mathbf{X} - \hat{\mathbf{X}}\|^2}{d} + (1 - \rho)\psi(m)$$

where:
*   $m = \sqrt{(\mathbf{z} - \boldsymbol{\mu}_z)^T \boldsymbol{\Sigma}_z^{-1} (\mathbf{z} - \boldsymbol{\mu}_z)}$ is the Mahalanobis distance in the latent memory space.
*   $\psi(\cdot)$ is a scaling function mapping distance to $[0,1]$.

### 3.3 Precision-Weighted Risk Opinion Pool (CROP)
Individual risk outputs $P_k$ (from graph spectral, pose, and autoencoder channels) are aggregated in log space:

$$\log R = \sum_k \pi_k \log P_k - \log Z$$

where $\pi_k = \frac{1}{\sigma_k^2}$ represents the precision (inverse variance) of source $k$, and $Z$ is the partition normalizing constant:

$$Z = \int \prod_k P_k^{\pi_k} dP$$

### 3.4 Adaptive Conformal Prediction
To guarantee false-alarm control bound $\alpha$ under non-stationary distributions, we calculate residuals $E_i = |Y_i - R_i|$. The dynamic quantile threshold $q_{1-\alpha}$ is defined as:

$$q_{1-\alpha} = \inf \left\{ q : \frac{1}{N}\sum_{i=t-N}^{t-1} \mathbb{I}(E_i \le q) \ge 1 - \alpha \right\}$$

The alert fires if and only if $R_t \ge q_{1-\alpha}$.

---

## 4. Layer 4: Adaptive Orchestrator

### 4.1 Cost-Risk Lagrangian Policy
The compute router minimizes expected cloud processing cost subject to a constraint on missed anomaly risks:

$$\min_{\pi} \mathbb{E}[\text{Cost}(\pi)] \quad \text{s.t.} \quad \mathbb{E}[\text{Miss-Risk}(\pi)] \le \delta$$

We formulate this using a Lagrangian multiplier:

$$\mathcal{L}(\pi, \lambda) = \mathbb{E}[\text{Cost}(\pi)] + \lambda \Big(\mathbb{E}[\text{Miss-Risk}(\pi)] - \delta\Big)$$

The optimal policy threshold $\theta^*$ acts as the routing boundary for Cloud engine escalation.

---

## 5. Layer 8: Canary Deployment Controller

### 5.1 Sequential Probability Ratio Test (SPRT)
We monitor the False Alarm Rate (FAR) during canary rollouts. We test the hypothesis:
*   $H_0: p = p_0$ (Acceptable FAR = $0.01$)
*   $H_1: p = p_1$ (Unacceptable FAR = $0.05$)

The cumulative log-likelihood ratio $S_n$ for $n$ evaluations is updated as:

$$S_n = k \ln \frac{p_1}{p_0} + (n - k) \ln \frac{1 - p_1}{1 - p_0}$$

where $k$ is the number of false alarms observed.
*   **Trigger Rollback:** If $S_n \ge B$, where $B = \ln \left(\frac{1 - \beta}{\alpha}\right)$
*   **Verify Success:** If $S_n \le A$, where $A = \ln \left(\frac{\beta}{1 - \alpha}\right)$
