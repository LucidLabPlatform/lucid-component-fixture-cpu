from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import psutil

from lucid_component_base import Component, ComponentContext


@dataclass(frozen=True)
class CpuMetrics:
    cpu_percent: float
    temperature_c: Optional[float]
    ts: str


class FixtureCpuComponent(Component):
    """
    Test fixture component: periodically publishes CPU metrics as telemetry.

    Telemetry topic:
      {base_topic}/components/{component_id}/evt/telemetry
    """

    _PUBLISH_INTERVAL_SECONDS = 5.0

    def __init__(self, context: ComponentContext):
        super().__init__(context)
        self._log = self.context.logger()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._temperature_available = True

    @property
    def component_id(self) -> str:
        return "fixture_cpu"

    def _start(self) -> None:
        self._temperature_available = self._detect_temperature_available()
        if not self._temperature_available:
            self._log.info("CPU temperature is unavailable on this host")

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
        if not t:
            return

        self._stop_event.set()
        t.join(timeout=2.0)
        if t.is_alive():
            self._log.warning("CPU loop thread did not stop within timeout")
            return

        self._thread = None
        self._log.info("Stopped component: %s", self.component_id)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._publish_metrics()
            except Exception:
                self._log.exception("Failed to publish fixture CPU telemetry")

            if self._stop_event.wait(self._PUBLISH_INTERVAL_SECONDS):
                break

    def _publish_metrics(self) -> None:
        metrics = self._read_metrics()
        payload = {
            "type": "cpu",
            "fixture": True,
            "cpu_percent": metrics.cpu_percent,
            "temperature_c": metrics.temperature_c,
            "ts": metrics.ts,
        }
        topic = self.context.topic("evt/telemetry")
        self.context.mqtt.publish(topic, payload, qos=0, retain=False)

    def _read_metrics(self) -> CpuMetrics:
        cpu_percent = float(psutil.cpu_percent(interval=None))
        temperature_c = self._read_temperature()
        return CpuMetrics(
            cpu_percent=cpu_percent,
            temperature_c=temperature_c,
            ts=self._utc_timestamp(),
        )

    def _read_temperature(self) -> Optional[float]:
        if not self._temperature_available:
            return None

        for entry in self._temperature_entries():
            current = getattr(entry, "current", None)
            if current is None:
                continue
            try:
                return float(current)
            except (TypeError, ValueError):
                continue
        return None

    def _detect_temperature_available(self) -> bool:
        return bool(self._temperature_entries())

    def _temperature_entries(self) -> list[object]:
        sensors_fn = getattr(psutil, "sensors_temperatures", None)
        if not callable(sensors_fn):
            return []

        try:
            sensors = sensors_fn()
        except Exception:
            return []

        if not isinstance(sensors, dict):
            return []

        entries: list[object] = []
        for values in sensors.values():
            if isinstance(values, list):
                entries.extend(values)
        return entries

    @staticmethod
    def _utc_timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
