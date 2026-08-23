# Security, Privacy, and Cryptographic Provenance Specification: PhysEdge-Cloud

**Document Reference:** PEC-SEC-SPEC-V2.9  
**Classification:** Security Architecture, Cryptographic Specifications & Privacy Bounds  
**Compliance Standards:** OpenSSF Best Practices, NIST SP 800-53, ISO/IEC 27001, GDPR Article 25 (Privacy by Design), GDPR Article 32 (Security of Processing)  

---

## 1. Threat Model & STRIDE Analysis

The PhysEdge-Cloud distributed infrastructure operates across untrusted network perimeters, physical outdoor camera mountings, and shared cloud infrastructure. The STRIDE threat taxonomy governs the security engineering across all 9 layers.

| Threat Category (STRIDE) | Attack Vector Description | Vulnerable System Component | Concrete Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Spoofing Identity** | Adversary impersonates an edge camera or cloud control plane | MQTT / gRPC telemetry interfaces | Mutual TLS (mTLS) with X.509 device certificates; ECDSA-signed OTA packets. |
| **Tampering with Data** | Modification of historical video logs or telemetry to conceal crimes | Tier 6 Cloud Storage (Event Blocks) | Length-delimited Merkle hash-chaining binding video hashes, kinematics, and model digests. |
| **Repudiation** | Operator or system denies initiating false alerts or firmware rollouts | Tier 8 Canary / Tier 9 OTA Controller | Cryptographic event logs signed with unalterable timestamped monotonic counter metadata. |
| **Information Disclosure** | Interception of streaming video leading to facial / PII leakage | Tier 1 to Tier 2 Network Egress | Strict Zero-PII egress contract; raw pixels are destroyed in SRAM; Laplace DP coordinate coarsening. |
| **Denial of Service (DoS)** | Volumetric alert flooding to overwhelm cloud GPU clusters | Tier 2 Regional Node Queue | Dynamic backpressure queue shedding; priority dropping of low-jerk/stationary frames. |
| **Elevation of Privilege** | Replay of malicious firmware revisions containing backdoors | Tier 1 ESP32-S3 Flash Memory | Hardware-fused monotonic eFuse anti-rollback counters; atomic dual-partition verification. |

---

## 2. Zero-PII Egress Architecture & Data Flow Boundaries

```
+-----------------------------------------------------------------------------+
|  PRIVACY BOUNDARY 1: SENSOR RAW PIXEL ISOLATION (Tier 1 Edge)               |
|  - Camera DVP Sensor -> ESP32-S3 SRAM Internal Line Buffer                  |
|  - Raw frame is discarded immediately after fixed-point optical flow        |
|  - Zero raw pixels are written to non-volatile flash or network buffers     |
+--------------------------------------|--------------------------------------+
                                       | Anonymized Skeletal & Kinematic Vectors
                                       v
+-----------------------------------------------------------------------------+
|  PRIVACY BOUNDARY 2: REGIONAL SKELETAL FILTERING (Tier 2 Node)              |
|  - 33 Pose Keypoints without texture, skin color, facial or iris markers    |
|  - Calibrated CROP Opinion Pooling executes locally                         |
+--------------------------------------|--------------------------------------+
                                       | Obfuscated Coordinates & Risk Scalars
                                       v
+-----------------------------------------------------------------------------+
|  PRIVACY BOUNDARY 3: DIFFERENTIAL PRIVACY COORDINATE OBFUSCATION (Tier 3)   |
|  - Grid Coarsening: 64x64 Discrete Quantization Grid                        |
|  - Laplace Noise Injection: Lap(0, Δf / ε) using Cryptographic CSPRNG       |
+-----------------------------------------------------------------------------+
```

---

## 3. Mathematical Formulations for Differential Privacy

### 3.1 Laplace Mechanism on Spatial Trajectories
Let $\mathbf{X} \in [0, 1]^2$ be normalized ground-plane spatial coordinates. The coordinate coarsening operator $\mathcal{Q}_G$ quantizes coordinates onto a discrete lattice of size $G \times G$ ($G = 64$):

$$\mathcal{Q}_G(\mathbf{X}) = \frac{1}{G - 1} \text{round}\Big( (G - 1) \cdot \mathbf{X} \Big)$$

The $L_1$-sensitivity $\Delta f$ of the grid query across adjacent spatial states is bounded by:
$$\Delta f = \max_{\mathbf{X} \sim \mathbf{X}'} \|\mathcal{Q}_G(\mathbf{X}) - \mathcal{Q}_G(\mathbf{X}')\|_1 = \frac{\sqrt{2}}{G - 1}$$

The randomized mechanism $\mathcal{M}(\mathbf{X})$ adds zero-mean Laplace noise scaled by privacy budget $\varepsilon$:

$$\mathcal{M}(\mathbf{X}) = \text{clamp}\left( \mathcal{Q}_G(\mathbf{X}) + \boldsymbol{\eta}, 0.0, 1.0 \right), \quad \boldsymbol{\eta} = [\eta_1, \eta_2]^T, \quad \eta_i \sim \text{Lap}\left(0, \frac{\Delta f}{\varepsilon}\right)$$

### 3.2 Cryptographic Random Number Generation (CSPRNG)
To eliminate pseudo-random cycle predictability and fulfill OpenSSF standards, Laplace variates are sampled using inverse transform sampling on a Cryptographically Secure Pseudo-Random Number Generator (`secrets.SystemRandom` / `/dev/urandom`):

$$u \sim \mathcal{U}(0, 1), \quad u \neq 0.5$$
$$\eta = -\frac{\Delta f}{\varepsilon} \cdot \text{sgn}(u - 0.5) \cdot \ln(1 - 2|u - 0.5|)$$

### 3.3 Sequential Dimension Composition Theorem
For a $D$-dimensional trajectory queried sequentially $T$ times, the aggregate privacy leakage $\varepsilon_{\text{total}}$ satisfies the sequential composition property:

$$\varepsilon_{\text{total}} = \sum_{t=1}^T \sum_{d=1}^D \varepsilon_{t, d}$$

---

## 4. Length-Delimited Forensic Merkle Hash-Chain

To provide court-admissible forensic provenance for security incidents, Tier 6 constructs a cryptographically chained, tamper-evident hash ledger.

### 4.1 Canonical Length-Delimited Pre-Image Encoding
Standard string concatenation (e.g., $A \parallel B$) is vulnerable to boundary-shifting preimage collisions where $\text{hash}("ab" \parallel "c") = \text{hash}("a" \parallel "bc")$. PhysEdge-Cloud eliminates this vulnerability by enforcing a length-prefixed domain-separated canonical encoding:

$$\text{Encode}(S) = \text{uint32\_be}(\text{len}(S)) \parallel S$$

$$B_i = \text{SHA-256}\Big( \text{Encode}(B_{i-1}) \parallel \text{Encode}(C_i) \parallel \text{Encode}(K_i) \parallel \text{Encode}(M_i) \Big)$$

where:
- $B_{i-1}$: SHA-256 hexadecimal digest of the preceding block in the chain ($B_0 = 0^{64}$).
- $C_i$: SHA-256 digest of the encrypted video snippet.
- $K_i$: Deterministically serialized JSON metadata containing metric kinematics and spectral divergence values.
- $M_i$: SHA-256 digest of the neural network model weights executing at the time of adjudication.

### 4.2 Tamper Detection Algorithm
The hash chain is verified in $O(N)$ time by recomputing each block's cryptographic hash from its raw components and verifying unbroken linkage to $B_{i-1}$. Any historical alteration to video clips, kinematics, or model hashes invalidates all subsequent child blocks.

---

## 5. Secure Over-The-Air (OTA) & Anti-Rollback Architecture

The Tier 9 OTA pipeline deploys firmware binaries and parameter constraints while protecting edge hardware from downgrade and tampering attacks:

1. **Digital Signature Verification:** All firmware binaries are signed with an offline NIST P-256 ECDSA private key. The ESP32-S3 bootloader verifies the SHA-256 digest against public keys burned into hardware eFuses.
2. **Hardware Monotonic Anti-Rollback:** Hardware eFuse security registers track the minimum authorized firmware version. Any update containing a version counter $V_{\text{target}} < V_{\text{hardware}}$ is rejected at the bootloader level.
3. **Atomic A/B Partitioning:** Flashing occurs into the passive `ota_1` partition while `ota_0` executes. Upon successful reboot and operational self-test verification, the active boot flag is toggled.
