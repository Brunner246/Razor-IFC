from dataclasses import dataclass
import re

@dataclass(frozen=True, eq=True, unsafe_hash=True)
class Guid:
    value: str

    def __post_init__(self):
        # Example validation for standard UUID or IFC GUID
        if not self.value:
            raise ValueError("GUID cannot be empty")
        # Add regex check if you want strict validation
    
    def __str__(self):
        return self.value

@dataclass
class IfcElement:
    guid: Guid
    type_name: str