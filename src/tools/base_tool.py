"""Base class for all agent tools."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Every agent tool must inherit from this."""

    name: str = "base_tool"
    description: str = "Base tool interface"

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema(),
            },
        }

    def parameters_schema(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}
