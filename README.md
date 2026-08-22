# PhysEdge-Cloud

[![CI](https://github.com/Anshul-5/Physics-Edge-Cloud-/actions/workflows/ci.yml/badge.svg)](https://github.com/Anshul-5/Physics-Edge-Cloud-/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Anshul-5/Physics-Edge-Cloud-/actions/workflows/codeql.yml/badge.svg)](https://github.com/Anshul-5/Physics-Edge-Cloud-/actions/workflows/codeql.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.1+-orange.svg)](https://docs.espressif.com/projects/esp-idf/en/v5.1/esp32s3/)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/Anshul-5/Physics-Edge-Cloud-/badge)](https://securityscorecards.dev/viewer/?uri=github.com/Anshul-5/Physics-Edge-Cloud-)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/github/Anshul-5/Physics-Edge-Cloud-/badge)](https://www.bestpractices.dev/projects/github/Anshul-5/Physics-Edge-Cloud-)

> An Uncertainty-Calibrated, Physics-Informed Edge-to-Cloud Cascade for Real-Time Video Anomaly Detection

---

## Overview

**PhysEdge-Cloud** is a 9-layer video anomaly detection framework that optimizes the trade-off between real-time detection latency, cloud bandwidth costs, and strict privacy regulations. By leveraging lightweight physics-based algorithms (metric kinematics, directional motion entropy) on sub-watt microcontroller edge devices (ESP32-S3), the system filters **80–90% of normal scene activity** before it ever reaches the cloud.

Suspicious events are escalated through a three-tier cascade:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Tier 1: ESP32-S3 Edge Gate                                         │
│  Camera → Downscaler → Optical Flow → Homography → Kinematics      │
│  Discards 80-90% of normal frames · Zero-PII egress boundary       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ Skeletal stream + kinematics
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Tier 2: Regional Edge (NVIDIA Jetson)                              │
│  Calibrated Recursive Log-Odds Fusion (CROP)                       │
│  Validates semantic posture/poses · Abstains on low confidence     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ Escalated events
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Tier 3: Central Cloud (GPU Clusters)                               │
│  Graph Spectral Instability · Memory-AE · Conformal Prediction     │
│  Deep contextual adjudication · Forensic audit trail               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Camera Capture Driver** | QVGA (320x240) grayscale initialization with hardcoded pin mapping |
| **Fixed-Point Downscaler** | Q8.8 bilinear interpolation 320x240→160x120, zero float on MCU |
| **Block SAD Optical Flow** | 10x7 grid, 16x16 blocks, SIMD-optimized inner loop |
| **Metric Kinematics Gate** | Homography-normalized pixel→ground-plane mapping for velocity, acceleration, and jerk in SI units |
| **Privacy-by-Architecture** | Zero-PII egress contract—video never leaves the edge; only anonymized skeletons and kinematics vectors are transmitted |
| **Calibrated Risk Opinion Pool (CROP)** | Precision-weighted log-opinion fusion of multi-source anomaly indicators |
| **Closed-Loop Feedback** | Cloud-adjudicated false triggers send negative constraints back to edge devices for auto-tuning |
| **Forensic Auditing** | Merkle-log chained video clips bound to model versions and kinematic provenance |

---

## Repository Structure

```
PhysEdge-Cloud/
├── edge/                            # ESP32-S3 firmware (L1 Edge Gate)
│   ├── components/
│   │   ├── camera_capture/          # QVGA grayscale camera driver
│   │   ├── downscaler/              # Q8.8 fixed-point bilinear downscaler
│   │   └── optical_flow/            # Block SAD optical flow with SIMD
│   ├── main/                        # Application entry point
│   ├── test/                        # Host-side unit tests
│   └── sdkconfig.defaults           # ESP32-S3 configuration
├── docs/                            # Technical specifications
│   ├── system_architecture.md       # 9-layer cascade design
│   ├── api_specification.md         # gRPC, JSON schemas, update payloads
│   ├── security_and_privacy.md      # Threat models, differential privacy
│   ├── production_runbook.md        # Canary rollouts, SPRT rollbacks
│   ├── development_roadmap.md       # Milestones, verification, KPIs
│   └── mathematical_documentation.md # Formal equations and proofs
├── .github/
│   ├── workflows/                   # 23 CI/CD workflows
│   │   ├── ci.yml                   # Main pipeline (9 jobs)
│   │   ├── codeql.yml               # C/C++ security analysis
│   │   ├── gitleaks.yml             # Secret detection
│   │   ├── scorecard.yml            # OpenSSF Scorecard
│   │   ├── sbom.yml                 # SBOM generation (SPDX + CycloneDX)
│   │   ├── benchmarks.yml           # Performance tracking
│   │   ├── benchmark-history.yml    # Historical benchmark data
│   │   ├── size-history.yml         # Source code size tracking
│   │   ├── changelog.yml            # Auto-update CHANGELOG.md
│   │   ├── changelog-validate.yml   # PR changelog check
│   │   ├── commitlint.yml           # Conventional commit validation
│   │   ├── semver-check.yml         # Version bump suggestions
│   │   ├── coverage.yml             # Codecov reporting
│   │   ├── license-check.yml        # License compliance
│   │   ├── pr-title.yml             # Semantic PR titles
│   │   ├── pr-size.yml              # PR size labeling
│   │   ├── labeler.yml              # Auto-label by file path
│   │   ├── release.yml              # GitHub Release on tag push
│   │   ├── pages.yml                # GitHub Pages docs
│   │   ├── nightly.yml              # Nightly builds
│   │   ├── stale.yml                # Stale issue/PR bot
│   │   └── auto-close.yml           # Auto-close on fix keyword
│   ├── dependabot.yml               # Dependency updates
│   ├── CODEOWNERS                   # @Anshul-5, @purvanshjoshi
│   ├── labeler.yml                  # Label rules
│   └── ISSUE_TEMPLATE/              # Bug/feature templates
├── CHANGELOG.md                     # Auto-updated release history
├── CODE_OF_CONDUCT.md               # Contributor Covenant v2.0
├── LICENSE                          # Apache 2.0
└── SECURITY.md                      # Vulnerability reporting
```

---

## Getting Started

### Prerequisites

- **Hardware:** ESP32-S3 development board with camera interface (e.g., ESP-S3-CAM)
- **Toolchain:** ESP-IDF v5.1+ ([installation guide](https://docs.espressif.com/projects/esp-idf/en/v5.1/esp32s3/get-started/index.html))
- **Optional:** NVIDIA Jetson Nano (Tier 2), Docker (for cloud services)

### Build & Flash

```bash
# Clone the repository
git clone https://github.com/Anshul-5/Physics-Edge-Cloud-.git
cd Physics-Edge-Cloud-/edge

# Set target and build
idf.py set-target esp32s3
idf.py build

# Flash to device
idf.py -p /dev/ttyUSB0 flash monitor
```

### Run Tests (Host-side)

```bash
# Downscaler tests
gcc -I components/downscaler/include \
    components/downscaler/downscaler.c \
    test/test_downscaler.c -o test_downscaler -lm
./test_downscaler

# Optical flow tests
gcc -I components/optical_flow/include \
    components/optical_flow/optical_flow.c \
    test/test_optical_flow.c -o test_optical_flow -lm
./test_optical_flow
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [System Architecture](docs/system_architecture.md) | 9-layer cascade design, hardware profiles, graph spectral instability |
| [API Specification](docs/api_specification.md) | gRPC payloads, REST schemas, MQTT topics |
| [Security & Privacy](docs/security_and_privacy.md) | Threat models, differential privacy, forensic hashing |
| [Production Runbook](docs/production_runbook.md) | Canary deployments, SPRT rollbacks, drift monitoring |
| [Development Roadmap](docs/development_roadmap.md) | 12-month schedule, test rigs, target KPIs |
| [Mathematical Documentation](docs/mathematical_documentation.md) | Formal equations, proofs, parameter derivations |

---

## CI/CD Pipeline

Our CI/CD infrastructure includes **23 automated workflows**:

### Core CI (9 jobs)

| Job | Purpose |
|-----|---------|
| Lint & Format | C formatting (clang-format) + static analysis (cppcheck) |
| Build ESP32-S3 | Full ESP-IDF firmware build |
| Unit Tests | Host-side GCC compilation + gcov/lcov coverage |
| Stack Usage Analysis | VLA detection + large allocation warnings |
| Dependency Audit | Component version tracking + CVE patterns |
| Kconfig Validation | sdkconfig.defaults analysis |
| Memory Analysis | PSRAM vs SRAM usage + leak patterns |
| Binary Size Tracking | Firmware size breakdown + optimization tips |
| Docs Validation | Markdown existence + link checks |

### Security

| Workflow | Purpose |
|----------|---------|
| CodeQL | C/C++ static analysis for vulnerabilities |
| GitLeaks | Secret detection on every push/PR |
| OpenSSF Scorecard | Security best practices assessment |
| SBOM Generation | SPDX + CycloneDX software bills of materials |
| License Compliance | Apache 2.0 header verification |

### Automation

| Workflow | Purpose |
|----------|---------|
| Changelog | Auto-updates CHANGELOG.md after CI passes |
| Changelog Validate | Ensures PRs update CHANGELOG.md |
| Commit Lint | Conventional commit message validation |
| Semantic PR Title | PR title format validation |
| PR Size | Auto-labels PRs by diff size |
| Auto Label | Labels PRs by file path changed |
| Release | Creates GitHub Release with firmware binaries on tag push |
| Nightly | Scheduled builds at 2:00 UTC daily |

### Quality Tracking

| Workflow | Purpose |
|----------|---------|
| Benchmarks | Optical flow performance with pass/fail comments |
| Benchmark History | Tracks performance over time |
| Size History | Tracks source code size over time |
| Code Coverage | Codecov integration |

### Community

| Workflow | Purpose |
|----------|---------|
| Stale | Auto-closes inactive issues/PRs |
| Auto Close | Closes issues when fix keyword detected |
| Dependabot | Automated dependency updates |

---

## Contributing

We welcome contributions! Please see our [Code of Conduct](CODE_OF_CONDUCT.md) and [Security Policy](SECURITY.md) before contributing.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Espressif Systems](https://www.espressif.com/) for ESP-IDF and ESP32-S3
- [NVIDIA](https://www.nvidia.com/) for Jetson platform
- Contributors and maintainers of the open-source dependencies
