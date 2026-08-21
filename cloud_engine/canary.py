"""
Progressive Canary Rollout & SPRT Rollback Controller (L8 Delivery Layer)

Implements:
1. Sequential Probability Ratio Test (SPRT) online safety rollback monitor.
   Hypotheses:
       H0: p = p0 (Acceptable baseline False Alarm Rate, e.g. 1%)
       H1: p = p1 (Elevated unacceptable False Alarm Rate, e.g. 5%)
   Log-Likelihood Ratio:
       S_n = k * ln(p1 / p0) + (n - k) * ln((1 - p1) / (1 - p0))
   Abort condition:
       S_n >= B where B = ln((1 - beta) / alpha)
   Accept condition:
       S_n <= A where A = ln(beta / (1 - alpha))

2. Progressive Canary Rollout Scheduler (5% -> 20% -> 100%).
   Deterministic hashing-based fleet partitioning, progressive stage promotion,
   and automated rollback interception.
"""

import math
import hashlib
import time
from enum import Enum
from typing import Dict, List, Optional, Callable, Any


class CanaryState(str, Enum):
    IDLE = "IDLE"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    ROLLED_BACK = "ROLLED_BACK"
    COMPLETED = "COMPLETED"


class SPRTDecision(str, Enum):
    CONTINUE = "CONTINUE"
    ACCEPT_H0 = "ACCEPT_H0"   # Safe (baseline FAR confirmed)
    REJECT_H0 = "REJECT_H0"   # Abort / Rollback (elevated FAR detected)


class SPRTController:
    """
    Wald's Sequential Probability Ratio Test (SPRT) for online False Alarm Rate monitoring.
    """
    def __init__(
        self,
        p0: float = 0.01,
        p1: float = 0.05,
        alpha: float = 0.05,
        beta: float = 0.05,
        on_rollback_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Args:
            p0: Baseline acceptable false alarm rate (H0).
            p1: Unacceptable elevated false alarm rate (H1).
            alpha: Type I error probability (false alarm of rollback).
            beta: Type II error probability (missed detection of bad model).
            on_rollback_callback: Optional hook called when rollback threshold B is reached.
        """
        if not (0 < p0 < p1 < 1):
            raise ValueError(f"Requires 0 < p0 < p1 < 1. Got p0={p0}, p1={p1}")
        if not (0 < alpha < 1 and 0 < beta < 1):
            raise ValueError(f"Requires 0 < alpha, beta < 1. Got alpha={alpha}, beta={beta}")
            
        self.p0 = p0
        self.p1 = p1
        self.alpha = alpha
        self.beta = beta
        self.on_rollback_callback = on_rollback_callback
        
        # Log-likelihood ratio terms
        self.log_p1_p0 = math.log(self.p1 / self.p0)
        self.log_q1_q0 = math.log((1.0 - self.p1) / (1.0 - self.p0))
        
        # Wald decision thresholds
        self.B = math.log((1.0 - self.beta) / self.alpha)   # Upper bound (Abort / Rollback)
        self.A = math.log(self.beta / (1.0 - self.alpha))   # Lower bound (Accept H0 / Safe)
        
        self.total_samples = 0
        self.false_alarms = 0
        self.s_n = 0.0
        self.decision = SPRTDecision.CONTINUE
        self.is_aborted = False

    def reset(self):
        """Resets the sequential test counters and log-likelihood statistics."""
        self.total_samples = 0
        self.false_alarms = 0
        self.s_n = 0.0
        self.decision = SPRTDecision.CONTINUE
        self.is_aborted = False

    def update(self, is_false_alarm: bool) -> SPRTDecision:
        """
        Ingests an alert outcome and updates the SPRT statistic.
        
        Args:
            is_false_alarm: True if the alert was a false positive, False if valid detection.
            
        Returns:
            SPRTDecision: Current evaluation status (CONTINUE, ACCEPT_H0, or REJECT_H0).
        """
        if self.is_aborted:
            return SPRTDecision.REJECT_H0
            
        self.total_samples += 1
        if is_false_alarm:
            self.false_alarms += 1
            
        n = self.total_samples
        k = self.false_alarms
        
        # Compute S_n = k * ln(p1/p0) + (n - k) * ln((1-p1)/(1-p0))
        self.s_n = k * self.log_p1_p0 + (n - k) * self.log_q1_q0
        
        # Check decision boundaries
        if self.s_n >= self.B:
            self.decision = SPRTDecision.REJECT_H0
            self.is_aborted = True
            if self.on_rollback_callback:
                self.on_rollback_callback(self.get_metrics())
        elif self.s_n <= self.A:
            self.decision = SPRTDecision.ACCEPT_H0
        else:
            self.decision = SPRTDecision.CONTINUE
            
        return self.decision

    def get_metrics(self) -> Dict[str, Any]:
        """Returns current SPRT metrics."""
        return {
            "total_samples": self.total_samples,
            "false_alarms": self.false_alarms,
            "empirical_far": (self.false_alarms / self.total_samples) if self.total_samples > 0 else 0.0,
            "s_n": float(self.s_n),
            "lower_bound_A": float(self.A),
            "upper_bound_B": float(self.B),
            "decision": self.decision.value,
            "is_aborted": self.is_aborted
        }


class CanaryRolloutScheduler:
    """
    Manages progressive staged deployment (5% -> 20% -> 100%) and automatic SPRT safety aborts.
    """
    def __init__(
        self,
        champion_version: str,
        challenger_version: str,
        stages: Optional[List[float]] = None,
        sprt_controller: Optional[SPRTController] = None
    ):
        self.champion_version = champion_version
        self.challenger_version = challenger_version
        self.stages = stages or [0.05, 0.20, 1.00]
        self.current_stage_idx = 0
        self.state = CanaryState.IDLE
        
        self.sprt = sprt_controller or SPRTController(
            on_rollback_callback=self._handle_sprt_rollback
        )
        # Ensure callback is bound to scheduler rollback
        self.sprt.on_rollback_callback = self._handle_sprt_rollback
        self.stage_history: List[Dict[str, Any]] = []

    def start_rollout(self):
        """Starts the progressive rollout at Stage 0."""
        self.current_stage_idx = 0
        self.state = CanaryState.IN_PROGRESS
        self.sprt.reset()
        self._record_stage_event("STAGE_STARTED")

    def _handle_sprt_rollback(self, metrics: Dict[str, Any]):
        """Callback invoked when SPRT controller detects unacceptable false alarm rates."""
        self.state = CanaryState.ROLLED_BACK
        self._record_stage_event("AUTOMATIC_ROLLBACK_TRIGGERED", details=metrics)

    def should_route_to_challenger(self, device_id: str) -> bool:
        """
        Determines if a device belongs to the active canary cohort using deterministic hashing.
        
        Args:
            device_id: Unique identifier for edge camera / device.
            
        Returns:
            bool: True if device receives challenger model, False if champion model.
        """
        if self.state in [CanaryState.IDLE, CanaryState.ROLLED_BACK]:
            return False
        if self.state == CanaryState.COMPLETED:
            return True
            
        current_pct = self.stages[self.current_stage_idx]
        
        # Deterministic hash modulo 100: [0, 99] / 100.0 -> [0.00, 0.99]
        hash_digest = hashlib.sha256(device_id.encode('utf-8')).hexdigest()
        hash_val = int(hash_digest[:8], 16) % 100
        device_cohort = hash_val / 100.0
        
        return device_cohort < current_pct

    def get_device_target_version(self, device_id: str) -> str:
        """Returns the model version assigned to the given device."""
        if self.should_route_to_challenger(device_id):
            return self.challenger_version
        return self.champion_version

    def record_canary_alert(self, is_false_alarm: bool) -> SPRTDecision:
        """Ingests an alert outcome from canary devices."""
        if self.state != CanaryState.IN_PROGRESS:
            return self.sprt.decision
        return self.sprt.update(is_false_alarm)

    def advance_stage(self) -> bool:
        """
        Advances rollout to the next percentage stage if SPRT has not aborted.
        
        Returns:
            bool: True if successfully advanced or completed, False if aborted/blocked.
        """
        if self.state != CanaryState.IN_PROGRESS:
            return False
            
        if self.sprt.is_aborted:
            self.state = CanaryState.ROLLED_BACK
            return False
            
        if self.current_stage_idx + 1 < len(self.stages):
            self.current_stage_idx += 1
            self.sprt.reset()  # Reset SPRT for next cohort testing window
            self._record_stage_event("STAGE_ADVANCED")
            return True
        else:
            self.state = CanaryState.COMPLETED
            self._record_stage_event("ROLLOUT_COMPLETED")
            return True

    def pause(self):
        """Pauses the rollout."""
        if self.state == CanaryState.IN_PROGRESS:
            self.state = CanaryState.PAUSED
            self._record_stage_event("ROLLOUT_PAUSED")

    def resume(self):
        """Resumes the rollout."""
        if self.state == CanaryState.PAUSED:
            self.state = CanaryState.IN_PROGRESS
            self._record_stage_event("ROLLOUT_RESUMED")

    def manual_rollback(self):
        """Manually aborts rollout and restores all devices to champion version."""
        self.state = CanaryState.ROLLED_BACK
        self._record_stage_event("MANUAL_ROLLBACK")

    def _record_stage_event(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        self.stage_history.append({
            "event": event_type,
            "stage_idx": self.current_stage_idx,
            "stage_pct": self.stages[self.current_stage_idx] if self.current_stage_idx < len(self.stages) else 1.0,
            "state": self.state.value,
            "timestamp": time.time(),
            "details": details or {}
        })
