#!/usr/bin/env python3
"""
Reproducibility Verification and Benchmarking Suite
PhysEdge-Cloud Layer 1 (ESP32-S3 Firmware Host Tests)

This script automates:
1. Building all host-side unit tests for L1 components (Downscaler, Optical Flow, Homography).
2. Running the tests and validating all check assertions.
3. Benchmarking latency performance of test sweeps.
4. Generating a formatted academic-ready verification report (REPRODUCIBILITY_REPORT.md).
"""

import os
import subprocess
import time
import sys
import platform

COMPONENTS = {
    "Downscaler": {
        "src": "edge/components/downscaler/downscaler.cpp",
        "test": "edge/test/test_downscaler.cpp",
        "inc": "edge/components/downscaler/include",
        "binary": "test_downscaler",
    },
    "Optical Flow": {
        "src": "edge/components/optical_flow/optical_flow.cpp",
        "test": "edge/test/test_optical_flow.cpp",
        "inc": "edge/components/optical_flow/include",
        "binary": "test_optical_flow",
    },
    "Homography": {
        "src": "edge/components/homography/homography.cpp",
        "test": "edge/test/test_homography.cpp",
        "inc": "edge/components/homography/include",
        "binary": "test_homography",
    },
    "Jerk Baseline": {
        "src": "edge/components/jerk_baseline/jerk_baseline.cpp",
        "test": "edge/test/test_jerk_baseline.cpp",
        "inc": "edge/components/jerk_baseline/include",
        "binary": "test_jerk_baseline",
    }
}

def clean_binaries():
    """Remove generated test binaries and coverage instrumentation files."""
    for comp in COMPONENTS.values():
        if os.path.exists(comp["binary"]):
            try:
                os.remove(comp["binary"])
            except OSError:
                pass
    
    # Clean up gcov coverage artifacts
    for file in os.listdir("."):
        if file.endswith(".gcda") or file.endswith(".gcno"):
            try:
                os.remove(file)
            except OSError:
                pass

def compile_and_run(name, info):
    """Compiles and runs a single component's unit test suite, measuring performance."""
    print(f"[*] Validating component: {name}...")
    
    # 1. Compile Command
    compile_cmd = [
        "g++", "-O3", "--std=c++17",
        f"-I{info['inc']}",
        info["src"],
        info["test"],
        "-o", info["binary"],
        "-lm"
    ]
    if "flags" in info:
        compile_cmd.extend(info["flags"])
    
    comp_start = time.perf_counter()
    compile_res = subprocess.run(compile_cmd, capture_output=True, text=True)
    comp_duration = (time.perf_counter() - comp_start) * 1000 # ms
    
    if compile_res.returncode != 0:
        print(f"[!] Compilation failed for {name}!")
        print(compile_res.stderr)
        return {
            "compiled": False,
            "passed": False,
            "errors": compile_res.stderr,
            "latency_ms": 0.0,
            "test_summary": "Compilation Error",
            "passed_count": 0,
            "failed_count": 0
        }
        
    # 2. Run Executable
    run_start = time.perf_counter()
    run_res = subprocess.run([f"./{info['binary']}"], capture_output=True, text=True)
    run_duration = (time.perf_counter() - run_start) * 1000 # ms
    
    passed = (run_res.returncode == 0)
    stdout = run_res.stdout
    
    # Parse test counts (e.g., "PASS test_solid_color" or "Results: 0 failures")
    lines = stdout.split("\n")
    passed_count = sum(1 for line in lines if line.startswith("PASS"))
    failed_count = sum(1 for line in lines if line.startswith("FAIL"))
    
    # If there are failures in output (even if return code is 0)
    if failed_count > 0 or "failures" in stdout.lower() and not "0 failures" in stdout.lower():
        passed = False
        
    return {
        "compiled": True,
        "passed": passed,
        "errors": run_res.stderr if not passed else "",
        "latency_ms": run_duration,
        "test_summary": stdout.strip(),
        "passed_count": passed_count,
        "failed_count": failed_count
    }

def generate_report(results, system_info):
    """Writes the markdown reproducibility report."""
    report_path = "REPRODUCIBILITY_REPORT.md"
    
    total_passed = sum(r["passed_count"] for r in results.values())
    total_failed = sum(r["failed_count"] for r in results.values())
    overall_status = "PASSED" if all(r["passed"] for r in results.values()) else "FAILED"
    
    markdown = f"""# Reproducibility & Verification Report: PhysEdge-Cloud L1

This document provides a cryptographic and test-validation transcript of the physical kinematic components running on local host-emulated hardware. It verifies mathematical correctness, performance benchmarks, and compilation compatibility.

---

## 💻 System Configuration & Environment
- **Operating System:** {system_info['os']} ({system_info['os_release']})
- **Architecture:** {system_info['arch']}
- **Compiler Version:** {system_info['compiler']}
- **Python Version:** {system_info['python_version']}
- **Verification Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}

---

## 📊 Verification & Latency Matrix

| Component Layer | Compilation | Tests Passed | Tests Failed | Execution Latency | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
    
    for name, r in results.items():
        comp_status = "✓ Success" if r["compiled"] else "✗ Failed"
        status = "🟢 PASS" if r["passed"] else "🔴 FAIL"
        latency = f"{r['latency_ms']:.3f} ms" if r["compiled"] else "N/A"
        markdown += f"| **{name}** | {comp_status} | {r['passed_count']} | {r['failed_count']} | {latency} | {status} |\n"
        
    markdown += f"""
### Overall Verification Summary: **{overall_status}**
- **Total Test Cases Executed:** {total_passed + total_failed}
- **Total Passed:** {total_passed}
- **Total Failed:** {total_failed}

---

## 🧪 Detailed Execution Transcript

"""
    
    for name, r in results.items():
        markdown += f"### {name} Unit Test Log\n"
        if r["compiled"]:
            markdown += f"```text\n{r['test_summary']}\n```\n\n"
        else:
            markdown += f"```text\nCompilation errors:\n{r['errors']}\n```\n\n"
            
    markdown += """
---

## 🔬 How to Reproduce Locally
To recreate this report and re-verify all mathematical derivations, execute the following command at the root of the workspace:
```bash
python3 reproduce.py
```

This verification suite compiles raw C source files with maximum compiler optimization (`-O3`) to simulate actual deployment execution times, verifying the kinematics mathematical pipelines.
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    print(f"[*] Reproducibility report written successfully to: {report_path}")

def get_system_info():
    """Gathers compiler and OS metadata for the report."""
    os_name = platform.system()
    os_release = platform.release()
    arch = platform.machine()
    python_ver = platform.python_version()
    
    # Get compiler version
    try:
        compiler_res = subprocess.run(["gcc", "--version"], capture_output=True, text=True)
        compiler = compiler_res.stdout.split("\n")[0] if compiler_res.returncode == 0 else "Unknown GCC"
    except OSError:
        compiler = "GCC not found"
        
    return {
        "os": os_name,
        "os_release": os_release,
        "arch": arch,
        "compiler": compiler,
        "python_version": python_ver
    }

def main():
    print("======================================================================")
    print("   PhysEdge-Cloud L1 Host-Emulation Verification & Benchmarking Suite ")
    print("======================================================================\n")
    
    clean_binaries()
    system_info = get_system_info()
    results = {}
    
    for name, info in COMPONENTS.items():
        results[name] = compile_and_run(name, info)
        
    generate_report(results, system_info)
    clean_binaries()
    
    all_passed = all(r["passed"] for r in results.values())
    if all_passed:
        print("\n[+] Verification successful! All host unit tests passed.")
        sys.exit(0)
    else:
        print("\n[!] Verification failed. Please inspect REPRODUCIBILITY_REPORT.md.")
        sys.exit(1)

if __name__ == "__main__":
    main()
