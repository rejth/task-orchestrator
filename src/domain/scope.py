from dataclasses import dataclass


@dataclass(frozen=True)
class Scope:
    scope_id: str

    def get_id(self) -> str:
        return self.scope_id
