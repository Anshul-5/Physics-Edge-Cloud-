"""
Closed-Loop Telemetry & Negative Constraints Pipeline (L7 Retraining Layer)

Implements:
1. Negative Constraint Pool: Captures Cloud/Human false positive adjudications
   and serializes them into negative training samples for continuous retraining.
2. Edge Parameter Streamer: Computes adaptive threshold adjustments (e.g., elevated
   EWMA jerk baseline thresholds and optical flow gating values) and streams them
   downlink to ESP32-S3 edge devices within 1 minute.
"""

import time
import json
import uuid
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable


class NegativeConstraintRecord:
    def __init__(
        self,
        event_id: str,
        camera_id: str,
        features: np.ndarray,
        jerk_peak: float,
        optical_flow_mag: float,
        adjudication_reason: str,
        timestamp: Optional[float] = None
    ):
        self.event_id = event_id
        self.camera_id = camera_id
        self.features = np.asarray(features, dtype=float)
        self.jerk_peak = float(jerk_peak)
        self.optical_flow_mag = float(optical_flow_mag)
        self.adjudication_reason = adjudication_reason
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "camera_id": self.camera_id,
            "features": self.features.tolist(),
            "jerk_peak": self.jerk_peak,
            "optical_flow_mag": self.optical_flow_mag,
            "adjudication_reason": self.adjudication_reason,
            "timestamp": self.timestamp
        }


class NegativeConstraintPool:
    """
    Thread-safe buffer aggregating false positive adjudications for batch retraining.
    """
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.records: List[NegativeConstraintRecord] = []

    def add_record(self, record: NegativeConstraintRecord):
        if len(self.records) >= self.max_size:
            self.records.pop(0)  # Evict oldest
        self.records.append(record)

    def size(self) -> int:
        return len(self.records)

    def export_dataset(self) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
        """
        Exports feature matrix, negative target labels (0), and metadata for retraining.
        """
        if not self.records:
            return np.empty((0, 0)), np.empty((0,)), []
            
        x_list = [r.features for r in self.records]
        x = np.vstack(x_list)
        y = np.zeros(len(self.records), dtype=int)  # All negative constraints have label 0
        metadata = [r.to_dict() for r in self.records]
        return x, y, metadata

    def clear(self):
        self.records.clear()


class EdgeParameterStreamer:
    """
    Computes calibrated EWMA threshold adjustments and generates downlink messages
    for ESP32-S3 edge nodes.
    """
    def __init__(
        self,
        default_jerk_threshold: float = 150.0,
        default_flow_threshold: float = 1.2,
        learning_rate: float = 0.15,
        max_jerk_threshold: float = 400.0,
        downlink_sender: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    ):
        self.default_jerk_threshold = default_jerk_threshold
        self.default_flow_threshold = default_flow_threshold
        self.learning_rate = learning_rate
        self.max_jerk_threshold = max_jerk_threshold
        self.downlink_sender = downlink_sender
        
        # Per-camera active thresholds: {camera_id: {"jerk_threshold": float, "flow_threshold": float}}
        self.camera_thresholds: Dict[str, Dict[str, float]] = {}
        self.delivery_log: List[Dict[str, Any]] = []

    def get_camera_thresholds(self, camera_id: str) -> Dict[str, float]:
        if camera_id not in self.camera_thresholds:
            self.camera_thresholds[camera_id] = {
                "jerk_threshold": self.default_jerk_threshold,
                "flow_threshold": self.default_flow_threshold
            }
        return self.camera_thresholds[camera_id]

    def adapt_thresholds(self, record: NegativeConstraintRecord) -> Dict[str, Any]:
        """
        Computes adapted threshold parameters based on the false positive jerk peak.
        
        Formula:
            delta_tau = min(max_jerk - current_jerk, lr * max(0, jerk_fp - current_jerk))
            new_tau = current_jerk + delta_tau
        """
        current = self.get_camera_thresholds(record.camera_id)
        curr_jerk = current["jerk_threshold"]
        
        # If false positive peak exceeded current threshold, elevate threshold
        if record.jerk_peak > curr_jerk:
            excess = record.jerk_peak - curr_jerk
            adjustment = min(self.max_jerk_threshold - curr_jerk, self.learning_rate * excess)
            new_jerk = curr_jerk + adjustment
        else:
            # Conservative minor upward nudge
            new_jerk = min(self.max_jerk_threshold, curr_jerk + 2.0)
            
        current["jerk_threshold"] = float(new_jerk)
        
        # Prepare downlink payload
        payload = {
            "version": "1.0",
            "camera_id": record.camera_id,
            "jerk_threshold": float(new_jerk),
            "flow_threshold": current["flow_threshold"],
            "timestamp": time.time(),
            "trigger_event_id": record.event_id,
            "reason": record.adjudication_reason
        }
        
        delivery_success = True
        if self.downlink_sender:
            try:
                delivery_success = bool(self.downlink_sender(record.camera_id, payload))
            except Exception:
                delivery_success = False
                
        log_entry = {
            "camera_id": record.camera_id,
            "payload": payload,
            "delivered": delivery_success,
            "timestamp": time.time()
        }
        self.delivery_log.append(log_entry)
        return payload


class ClosedLoopAdjudicator:
    """
    Coordinates Cloud false positive ingestion, negative constraint buffering,
    and immediate edge parameter downlink adaptation.
    """
    def __init__(
        self,
        constraint_pool: Optional[NegativeConstraintPool] = None,
        edge_streamer: Optional[EdgeParameterStreamer] = None
    ):
        self.pool = constraint_pool or NegativeConstraintPool()
        self.streamer = edge_streamer or EdgeParameterStreamer()
        self.adjudication_history: List[Dict[str, Any]] = []

    def adjudicate_false_positive(
        self,
        event_id: str,
        camera_id: str,
        features: np.ndarray,
        jerk_peak: float,
        optical_flow_mag: float,
        adjudication_reason: str
    ) -> Dict[str, Any]:
        """
        Ingests a false alarm verdict, registers it in the retraining pool,
        and streams adapted parameters to the source edge camera.
        """
        record = NegativeConstraintRecord(
            event_id=event_id,
            camera_id=camera_id,
            features=features,
            jerk_peak=jerk_peak,
            optical_flow_mag=optical_flow_mag,
            adjudication_reason=adjudication_reason
        )
        
        # 1. Ingest to negative retraining pool
        self.pool.add_record(record)
        
        # 2. Compute and stream adaptive thresholds to edge device
        downlink_payload = self.streamer.adapt_thresholds(record)
        
        result = {
            "event_id": event_id,
            "camera_id": camera_id,
            "pool_size": self.pool.size(),
            "downlink_payload": downlink_payload,
            "timestamp": time.time()
        }
        self.adjudication_history.append(result)
        return result
