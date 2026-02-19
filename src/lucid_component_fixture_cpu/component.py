"""
Fixture CPU component — unified MQTT contract.

Publishes retained metadata, status, state, cfg, cfg/telemetry.
Stream telemetry: cpu_percent, load (gated).
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

    Retained: metadata, status, state, cfg, cfg/telemetry.
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
            cpu = float(psutil.cpu_percent(interval=None))
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
        self.publish_cfg({})
        self.publish_telemetry_cfg({
            "enabled": True,
            "metrics": {"cpu_percent": True, "load": True},
            "interval_s": 2,
            "change_threshold_percent": 2.0,
        })
        self.set_telemetry_config({
            "enabled": True,
            "metrics": {"cpu_percent": True, "load": True},
            "interval_s": 2,
            "change_threshold_percent": 2.0,
        })

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
        """Handle cmd/cfg/set → evt/cfg/set/result. Applies telemetry config from payload["set"]."""
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
            if set_dict:
                # Merge into current telemetry config and apply
                current = {
                    "enabled": self._telemetry_cfg.get("enabled", True),
                    "metrics": dict(self._telemetry_cfg.get("metrics", {})),
                    "interval_s": self._telemetry_cfg.get("interval_s", 2),
                    "change_threshold_percent": self._telemetry_cfg.get("change_threshold_percent", 2.0),
                }
                if "enabled" in set_dict:
                    current["enabled"] = bool(set_dict["enabled"])
                if "metrics" in set_dict and isinstance(set_dict["metrics"], dict):
                    current["metrics"] = dict(set_dict["metrics"])
                if "interval_s" in set_dict:
                    current["interval_s"] = int(set_dict["interval_s"])
                if "change_threshold_percent" in set_dict:
                    current["change_threshold_percent"] = float(set_dict["change_threshold_percent"])
                self.set_telemetry_config(current)
                self.publish_telemetry_cfg(current)
            self.publish_cfg_set_result(
                request_id=request_id,
                ok=True,
                applied=set_dict if set_dict else None,
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
