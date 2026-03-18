"""Schemas shared across MCP tools."""

from dataclasses import asdict, dataclass, field
from typing import Dict, List


@dataclass
class MCPToolResponse:
    status: str
    payload: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

