"""
Fixture CPU component — unified MQTT contract.

Publishes retained metadata, status, state, cfg (cfg includes nested telemetry).
Streams telemetry: cpu_percent, load (gated by cfg).
Commands: cmd/reset, cmd/ping, cmd/cfg/set → evt/<action>/result.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Optional

import psutil

from lucid_component_base import Component, ComponentContext


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FixtureCpuComponent(Component):
    """
    Test fixture component: CPU metrics under unified topic structure.

    Retained: metadata, status, state, cfg (includes nested telemetry).
    Stream: logs, telemetry/cpu_percent, telemetry/load (gated).
    Commands: reset, ping, cfg/set.
    """

    _PUBLISH_INTERVAL_SECONDS = 2.0

    def __init__(self, context: ComponentContext) -> None:
        super().__init__(context)
        self._log = self.context.logger()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def component_id(self) -> str:
        return "fixture_cpu"

    def capabilities(self) -> list[str]:
        return ["reset", "ping"]

    def metadata(self) -> dict:
        out = super().metadata()
        out["capabilities"] = self.capabilities()
        return out

    def get_state_payload(self) -> dict:
        try:
            # Use interval=0.1 to ensure we get a fresh measurement, not cached/zero
            cpu = float(psutil.cpu_percent(interval=0.1))
        except Exception:
            cpu = 0.0
        try:
            load = float(psutil.getloadavg()[0]) if hasattr(psutil, "getloadavg") else 0.0
        except Exception:
            load = 0.0
        return {"cpu_percent": cpu, "load": load}

    def _start(self) -> None:
        self._publish_all_retained()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="LucidFixtureCpuLoop",
            daemon=True,
        )
        self._thread.start()
        self._log.info("Started component: %s", self.component_id)

    def _stop(self) -> None:
        t = self._thread
        if t:
            self._stop_event.set()
            t.join(timeout=2.0)
            if t.is_alive():
                self._log.warning("CPU loop thread did not stop within timeout")
            self._thread = None
        self._log.info("Stopped component: %s", self.component_id)

    def _publish_all_retained(self) -> None:
        self.publish_metadata()
        self.publish_status()
        self.publish_state()
        # Set and publish unified cfg with telemetry nested
        # Metrics are derived from state, so we enable the ones we want with per-metric configs
        telemetry_cfg = {
            "metrics": {
                "cpu_percent": {
                    "enabled": True,
                    "interval_s": 2,
                    "change_threshold_percent": 2.0,
                },
                "load": {
                    "enabled": True,
                    "interval_s": 2,
                    "change_threshold_percent": 2.0,
                },
            },
        }
        self.set_telemetry_config(telemetry_cfg)
        # publish_cfg() will automatically include all state metrics, merging with current config
        self.publish_cfg()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                state = self.get_state_payload()
                self.publish_state(state)
                cpu = state.get("cpu_percent", 0.0)
                load = state.get("load", 0.0)
                if self.should_publish_telemetry("cpu_percent", cpu):
                    self.publish_telemetry("cpu_percent", cpu)
                if self.should_publish_telemetry("load", load):
                    self.publish_telemetry("load", load)
            except Exception:
                self._log.exception("Failed to publish fixture CPU telemetry")

            if self._stop_event.wait(self._PUBLISH_INTERVAL_SECONDS):
                break

    def on_cmd_reset(self, payload_str: str) -> None:
        """Handle cmd/reset: parse request_id, publish evt/reset/result."""
        try:
            payload = json.loads(payload_str) if payload_str else {}
            request_id = payload.get("request_id", "")
        except json.JSONDecodeError:
            request_id = ""
        self.publish_result("reset", request_id, ok=True, error=None)

    def on_cmd_ping(self, payload_str: str) -> None:
        """Handle cmd/ping → evt/ping/result."""
        try:
            payload = json.loads(payload_str) if payload_str else {}
            request_id = payload.get("request_id", "")
        except json.JSONDecodeError:
            request_id = ""
        self.publish_result("ping", request_id, ok=True, error=None)

    def on_cmd_cfg_set(self, payload_str: str) -> None:
        """Handle cmd/cfg/set → evt/cfg/set/result. Applies config from payload["set"] (telemetry nested)."""
        try:
            payload = json.loads(payload_str) if payload_str else {}
            request_id = payload.get("request_id", "")
            set_dict = payload.get("set") or {}
        except json.JSONDecodeError:
            request_id = ""
            set_dict = {}

        if not isinstance(set_dict, dict):
            self.publish_cfg_set_result(
                request_id=request_id,
                ok=False,
                applied=None,
                error="payload 'set' must be an object",
                ts=_utc_iso(),
            )
            return

        try:
            applied = {}
            
            # Handle logs_enabled config
            if "logs_enabled" in set_dict:
                self._logs_enabled = bool(set_dict["logs_enabled"])
                applied["logs_enabled"] = self._logs_enabled
            
            # Handle nested telemetry config
            if "telemetry" in set_dict:
                telemetry_set = set_dict["telemetry"]
                if not isinstance(telemetry_set, dict):
                    self.publish_cfg_set_result(
                        request_id=request_id,
                        ok=False,
                        applied=None,
                        error="telemetry must be an object",
                        ts=_utc_iso(),
                    )
                    return
                
                # Get available metrics from state to validate
                state_payload = self.get_state_payload()
                available_metrics = set(state_payload.keys()) if isinstance(state_payload, dict) else set()
                
                # Get current telemetry config
                current_metrics = dict(self._telemetry_cfg.get("metrics", {}))
                
                # Merge metrics config from set_dict
                if "metrics" in telemetry_set and isinstance(telemetry_set["metrics"], dict):
                    for metric_name, metric_cfg in telemetry_set["metrics"].items():
                        # Only process metrics that exist in state
                        if metric_name not in available_metrics:
                            self._log.warning("Ignoring metric not in state: %s", metric_name)
                            continue
                        
                        # Merge metric config
                        if metric_name in current_metrics and isinstance(current_metrics[metric_name], dict):
                            # Deep merge existing config
                            current_metrics[metric_name] = {
                                **current_metrics[metric_name],
                                **metric_cfg,
                            }
                            # Ensure all fields are present
                            if "enabled" not in current_metrics[metric_name]:
                                current_metrics[metric_name]["enabled"] = False
                            if "interval_s" not in current_metrics[metric_name]:
                                current_metrics[metric_name]["interval_s"] = 2
                            if "change_threshold_percent" not in current_metrics[metric_name]:
                                current_metrics[metric_name]["change_threshold_percent"] = 2.0
                        else:
                            # New metric config
                            current_metrics[metric_name] = {
                                "enabled": bool(metric_cfg.get("enabled", False)) if isinstance(metric_cfg, dict) else bool(metric_cfg),
                                "interval_s": int(metric_cfg.get("interval_s", 2)) if isinstance(metric_cfg, dict) else 2,
                                "change_threshold_percent": float(metric_cfg.get("change_threshold_percent", 2.0)) if isinstance(metric_cfg, dict) else 2.0,
                            }
                    
                    # Ensure all state metrics are present (add missing ones with defaults)
                    for metric_name in available_metrics:
                        if metric_name not in current_metrics:
                            current_metrics[metric_name] = {
                                "enabled": False,
                                "interval_s": 2,
                                "change_threshold_percent": 2.0,
                            }
                
                # Update telemetry config
                self.set_telemetry_config({"metrics": current_metrics})
                applied["telemetry"] = telemetry_set
            
            # Republish unified cfg (will include all state metrics with per-metric configs)
            self.publish_cfg()
            
            self.publish_cfg_set_result(
                request_id=request_id,
                ok=True,
                applied=applied if applied else None,
                error=None,
                ts=_utc_iso(),
            )
        except Exception as exc:
            self._log.exception("Failed to apply cfg/set")
            self.publish_cfg_set_result(
                request_id=request_id,
                ok=False,
                applied=None,
                error=str(exc),
                ts=_utc_iso(),
            )
