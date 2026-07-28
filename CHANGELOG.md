# Changelog

All notable changes to PhysEdge-Cloud will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]


### Documentation
- docs: update changelog [skip ci] ([86ec0ea](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/86ec0ea92f5af149bb3f0f1736a748b79c12f198)) @github-actions[bot]
- docs: update changelog [skip ci] ([31bdefd](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/31bdefd0a2e1f83107bd56287d4ce2def233cd7f)) @github-actions[bot]
- docs: update changelog [skip ci] ([12e969b](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/12e969b9209e5b748a991d7befa78f11518db43e)) @github-actions[bot]
- docs: update changelog [skip ci] ([108db1a](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/108db1a9de4193c95fbea2c377809306e6714269)) @github-actions[bot]
- docs: update changelog [skip ci] ([c9afade](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/c9afade6080622000a72fe58e3a48a737dc9f67b)) @github-actions[bot]
- docs: update changelog [skip ci] ([1e23d90](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/1e23d90ebb54f240424b6836d9ff60f897c0a0c2)) @github-actions[bot]
- docs: update changelog [skip ci] ([9d82d73](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/9d82d73d2b635379cc3bc492c203038d761abb7d)) @github-actions[bot]
- docs: update changelog [skip ci] ([dfc9684](https://github.com/Anshul-5/Physics-Edge-Cloud-/commit/dfc9684814dcd97602fe4008a15ba48d03ad3e80)) @github-actions[bot]

### Changed
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
