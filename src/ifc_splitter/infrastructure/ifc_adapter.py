import logging
import os
from abc import ABC, abstractmethod
from typing import List, Any, Set

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.root

from ifc_splitter.core.models import Guid
from ifc_splitter.core.ports import IfcLoader, IfcSaver, IfcSelector, IfcPruner, FilterCriteria

logger = logging.getLogger(__name__)


class IfcOpenShellLoader(IfcLoader):
    def load(self, file_path: str) -> Any:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")
        logger.info(f"Loading file: {file_path}")
        return ifcopenshell.open(file_path)


class IfcOpenShellSaver(IfcSaver):
    def save(self, model: Any, file_path: str) -> None:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            raise FileNotFoundError(f"Output directory does not exist: {directory}")

        logger.info(f"Writing to file: {file_path}")
        model.write(file_path)

        if os.path.exists(file_path):
            logger.info(f"Successfully created file: {file_path}")
        else:
            logger.warning(f"Warning: File was not created at {file_path}")


class SelectionStrategy(ABC):
    @abstractmethod
    def select(self, model: Any) -> Set[Guid]:
        pass


class GuidSelectionStrategy(SelectionStrategy):
    def __init__(self, guids: List[str]):
        self.guids = set(Guid(value=guid) for guid in guids)

    def select(self, model: Any) -> Set[Guid]:
        return self.guids


class TypeSelectionStrategy(SelectionStrategy):
    def __init__(self, ifc_types: List[str]):
        self.ifc_types = ifc_types

    def select(self, model: Any) -> Set[Guid]:
        guids: Set[Guid] = set()
        for ifc_type in self.ifc_types:
            logger.info(f"Collecting elements of type {ifc_type}...")
            try:
                elements_by_type = model.by_type(ifc_type)
                count = 0
                for element in elements_by_type:
                    if hasattr(element, "GlobalId"):
                        guids.add(Guid(value=element.GlobalId))
                        count += 1
                logger.info(f"Added {count} elements from type {ifc_type}.")
            except Exception as e:
                logger.warning(f"Error querying type {ifc_type}: {e}")
        return guids


class StoreySelectionStrategy(SelectionStrategy):
    def __init__(self, storeys: List[str]):
        self.storeys = storeys

    def select(self, model: Any) -> Set[Guid]:
        guids: Set[Guid] = set()
        for storey_name in self.storeys:
            logger.info(f"Collecting elements for storey: {storey_name}...")
            # Find the storey(s) by name
            # Note: IfcBuildingStorey Name can be None, though unlikely in valid files
            storeys = (s for s in model.by_type("IfcBuildingStorey") if s.Name == storey_name)

            if not storeys:
                logger.warning(f"Storey not found: {storey_name}")
                continue

            count = 0
            for storey in storeys:
                # IfcRelContainedInSpatialStructure relationships
                # checking inverse attribute 'ContainsElements'
                # https://standards.buildingsmart.org/IFC/DEV/IFC4_2/FINAL/HTML/schema/ifcproductextension/lexical/ifcbuildingstorey.htm
                if not hasattr(storey, "ContainsElements"):
                    logger.warning(f"Storey {storey_name} has no ContainsElements relationship.")
                    continue
                for rel in storey.ContainsElements:
                    for element in rel.RelatedElements:
                        if not hasattr(element, "GlobalId"):
                            continue
                        guids.add(Guid(value=element.GlobalId))
                        count += 1
            logger.info(f"Added {count} elements from storey {storey_name}.")
        return guids


class IfcOpenShellSelector(IfcSelector):
    def select_elements(self, model: Any, criteria: FilterCriteria) -> Set[Guid]:
        strategies: List[SelectionStrategy] = []
        if criteria.guids:
            strategies.append(GuidSelectionStrategy(criteria.guids))
        if criteria.ifc_types:
            strategies.append(TypeSelectionStrategy(criteria.ifc_types))
        if criteria.storeys:
            strategies.append(StoreySelectionStrategy(criteria.storeys))

        keep_guids: Set[Guid] = set()
        for strategy in strategies:
            keep_guids.update(strategy.select(model))

        return keep_guids


class IfcOpenShellPruner(IfcPruner):

    def prune_model(self, model: Any, keep_guids: Set[Guid]) -> Any:
        # self._log_verification(model, keep_guids)

        elements = model.by_type("IfcElement")
        logger.info(f"Found {len(elements)} IfcElements in total.")

        to_remove = (e for e in elements if e.GlobalId not in keep_guids)  # entities
        self._remove_elements(model, list(to_remove))

        return model

    @staticmethod
    def _log_verification(model: Any, keep_guids: Set[Guid]) -> None:
        logger.info(f"Filtering model. Keeping {len(keep_guids)} GUIDs.")
        found = 0
        for guid in keep_guids:
            if model.by_guid(guid):
                found += 1

        logger.info(f"Verified {found}/{len(keep_guids)} provided GUIDs exist in the source file.")

    def _remove_elements(self, model: Any, elements: List[Any]) -> None:
        total = len(elements)
        logger.info(f"Removing {total} elements...")

        failed = 0
        for i, element in enumerate(elements):
            if not self._safe_remove(model, element):
                failed += 1

        if failed > 0:
            logger.warning(f"Failed to remove {failed} elements.")
        logger.info("Finished removing elements.")

    @staticmethod
    def _safe_remove(model: Any, element: Any) -> bool:

        if element.id() == 0:
            return False

        try:
            ifcopenshell.api.root.remove_product(model, product=element)
            return True
        except Exception as e:
            if not hasattr(element, "GlobalId"):
                logger.debug(f"Element has no GlobalId, cannot log GUID: {e}")
                return False
            guid = element.GlobalId
            logger.debug(f"ifcopenshell.api.root.remove_product failed for {guid}: {e}")
            try:
                if element.id() != 0:
                    model.remove(element)
                    return True
            except Exception as e:
                logger.debug(f"Failed to remove element {guid}: {e}")
        return False

    @staticmethod
    def _log_progress(current: int, total: int, failed: int) -> None:
        percent = (current / total) * 100
        logger.info(
            f"Progress: {current}/{total} ({percent:.1f}%) elements processed. (Failed/Already Removed: {failed})")
