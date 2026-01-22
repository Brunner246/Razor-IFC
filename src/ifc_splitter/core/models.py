from dataclasses import dataclass

@dataclass(frozen=True, eq=True, unsafe_hash=True)
class Guid:
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("GUID cannot be empty")
    
    def __str__(self):
        return self.value

@dataclass
class IfcElement:
    guid: Guid
    type_name: str