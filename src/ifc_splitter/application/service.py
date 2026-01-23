import logging
from dataclasses import dataclass

from ifc_splitter.core.ports import IfcLoader, IfcSaver, IfcSelector, IfcPruner, FilterCriteria

logger = logging.getLogger(__name__)


@dataclass
class SplitCommand:
    source_path: str
    dest_path: str
    criteria: FilterCriteria


class SplitIfcFileUseCase:
    def __init__(self, loader: IfcLoader, saver: IfcSaver, selector: IfcSelector, pruner: IfcPruner):
        self.loader = loader
        self.saver = saver
        self.selector = selector
        self.pruner = pruner

    def execute(self, command: SplitCommand) -> None:
        logger.info(f"Loading IFC file from: {command.source_path}")
        model = self.loader.load(command.source_path)

        logger.info(f"Selecting elements based on criteria: {command.criteria}")
        keep_guids = self.selector.select_elements(model, command.criteria)

        logger.info(f"Pruning model, keeping {len(keep_guids)} elements...")
        model = self.pruner.prune_model(model, keep_guids)

        logger.info(f"Saving filtered model to: {command.dest_path}")
        self.saver.save(model, command.dest_path)
        logger.info("Operation completed successfully.")
