from lucid_component_base import Component


class ExampleComponent(Component):

    @property
    def component_id(self) -> str:
        return "example"

    def _start(self) -> None:
        # startup logic
        pass

    def _stop(self) -> None:
        # shutdown logic
        pass
