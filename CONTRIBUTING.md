# Contributing to PhysEdge-Cloud

Thank you for your interest in contributing to **PhysEdge-Cloud**!

This project adheres to the **OpenSSF Best Practices Program** standards. All contributions must follow the security, code quality, and peer review guidelines outlined below.

---

## 1. Code Review & Pull Request Workflow

1. **All Changes Must Go Through Reviewed Pull Requests**:
   - Direct pushes to main are disallowed.
   - Every pull request requires at least **1 approving review** from a designated code owner before merging.
   - PRs must pass 100% of automated CI checks (CodeQL SAST, secret scanning, dependency audits, firmware compilation, and unit tests).

2. **Branch Naming Conventions**:
   - eat/<feature-name> for new features or capabilities.
   - ix/<issue-name> for bug fixes and security patches.
   - chore/<task-name> for maintenance and workflow updates.

3. **Conventional Commits**:
   - Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
     - eat(...): A new feature
     - ix(...): A bug fix
     - docs(...): Documentation changes
     - style(...): Code style or formatting changes
     - perf(...): Performance improvements
     - 	est(...): Adding or updating tests
     - ci(...): CI/CD workflow changes
     - chore(...): General maintenance

---

## 2. Code Ownership & Areas of Responsibility

Reviewers are assigned automatically via [.github/CODEOWNERS](.github/CODEOWNERS):
- **Core Maintainers**: @Anshul-5, @purvanshjoshi, @archittmittal
- **Critical Paths**: Firmware OTA (edge/components/secure_ota), Differential Privacy (cloud_engine/privacy.py), Forensic Storage (cloud_engine/storage.py), and CI/CD pipelines (.github/workflows/).

---

## 3. Testing & Verification

Before submitting a pull request, ensure all local tests pass:

`ash
# Python Unit & Integration Tests (L2 Regional + L3 Cloud)
pytest regional_node/ tests/ cloud_engine/tests/

# Host-Emulation Verification & Benchmarking Suite (L1 Firmware)
python reproduce.py
`

---

## 4. Security & Vulnerability Reporting

If you discover a potential security vulnerability, please report it via our **Responsible Disclosure Program** as detailed in [SECURITY.md](SECURITY.md). Do not file public GitHub issues for undisclosed security vulnerabilities.
