# lucid-component-example

Template LUCID component. Replace this with your component name and description.

## Purpose

Example/stub component demonstrating the minimal structure required for a LUCID component. Use this repo as a template when creating new components.

## Configuration keys

None. This component has no configuration.

(When you add config, list keys here so operators know what to set.)

## MQTT topics used

None. This component does not publish or subscribe.

(When you add MQTT, list topics here, e.g. `{base_topic}/components/{component_id}/state`.)

## Versioning

Version is derived from Git tags via [setuptools_scm](https://github.com/pypa/setuptools_scm). Do not set `version` in `pyproject.toml` manually.

## Entry point name

Registered under the `lucid.components` entry point group for discovery by agent-core:

- **Entry point name:** `example`
- **Module path:** `lucid_component_example.component:ExampleComponent`

Ensure your component’s entry point name and class are consistent across all LUCID components.
