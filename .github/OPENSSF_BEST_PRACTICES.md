# OpenSSF Best Practices Self-Assessment

This document outlines the OpenSSF (CII) Best Practices criteria compliance for **PhysEdge-Cloud**.

## 1. Basics

- **Basic project website content**: Documented in [README.md](../README.md) with architectural diagrams, cascade tier explanations, and operational overview.
- **FLOSS License**: Apache License 2.0 located at [LICENSE](../LICENSE).
- **Documentation**: Comprehensive guides in [CONTRIBUTING.md](../CONTRIBUTING.md), [SECURITY.md](../SECURITY.md), [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md), and [CHANGELOG.md](../CHANGELOG.md).

## 2. Change Control

- **Public version control**: Git repository hosted on GitHub at https://github.com/Anshul-5/Physics-Edge-Cloud-.
- **Unique version numbers**: Semantic versioning enforced via CI workflow [.github/workflows/semver-check.yml](workflows/semver-check.yml).
- **Release notes**: Maintained in [CHANGELOG.md](../CHANGELOG.md) following Keep a Changelog 1.1.0 standard.
- **Branch protection & code review**: Defined in [.github/rulesets/main-protection.json](rulesets/main-protection.json) requiring PR peer reviews and Code Owners approval ([.github/CODEOWNERS](CODEOWNERS)).

## 3. Reporting & Security

- **Vulnerability disclosure policy**: Detailed in [SECURITY.md](../SECURITY.md) with secure reporting email and private GitHub Security Advisories.
- **Supply chain security**: All GitHub Actions pinned to immutable 40-character commit SHAs; Python dependencies locked with audited 
equirements.lock ([cloud_engine/requirements.lock](../cloud_engine/requirements.lock), [
egional_node/requirements.lock](../regional_node/requirements.lock)).
- **Cryptography**: Secure boot OTA validation with ECDSA P-256 and SHA-256 in [edge/components/secure_ota](../edge/components/secure_ota).

## 4. Quality & Testing

- **Automated test suite**: 54 automated pytest suites covering cloud engine, feedback loops, and storage, plus C++ firmware unit tests.
- **Continuous Integration**: Automated CI runs on all PRs and pushes ([.github/workflows/ci.yml](workflows/ci.yml)).
- **Fuzz testing**: libFuzzer harnesses in [edge/test/fuzz/](../edge/test/fuzz/) integrated with ClusterFuzzLite ([.github/workflows/cflite_pr.yml](workflows/cflite_pr.yml)).
- **Static analysis**: Dual-language CodeQL SAST ([.github/workflows/codeql.yml](workflows/codeql.yml)), cppcheck, and clang-format enforced in CI.
