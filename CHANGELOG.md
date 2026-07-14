# Changelog

All notable changes to PhysEdge-Cloud will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]


### Changed
- fix(ci): CodeQL language to c-cpp for ESP32 project ([96e3d94](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/96e3d949c2f07ee40ff7bb264046651f06af0632)) @Purvansh Joshi
- fix(ci): run changelog only after CI passes ([15cd87b](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/15cd87be4626383943053200a3694f55b48fc11f)) @Purvansh Joshi

### Infrastructure
- ci: add dependabot and codeql configuration ([285af08](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/285af08627eb31e6822708ac69b6141d6ad1ac51)) @Purvansh Joshi
- ci: use github-script for changelog ([5d5ad23](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/5d5ad23c428698630f864b6bfb24bec8e58d4fb8)) @Purvansh Joshi
### Added
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
