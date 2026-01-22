from abc import ABC, abstractmethod
from typing import List, Set, Any
from dataclasses import dataclass

@dataclass
class FilterCriteria:
    guids: List[str] = None
    ifc_types: List[str] = None
    storeys: List[str] = None

class IfcLoader(ABC):
    @abstractmethod
    def load(self, file_path: str) -> Any:
        """Load an IFC model from a file."""
        pass

class IfcSaver(ABC):
    @abstractmethod
    def save(self, model: Any, file_path: str) -> None:
        """Save an IFC model to a file."""
        pass

class IfcSelector(ABC):
    @abstractmethod
    def select_elements(self, model: Any, criteria: FilterCriteria) -> Set[str]:
        """
        Identify elements in the model based on criteria.
        Returns a set of GUIDs to keep.
        """
        pass

class IfcPruner(ABC):
    @abstractmethod
    def prune_model(self, model: Any, keep_guids: Set[str]) -> Any:
        """
        Remove everything from the model except the elements in keep_guids 
        and their required dependencies (Project structure, etc).
        """
        pass

