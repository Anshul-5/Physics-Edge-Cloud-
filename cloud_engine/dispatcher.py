"""
Fleet Operations Telemetry Dashboard & Alert Dispatcher (L8/L9 Operations Layer)

Implements:
1. Alert Dispatcher: High-throughput incident dispatcher connecting Cloud adjudications
   to external operational endpoints (Slack, Webhook, PagerDuty) with <= 100 ms dispatch latency.
2. Fleet Metrics Collector: Prometheus gauge and counter exporter tracking system KPIs
   (end-to-end latency, edge FPS, network usage, buffer watermarks, alert rate).
"""

import time
import json
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any, Callable


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertPayload:
    def __init__(
        self,
        alert_id: str,
        camera_id: str,
        severity: AlertSeverity,
        anomaly_score: float,
        kinematics: Dict[str, float],
        description: str,
        timestamp: Optional[float] = None
    ):
        self.alert_id = alert_id
        self.camera_id = camera_id
        self.severity = severity
        self.anomaly_score = float(anomaly_score)
        self.kinematics = kinematics
        self.description = description
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "camera_id": self.camera_id,
            "severity": self.severity.value,
            "anomaly_score": self.anomaly_score,
            "kinematics": self.kinematics,
            "description": self.description,
            "timestamp": self.timestamp
        }

    def format_slack_message(self) -> Dict[str, Any]:
        """Formats payload for Slack Incoming Webhook."""
        color = "#36a64f" if self.severity == AlertSeverity.INFO else ("#ecb22e" if self.severity == AlertSeverity.WARNING else "#e01e5a")
        return {
            "text": f"*{self.severity.value} Alert:* Camera `{self.camera_id}` Anomaly Score: `{self.anomaly_score:.2f}`",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {"title": "Camera ID", "value": self.camera_id, "short": True},
                        {"title": "Anomaly Score", "value": f"{self.anomaly_score:.3f}", "short": True},
                        {"title": "Description", "value": self.description, "short": False},
                        {"title": "Kinematics", "value": json.dumps(self.kinematics), "short": False}
                    ],
                    "footer": "PhysEdge-Cloud Alert Dispatcher",
                    "ts": int(self.timestamp)
                }
            ]
        }

    def format_pagerduty_event(self, routing_key: str = "default") -> Dict[str, Any]:
        """Formats payload for PagerDuty Events API v2."""
        pd_severity = "info" if self.severity == AlertSeverity.INFO else ("warning" if self.severity == AlertSeverity.WARNING else "critical")
        return {
            "routing_key": routing_key,
            "event_action": "trigger",
            "dedup_key": self.alert_id,
            "payload": {
                "summary": f"[{self.severity.value}] {self.description} on {self.camera_id}",
                "source": self.camera_id,
                "severity": pd_severity,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(self.timestamp)),
                "custom_details": {
                    "anomaly_score": self.anomaly_score,
                    "kinematics": self.kinematics
                }
            }
        }


class AlertDispatcher:
    """
    Asynchronously dispatches verified security alerts to operational webhooks and logging channels.
    SLA requirement: <= 100 ms dispatch latency.
    """
    def __init__(
        self,
        webhook_client: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        max_history: int = 1000
    ):
        self.webhook_client = webhook_client
        self.max_history = max_history
        self.dispatch_log: List[Dict[str, Any]] = []

    def dispatch(
        self,
        alert: AlertPayload,
        channel: str = "webhook",
        target_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches alert and tracks latency against the 100 ms SLA.
        """
        t_start = time.perf_counter()
        
        if channel == "slack":
            formatted_body = alert.format_slack_message()
        elif channel == "pagerduty":
            formatted_body = alert.format_pagerduty_event()
        else:
            formatted_body = alert.to_dict()
            
        success = True
        if self.webhook_client and target_url:
            try:
                success = bool(self.webhook_client(target_url, formatted_body))
            except Exception:
                success = False
                
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        
        record = {
            "alert_id": alert.alert_id,
            "channel": channel,
            "target_url": target_url,
            "latency_ms": t_elapsed_ms,
            "success": success,
            "sla_met": t_elapsed_ms <= 100.0,
            "timestamp": time.time()
        }
        
        if len(self.dispatch_log) >= self.max_history:
            self.dispatch_log.pop(0)
        self.dispatch_log.append(record)
        return record


class FleetMetricsCollector:
    """
    Aggregates edge and cloud metrics and exposes Prometheus scrape format.
    """
    def __init__(self):
        # Latencies in milliseconds
        self.e2e_latencies: List[float] = []
        # Per-camera metrics
        self.camera_fps: Dict[str, float] = {}
        self.camera_buffer_watermarks: Dict[str, float] = {}
        self.total_alerts_dispatched = 0
        self.total_false_alarms = 0

    def record_e2e_latency(self, latency_ms: float):
        self.e2e_latencies.append(latency_ms)
        if len(self.e2e_latencies) > 5000:
            self.e2e_latencies.pop(0)

    def record_camera_fps(self, camera_id: str, fps: float):
        self.camera_fps[camera_id] = float(fps)

    def record_buffer_watermark(self, camera_id: str, ratio: float):
        self.camera_buffer_watermarks[camera_id] = float(ratio)

    def record_alert(self, is_false_alarm: bool = False):
        self.total_alerts_dispatched += 1
        if is_false_alarm:
            self.total_false_alarms += 1

    def get_prometheus_metrics(self) -> str:
        """Exposes Prometheus text metric representations."""
        lines = []
        
        # 1. End-to-End Latency
        avg_latency = float(np.mean(self.e2e_latencies)) if self.e2e_latencies else 0.0
        lines.append("# HELP physedge_e2e_latency_ms Average end-to-end processing latency in ms.")
        lines.append("# TYPE physedge_e2e_latency_ms gauge")
        lines.append(f"physedge_e2e_latency_ms {avg_latency:.3f}")
        
        # 2. Camera FPS
        lines.append("# HELP physedge_camera_fps Current frame processing rate per camera.")
        lines.append("# TYPE physedge_camera_fps gauge")
        for cam_id, fps in sorted(self.camera_fps.items()):
            lines.append(f'physedge_camera_fps{{camera_id="{cam_id}"}} {fps:.2f}')
            
        # 3. Buffer Watermarks
        lines.append("# HELP physedge_buffer_watermark_ratio PSRAM circular buffer fill ratio.")
        lines.append("# TYPE physedge_buffer_watermark_ratio gauge")
        for cam_id, ratio in sorted(self.camera_buffer_watermarks.items()):
            lines.append(f'physedge_buffer_watermark_ratio{{camera_id="{cam_id}"}} {ratio:.4f}')
            
        # 4. Total Alerts Dispatched
        lines.append("# HELP physedge_alerts_dispatched_total Total security alerts dispatched.")
        lines.append("# TYPE physedge_alerts_dispatched_total counter")
        lines.append(f"physedge_alerts_dispatched_total {self.total_alerts_dispatched}")
        
        # 5. False Alarm Rate
        far = (self.total_false_alarms / self.total_alerts_dispatched) if self.total_alerts_dispatched > 0 else 0.0
        lines.append("# HELP physedge_false_alarm_rate Current empirical False Alarm Rate.")
        lines.append("# TYPE physedge_false_alarm_rate gauge")
        lines.append(f"physedge_false_alarm_rate {far:.4f}")
        
        return "\n".join(lines) + "\n"

import numpy as np
