# lucid-component-fixture-cpu

LUCID fixture component that publishes CPU metrics for integration testing. Used by **lucid-agent-core** when loaded from the component registry.

---

## Purpose

Demonstrates the full LUCID component contract:

- **Retained:** metadata, status, state, cfg (nested telemetry config).
- **Stream:** logs (rate-limited, batched), telemetry for `cpu_percent` and `load` (gated by cfg).
- **Commands:** reset, ping, cfg/set → results on `evt/<action>/result`.

---

## Installation and build

Development (editable, from repo):

```bash
pip install -e .
```

Build for distribution:

```bash
pip install build
python -m build
```

Version comes from the git tag via [setuptools_scm](https://github.com/pypa/setuptools_scm). Do not set `version` in `pyproject.toml` manually.

---

## Configuration (cfg)

| Key | Description |
|-----|-------------|
| `cfg.telemetry.metrics` | Per-metric: `enabled`, `interval_s`, `change_threshold_percent` for `cpu_percent`, `load`. |
| `cfg.logs_enabled` | When true, component logs are streamed to the component `logs` topic (rate-limited, batched). |

---

## Entry point (agent-core discovery)

Registered under `lucid.components` so agent-core can load the component:

| Field | Value |
|-------|--------|
| **Entry point name** | `fixture_cpu` |
| **Module path** | `lucid_component_fixture_cpu.component:FixtureCpuComponent` |

---

## Dependencies

- **lucid-component-base** — component base class and context.
- **psutil** — CPU and load metrics.

---

## Relation to other packages

- **lucid-component-base** defines the component contract; this package implements it.
- **lucid-agent-core** discovers and runs this component when it is installed and enabled in the registry.
