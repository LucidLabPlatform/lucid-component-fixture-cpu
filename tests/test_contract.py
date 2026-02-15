from __future__ import annotations

from dataclasses import dataclass

from lucid_component_fixture_cpu.component import FixtureCpuComponent


@dataclass
class DummyCfg:
    pass


class DummyMQTT:
    def publish(self, topic: str, payload, *, qos: int = 0, retain: bool = False) -> None:
        assert isinstance(topic, str) and topic
        assert payload is not None


class DummyCtx:
    def __init__(self):
        from lucid_component_base import ComponentContext
        self._ctx = ComponentContext.create(
            agent_id="test",
            base_topic="lucid/agents/test",
            component_id="fixture_cpu",
            mqtt=DummyMQTT(),
            config=DummyCfg(),
        )

    def __getattr__(self, name):
        return getattr(self._ctx, name)


def test_start_stop_idempotent():
    c = FixtureCpuComponent(DummyCtx())  # type: ignore[arg-type]
    c.start()
    c.start()
    c.stop()
    c.stop()
