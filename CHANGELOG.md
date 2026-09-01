# Changelog

All notable changes to PhysEdge-Cloud will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]
### Security
- Pinned all Python dependencies to fixed, audited versions and generated lockfiles resolving 23 OSV advisories (#152, #153)
- Hardened forensic Merkle log hash chain with length-delimited domain-separated encoding to prevent boundary-shifting collisions (#118)
- Hardened CROP risk pooling and Conformal Prediction against NaN/non-finite alert suppression and variance poisoning (#126)
- Added strict UUID validation to prevent MQTT topic injection and namespace escapes on constraint downlinks (#130)
- Added parameter allowlist schema validation for edge negative constraints (#134)
- Implemented bounded history tracking and memory eviction in ConstraintRateLimiter and MQTT broadcaster (#135)
- Enforced strict 64-character hexadecimal digest validation in EventBlock (#139)
- Added explicit opt-in requirement for PostgreSQLVectorStore in-memory fallback mode (#129)
- Vectorized Laplace noise sampling and implemented sequential dimension budget composition in CoordinateObfuscator (#131, #147)
- Hardened L2 Regional Node gRPC ingestion with mTLS support, bounded queue, frame limits, and YOLO checksums (#162)
- Hardened all 22 GitHub Actions workflows by pinning all action dependencies to immutable 40-character commit SHAs (#122)
- Added dual-language SAST CodeQL analysis for C++ and Python with top-level read-all permissions (#122)
- Added OpenSSF Best Practices Program badge to README (#122)

### Fixed
- Enabled strict failure exit codes on cppcheck and clang-format static analysis in CI (#158)
- Fixed action commit SHA in stale workflow for scheduled stale maintenance (#151)
- Fixed NaN suppression in FusionEngine Bayesian log-odds updating and added temperature validation
- Fixed worker thread exception resilience in PriorityStreamQueue process loop
- Fixed off-by-one threshold and NaN fail-closed handling in BackpressureManager
- Fixed GitHub Pages deployment workflow with verified immutable action commit SHAs (#151)

### Performance
- Optimized AdaptiveConformalPredictor.get_quantile with O(N) selection algorithm via np.partition (#146)

### Added
- Added comprehensive mathematical formulations and matrix equations (Homography $\mathbf{H}_{3\times 3}$, Spatio-Temporal Adjacency $\mathbf{A}_{N\times N}$, Normalized Graph Laplacian $\mathbf{L}_{\text{norm}}$, CROP Log-Opinion Pool, Lagrangian Dual Optimization, Length-Delimited Merkle Hash Chain, and Differential Privacy Laplace Mechanism) to [`README.md`](file:///D:/Physics-Cloud/README.md) for research journal reference
- Added empirical evaluation and real-world simulation benchmark results (1,000 live streaming frames, 82.30% edge filtering, 98.00% classification accuracy, 0.33 ms end-to-end latency, 14,783 FPS throughput) to [`README.md`](file:///D:/Physics-Cloud/README.md)
- Added declarative branch protection ruleset configuration for main branch (#151)
- Added OpenSSF Best Practices self-assessment documentation and badge compliance mapping (#156)
- Added libFuzzer fuzzing harnesses for secure OTA, downscaler, optical flow, and uplink buffer with ClusterFuzzLite integration (#155)
- Added @archittmittal as repository code owner in .github/CODEOWNERS and CONTRIBUTING.md
- Added CONTRIBUTING.md with OpenSSF peer review guidelines and Conventional Commit specifications (#154)
- Updated .github/CODEOWNERS covering regional node, cloud engine, and firmware OTA paths (#154)
- Hardened L1 firmware against integer overflows, signed SIMD shift, NaN corruption, and memory safety vulnerabilities (#160)
- Implemented Time-to-Collision (TTC) calculations with division-by-zero safeguards for L1 Edge (#112)
- Implemented Spatiotemporal Pedestrian Interaction Graph and spectral instability detector for L3 Engine (#113)
- Added End-to-End Evaluation & Benchmark Harness, kinematics reprojection tests, and production configuration (#111)
- Implemented flow-confidence-weighted non-dimensionalized Motion Energy (E) calculations on the L1 edge and integrated with L2 telemetry gRPC streaming (#115)
- Implemented Closed-Loop Negative Constraints Pipeline, Edge Parameter Streamer, and L1 Jerk Baseline adjustment parser for L7 Retraining (#27)
- Implemented Operations Alert Dispatcher, Prometheus Fleet Metrics, and Grafana Dashboard for L8/L9 Operations (#30)
- Implemented ESP32-S3 OTA Secure Boot Anti-Rollback validation and signing utility for L9 Delivery (#25)
- Implemented Champion/Challenger Model Promotion Pipeline with bootstrap significance gating and Model Registry for L7 Retraining (#26)
- Implemented Progressive Canary Rollout Scheduler with hashing-based fleet partitioning for L8 Delivery (#28)
- Implemented SPRT False Alarm Rate Rollback Controller for automated canary safety monitoring for L8 Delivery (#29)
- Implemented Secure Boot ECDSA signature verification and anti-rollback checks for L9 OTA updates (#25)
- Implemented Grid Coordinate Coarsening and Laplace Differential Privacy for security/privacy obfuscation (#24)
- Implemented PostgreSQL pgvector schema setup, HNSW indexes, and similarity search client for L6 Storage (#22)
- Implemented Forensic Cryptographic Merkle Log Hash Chain with block serialization and consistency validation checks for L6 Storage (#23)
- Implemented Feature KL-Divergence Input Drift Tracker with rolling histogram compilation and Prometheus metrics for L5 Registry (#21)
- Implemented Cost-Risk Lagrangian Compute Router and connection telemetry outage fallback for L4 Orchestrator (#20)
- Implemented Precision-Weighted Risk Opinion Pool (CROP) with variance tracking for L3 Engine (#18)
- Implemented Time-Adaptive Conformal Prediction Coverage and alert boundaries for L3 Engine (#19)
- Added Graph Laplacian Fiedler eigenvalue and spectral instability calculations to SpatialGraphEngine (#3)
- Implemented Spatio-Temporal Graph Architecture for Cloud Engine (#16)
- Implemented PyTorch Memory-Augmented Autoencoder (Mem-AE) for open-set anomaly detection (#17)
- Implemented Multi-Camera Backpressure Manager and Abstain Policy for L2 Node (#15)
- Implemented MediaPipe BlazePose Landmark Extraction for L2 skeletal posture analysis (#13)
- Implemented Python asyncio gRPC telemetry receiver for L2 Regional Node with Protobuf compilation (#12)
- Integrated Ultralytics YOLOv8n object detection into the L2 processing loop (#12)
- Added Bayesian Recursive Log-Odds Fusion engine with Temperature Calibration to L2 node (#14)
- Implemented Python asyncio gRPC telemetry receiver for L2 Regional Node with Priority Queueing (#11)
- Added ESP32-S3 PSRAM Circular Buffer data store and Protobuf Uplink schema (#10)
- Implemented EWMA Jerk Baseline and Hysteresis Gating for smart motion triggering (#9)


### Documentation
- docs: update changelog [skip ci] ([4d95229](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/4d95229064589d87b25595c1bb811fc480333266)) @github-actions[bot]
- docs: update changelog [skip ci] ([14fec33](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/14fec336d77dd6ee3cf2c380e823da854435ee7e)) @github-actions[bot]
- docs: add international journal manuscript, research evaluation report, and formal ICD specifications ([883d17e](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/883d17e4fa9ad913a073fd1533c7c47e02f95ab6)) @Purvansh Joshi
- docs: add mathematical matrix formulations and real-world benchmark metrics to README ([62588c0](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/62588c06c9f59cbbb198c29b59fe0805854606b5)) @Purvansh Joshi
- docs: update changelog [skip ci] ([d56d2d6](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/d56d2d6481cb6e052eb4c8c6ab72b51198fabb4b)) @github-actions[bot]
- docs: update changelog [skip ci] ([cc0f84a](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/cc0f84a2db8748895296b7bdf273b53ac238a101)) @github-actions[bot]
- docs: update changelog [skip ci] ([d168fa6](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/d168fa640ad991d99efccf6b7e603003d033938d)) @github-actions[bot]
- docs: update changelog [skip ci] ([725f47f](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/725f47f03acb23d4c4ef56a6f9c98feb9452d2d0)) @github-actions[bot]
- docs: update changelog [skip ci] ([86ec0ea](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/86ec0ea92f5af149bb3f0f1736a748b79c12f198)) @github-actions[bot]
- docs: update changelog [skip ci] ([31bdefd](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/31bdefd0a2e1f83107bd56287d4ce2def233cd7f)) @github-actions[bot]
- docs: update changelog [skip ci] ([12e969b](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/12e969b9209e5b748a991d7befa78f11518db43e)) @github-actions[bot]
- docs: update changelog [skip ci] ([108db1a](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/108db1a9de4193c95fbea2c377809306e6714269)) @github-actions[bot]
- docs: update changelog [skip ci] ([c9afade](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/c9afade6080622000a72fe58e3a48a737dc9f67b)) @github-actions[bot]
- docs: update changelog [skip ci] ([1e23d90](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/1e23d90ebb54f240424b6836d9ff60f897c0a0c2)) @github-actions[bot]
- docs: update changelog [skip ci] ([9d82d73](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/9d82d73d2b635379cc3bc492c203038d761abb7d)) @github-actions[bot]
- docs: update changelog [skip ci] ([dfc9684](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/dfc9684814dcd97602fe4008a15ba48d03ad3e80)) @github-actions[bot]

### Changed
- docs(openssf): document branch protection ruleset and Best Practices (#169) ([08018dc](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/08018dc4abf6a139890b1137bf134668c1cb1570)) @Purvansh Joshi
- feat(openssf): add fuzzing harnesses and lock Python dependencies (#168)

* feat(openssf): add fuzzing harnesses and lock Python dependencies

* fix(ci): correct ClusterFuzzLite action commit SHA

* fix(fuzz): fix Dockerfile paths and CMakeLists references for ClusterFuzzLite

* fix(fuzz): fix API calls and signatures in fuzz harnesses ([634d5c9](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/634d5c9c518a038a00d926ee360fd7b96ab792ed)) @Purvansh Joshi
- chore(governance): add archittmittal to CODEOWNERS and maintainers (#167)

* chore(governance): add archittmittal to CODEOWNERS and maintainers

* docs(changelog): note archittmittal codeowner addition ([4980af7](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/4980af755d4ba7766d1900166c28967670bcc6c7)) @Purvansh Joshi
- docs(governance): add CONTRIBUTING guidelines and update CODEOWNERS (#166) ([8fe2c92](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/8fe2c9260e168af39a708b5fa0d4eaf2018723c6)) @Purvansh Joshi
- perf(cloud): optimize quantile selection and enforce CI static analysis (#165)

* perf(cloud): optimize quantile selection and enforce CI static analysis

* style(ci): add .clang-format config and scope C/C++ format check

* fix(ci): adjust clang-format dry-run and enforce strict cppcheck error codes

* fix(ci): suppress unusedStructMember and constParameter in cppcheck ([286cc8f](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/286cc8febf2854a48f3003a477b2d09bb7611e4a)) @Purvansh Joshi
- feat(cloud): harden cloud engine security, storage and feedback (#164) ([282b754](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/282b75416952737d2e08d3b4ac04c879c408799c)) @Purvansh Joshi
- feat(regional): harden L2 telemetry ingestion, fusion & backpressure (#162)

- Support mTLS on gRPC server & warn on insecure port (Issue #119)
- Prevent NaN alert suppression and stabilize fusion math (Issue #125)
- Protect worker thread from unhandled exceptions (Issue #127)
- Bound PriorityQueue capacity and prevent memory DoS (Issue #128)
- Support local YOLO weights and digest verification (Issue #136)
- Cap JPEG size and bounds check decoded dimensions (Issue #137)
- Validate FusionEngine temperature parameter (Issue #142)
- Fix backpressure off-by-one and NaN fail-closed handling (Issue #148) ([ff81763](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/ff81763ff7cfa7acc57b73fbe697bcc201ab78d5)) @Archit Mittal
- docs(readme): style OpenSSF Best Practices badge with Shields.io (#163) ([26d6196](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/26d6196e45a659eca43725fec127cc6a4c3a70d6)) @Purvansh Joshi
- feat(edge): harden L1 firmware security and correctness (#160)

- Fix 32-bit integer overflow in secure_ota (Issue #117)
- Fix SIMD SAD unsigned shift & unaligned loads (Issue #120, #145)
- Add NaN guards in jerk_baseline constraint clamp (Issue #121)
- Fix heap over-read and malloc failure in uplink buffer (Issue #123, #124)
- Fix UB shifts, denom threshold, and grid bounds (Issue #132, #133)
- Add stride and dimensions bounds in downscaler (Issue #140)
- Add structural validation to ota_security header (Issue #143)
- Update .gitignore to ignore test binaries and coverage (Issue #159)
- Expand host unit tests to 41 passing tests across 7 components ([1e2de29](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/1e2de29e52b597fd357eb37992535a96ac20d7db)) @Archit Mittal
- fix(ci): update pages workflow action SHAs for jekyll-build-pages (#161) ([c9c4a81](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/c9c4a81ec5fd27cf089bf1c155426934ea538f14)) @Purvansh Joshi
- ci(security): pin action SHAs, dual-language SAST & OpenSSF badges (#150) ([55a33f1](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/55a33f199286f77b62fcf2986667e03bc270c3b7)) @Purvansh Joshi
- Merge pull request #116 from Anshul-5/feat/roadmap-ttc-interaction-benchmark

feat: implement TTC safeguards, pedestrian graph & benchmark harness ([ded548b](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/ded548b208db272ba0682a1e0ab0a0edf5ab8b69)) @Purvansh Joshi
- Merge pull request #115 from Anshul-5/feat/issue-110-motion-energy

feat(edge): implement flow-confidence-weighted motion energy calculation ([e00297a](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/e00297af1fff431475e78e164dc781acbd414b52)) @Purvansh Joshi
- Merge pull request #109 from Anshul-5/feat/l7-closed-loop-feedback

feat: implement edge baseline closed-loop negative constraints ([b974848](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/b974848f8fb26b6f54152b856d8ec1f8f47c4c24)) @Purvansh Joshi
- fix(test): probe OpenSSL headers before compiling Secure OTA in reproduce.py ([c4aa0ea](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/c4aa0ead2ee64a92ab6a0c2b40ba312320678d3a)) @Purvansh Joshi
- Merge pull request #107 from Anshul-5/feat/phase5-closed-loop-ops-ota

feat(phase5): add closed-loop telemetry, ops dashboard & OTA security ([d2a5c49](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/d2a5c49e13ca4d86fdc07c67349855cd98f47012)) @Purvansh Joshi
- Merge pull request #105 from Anshul-5/feat/phase5-retraining-canary-sprt

feat(phase5): add Champion/Challenger pipeline & SPRT canary ([0f567d1](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/0f567d1c7c59430aa643d548b37d386eedfcab2c)) @Purvansh Joshi
- Merge pull request #104 from archittmittal/feat/l7-privacy-dp-laplace

feat: implement coordinate coarsening & Laplace Differential Privacy ([a9cad93](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/a9cad9375116c5a5ac0946230f4eb07ef6401fe5)) @Purvansh Joshi
- Merge pull request #102 from archittmittal/feat/l4-orchestrator-l5-drift-tracker

feat: implement L4 Compute Router & L5 Input Drift Tracker ([78d4b2c](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/78d4b2c88f5fd4407283d2e66cf38f7011fed51d)) @Purvansh Joshi
- Merge pull request #100 from Anshul-5/feat/openssf-security-hardening

chore(security): apply comprehensive OpenSSF Scorecard hardening ([f5e7d9d](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/f5e7d9d0af61915195e7c5c7106b4f6864e8f5ef)) @Purvansh Joshi
- Merge pull request #99 from Anshul-5/ci/configure-scorecard-action

ci: configure OpenSSF Scorecard permissions and OIDC publishing ([e9b3d8d](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/e9b3d8dbdb5f9e8d634c98f9b52811703de149d6)) @Purvansh Joshi
- Merge pull request #98 from Anshul-5/feat/phase3-cluster-a

ci: fix benchmark PR commenting permissions, branch triggers, and wor… ([934c6a7](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/934c6a718ffa6274fd1a62bb34c5ed3f1b65e281)) @Purvansh Joshi
- Merge pull request #97 from archittmittal/feat/l3-engine-crop-conformal-spectral

feat: implement CROP, Conformal Prediction & Spectral Instability ([b36bff2](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/b36bff28efb62a4b48bfd13222dd9987a93e6de3)) @Purvansh Joshi
- Merge pull request #96 from Anshul-5/feat/phase3-cluster-a

feat: L3 Graph Structural Adjacency & Mem-AE ([3874b8a](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/3874b8a103982c9fd8b106460b5592986ec925f4)) @Purvansh Joshi
- Merge pull request #93 from Anshul-5/feat/phase2-yolo-fusion

feat: Phase 2 YOLOv8 Integration & Calibrated Log-Odds Fusion ([c91f4eb](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/c91f4eb95600a4681f436ea0f0303636393803b0)) @Purvansh Joshi
- Merge pull request #91 from Anshul-5/feat/issue-11-l2-telemetry

feat(l2-node): L2 Node Telemetry Receiver & Frame Stream Handler ([780a524](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/780a52450477af137c1b8075dc9a9d67d96311af)) @Purvansh Joshi
- feat(edge): C to C++ Migration for L1 Gate Firmware (#88)

* feat(edge): convert L1 firmware from C to C++ for type safety and object-oriented abstractions

* fix(ci): update workflows to compile .cpp files with g++

* fix(test): remove c-style compound literal address assignment for strict c++ compliance

* ci: fix debconf interactive hang during apt-get install

* ci: remove buggy lcov mismatch flag causing perl infinite loop ([0bc1315](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/0bc1315dd2aa9af658c9510adfa53ed44766cd72)) @Purvansh Joshi
- feat(edge): Homography projection and ground-plane kinematics (#8) (#85)

* feat(edge): add homography projection and ground-plane kinematics

Implements Issue #8: maps pixel-space optical flow displacements to metric
ground-plane coordinates via a Q16.16 fixed-point planar homography, then
computes velocity/acceleration/jerk with backward differences and a 3-tap
EWMA filter for noise suppression.

- components/homography: opaque-context API (init/project/kinematics_update/deinit)
- Q16.16 fixed-point arithmetic, no float on MCU
- Denominator guard rejects degenerate (near-horizon) projections
- Host-side unit tests (10) covering conversion, projection, guard,
  constant velocity, acceleration, EWMA smoothing, and null inputs
- Wire test into CI Unit Tests job with gcov coverage

* ci: fix semver-check shell injection and document homography in changelog

Pass PR title/body via environment variables instead of inlining them into
the shell script, which caused command-substitution failures whenever a PR
body contained backticks or dollar signs (e.g. code examples).

Also add homography projection feature to the CHANGELOG. ([43263b7](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/43263b7e55164d9478adb813aff3b70fbb862798)) @Purvansh Joshi
- Merge pull request #84 from Anshul-5/dependabot/github_actions/github/codeql-action-4.37.4

ci: bump github/codeql-action from 4 to 4.37.4 ([c75d977](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/c75d977baf6fc3d56a6f7ea2052643383c52ddfd)) @Purvansh Joshi
- Merge pull request #81 from Anshul-5/dependabot/github_actions/github/codeql-action-4

ci: bump github/codeql-action from 3 to 4 ([30c18b1](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/30c18b196fd63ddb5e58933238ec885f60daaa7c)) @Purvansh Joshi
- Merge pull request #78 from Anshul-5/dependabot/github_actions/actions/upload-pages-artifact-5

ci: bump actions/upload-pages-artifact from 3 to 5 ([2e19dd9](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/2e19dd922a68c7396596e60c6612656504ea077a)) @Purvansh Joshi
- fix(ci): always comment benchmark results (pass or fail) ([4102842](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/41028425d5800467502be5dba193ccac0cb76f4d)) @Purvansh Joshi
- fix(ci): update labeler.yml to v5 format ([4a8ac26](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/4a8ac26d13ff8486dfec78b21fd0034fc748e9f5)) @Purvansh Joshi
- Merge pull request #67 from Anshul-5/dependabot/github_actions/amannn/action-semantic-pull-request-6

ci: bump amannn/action-semantic-pull-request from 5 to 6 ([463e58b](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/463e58b67896ad03f52bccc3ce8691c20534ba5b)) @Purvansh Joshi
- fix(ci): fix labeler YAML syntax and benchmarks permissions ([e434636](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/e43463657d671edf6a82efeb3e9555025a1384c2)) @Purvansh Joshi
- Merge pull request #66 from Anshul-5/dependabot/github_actions/actions/upload-artifact-7

ci: bump actions/upload-artifact from 4 to 7 ([09b6d25](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/09b6d25ee79f265dc7041f7a8f71e46ea31553ea)) @Purvansh Joshi
- Merge pull request #65 from Anshul-5/dependabot/github_actions/actions/checkout-7

ci: bump actions/checkout from 4 to 7 ([957ec88](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/957ec888dadbd8a43f3985ca5a8774faa4306d30)) @Purvansh Joshi
- fix(ci): CodeQL build-mode none for embedded project ([94c253c](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/94c253cb9cd59d315117b92fdb92c17a406c66fc)) @Purvansh Joshi
- fix(ci): CodeQL language to c-cpp for ESP32 project ([96e3d94](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/96e3d949c2f07ee40ff7bb264046651f06af0632)) @Purvansh Joshi
- fix(ci): run changelog only after CI passes ([15cd87b](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/15cd87be4626383943053200a3694f55b48fc11f)) @Purvansh Joshi

### Infrastructure
- ci: bump actions/download-artifact from 4.1.9 to 8.0.1 (#170)

Bumps [actions/download-artifact](https://github.com/actions/download-artifact) from 4.1.9 to 8.0.1.
- [Release notes](https://github.com/actions/download-artifact/releases)
- [Commits](https://github.com/actions/download-artifact/compare/cc203385981b70ca67e1cc392babf9cc229d5806...3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c)

---
updated-dependencies:
- dependency-name: actions/download-artifact
  dependency-version: 8.0.1
  dependency-type: direct:production
  update-type: version-update:semver-major
...

Signed-off-by: dependabot[bot] <support@github.com>
Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com> ([ecfa62e](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/ecfa62e9eba953f0de46a50ef66c30e180ab73d0)) @dependabot[bot]
- ci: add workflow_dispatch to pages.yml ([e0500e3](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/e0500e3d8c174daf9aab56251dc77181651e2cef)) @Purvansh Joshi
- ci: bump github/codeql-action from 4.37.4 to 4.37.7 (#87)

Bumps [github/codeql-action](https://github.com/github/codeql-action) from 4.37.4 to 4.37.7.
- [Release notes](https://github.com/github/codeql-action/releases)
- [Changelog](https://github.com/github/codeql-action/blob/main/CHANGELOG.md)
- [Commits](https://github.com/github/codeql-action/compare/v4.37.4...v4.37.7)

---
updated-dependencies:
- dependency-name: github/codeql-action
  dependency-version: 4.37.7
  dependency-type: direct:production
  update-type: version-update:semver-patch
...

Signed-off-by: dependabot[bot] <support@github.com>
Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com> ([1b4b53c](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/1b4b53cb785d6e2156fa7486aac3cffc9230baea)) @dependabot[bot]
- ci: exempt roadmap subtask and epic issues from stale bot

The stale bot flagged 16 planned roadmap subtasks (L2-L9) that have not
been scheduled yet. Exempt issues carrying the 'type: subtask' or
'type: epic' labels so planned roadmap work is not auto-marked stale and
closed. Existing stale labels were removed from issues 15-30. ([e89a4f1](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/e89a4f144cc09b7c4fb110a1c5124e16b639237a)) @Purvansh Joshi
- ci: make pages workflow skip gracefully when Pages not enabled ([2285066](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/2285066c2cd7b8af7c730b2b8ade30f85dad8233)) @Purvansh Joshi
- ci: fix SBOM SARIF upload and size-history ESP-IDF action ([77f1a1e](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/77f1a1e376a0cad08e8593342398e3729dce8274)) @Purvansh Joshi
- ci: add SBOM, scorecard, changelog validation, and history tracking

## Summary

Adds 6 new CI/CD workflows:

- **SBOM Generation** - SPDX + CycloneDX software bills of materials
- **OpenSSF Scorecard** - Security assessment on every push
- **Changelog Validation** - Ensures CHANGELOG.md updated for feature PRs
- **Semantic Versioning Check** - Suggests version bump based on PR content
- **Benchmark History** - Tracks optical flow performance over time
- **Size History** - Tracks ESP32-S3 binary size over time

## Checks

All 21 CI checks passing. Fixes commitlint subject length limit (72→78) and semver grep exit codes. ([2250bae](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/2250baeeb435c2579fed61d6c807e67512473354)) @Purvansh Joshi
- ci: add remaining automation and quality checks

- GitHub Pages deployment for documentation
- Nightly build schedule (2:00 UTC daily)
- Code coverage reporting with Codecov
- Auto-close issues on fix/closes keyword
- Commit lint (validate conventional commits) ([8f02bcb](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/8f02bcbfb2251b19087dc3faf439f3b7c8ee5895)) @Purvansh Joshi
- ci: add comprehensive automation and quality checks

- GitLeaks secret detection
- Semantic PR title validation (conventional commits)
- PR size limiter (warn on large PRs)
- Auto-labeling PRs by file paths
- Performance benchmarks (optical flow)
- Release automation (tag push)
- Stale issue/PR bot
- License compliance check
- Issue templates (bug report, feature request)
- PR template ([df65b32](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/df65b32bfefe2348d33ef155309ef2ae1e5ad07d)) @Purvansh Joshi
- ci: add dependabot and codeql configuration ([285af08](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/285af08627eb31e6822708ac69b6141d6ad1ac51)) @Purvansh Joshi
- ci: use github-script for changelog ([5d5ad23](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/5d5ad23c428698630f864b6bfb24bec8e58d4fb8)) @Purvansh Joshi
### Added
- Homography projection and ground-plane kinematics (Q16.16 fixed-point, EWMA-filtered velocity/acceleration/jerk)
- Unit test suite for homography projection and kinematics
- ESP32-S3 camera capture driver (QVGA grayscale, double-buffered)
- INT8 bilinear downscaler (320x240 -> 160x120, Q8.8 fixed-point)
- Block-based SAD optical flow (16x16 macroblocks, SIMD-optimized)
- Unit test suites for downscaler and optical flow
- CI/CD pipeline with GitHub Actions
- Auto-updated changelog on PR merge

---

## [0.1.0] - 2026-07-13

### Added
- Initial documentation suite (architecture, API, security, runbook, roadmap)
- Mathematical specifications and formulations
- PhysEdge-Cloud revised proposal
- Technical review and patent analysis
- 23 mathematical/physical error fixes across documentation

### Fixed
- fix: ensure UTF-8 encoding when writing reproducibility report on Windows ([a07763a](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/a07763a78d03b1a1bd403386bb48446bf2ba02ad)) @Purvansh Joshi
- Dimensionally inconsistent v^2+a^2 energy formula (non-dimensionalized)
- CROP normalizing constant Z (proper softmax normalization)
- Panic Index units (notation table corrected to m/s^2)
- Lagrangian optimality condition (ratio of policy derivatives)
- EMA variance bias (use previous mean)
- Division by zero in adjacency cosine (stationary node guard)
- TTC formula for diverging objects (return infinity)
- Savitzky-Golay mislabel (renamed to weighted smoothing filter)
- KL divergence form (discretized integral with bin width)
- Missing SE_diff formula (bootstrap-based standard error)
- Two-sided critical value (1.96 -> 1.645 for one-sided test)
- Conformal prediction coverage claim (qualified for non-stationary data)
- Undefined psi(m) (defined as 1-exp(-m))
- Undefined phi_t (removed, clarified velocity weighting)
