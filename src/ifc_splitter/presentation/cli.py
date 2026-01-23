import typer
import logging
import uvicorn
import os
import sys
from rich.logging import RichHandler
from typing import List
from ifc_splitter.infrastructure.ifc_adapter import IfcOpenShellLoader, IfcOpenShellSaver, IfcOpenShellSelector, IfcOpenShellPruner
from ifc_splitter.application.service import SplitIfcFileUseCase, SplitCommand
from ifc_splitter.core.ports import FilterCriteria

app = typer.Typer(help="IFC File Splitter CLI")

def setup_logging():
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)]
    )

@app.command()
def split(
    input_file: str = typer.Argument(..., help="Path to input IFC file"),
    output_file: str = typer.Argument(..., help="Path to output IFC file"),
    guids: List[str] = typer.Option(None, "--guid", "-g", help="GUIDs to keep. Can be used multiple times."),
    ifc_types: List[str] = typer.Option(None, "--type", "-t", help="IfcTypes to keep (e.g. IfcBeam, IfcWall). Can be used multiple times."),
    storeys: List[str] = typer.Option(None, "--storey", "-s", help="Storey names to keep (e.g. 'Level 1', 'Ground Floor'). Can be used multiple times."),
):
    """
    Create a new IFC file from an existing file by keeping only specified elements.
    """
    setup_logging()
    logger = logging.getLogger("ifc_splitter")

    # DI
    loader = IfcOpenShellLoader()
    saver = IfcOpenShellSaver()
    selector = IfcOpenShellSelector()
    pruner = IfcOpenShellPruner()
    
    use_case = SplitIfcFileUseCase(loader, saver, selector, pruner)
    
    try:
        criteria = FilterCriteria(guids=guids or [], ifc_types=ifc_types or [], storeys=storeys or [])
        command = SplitCommand(source_path=input_file, dest_path=output_file, criteria=criteria)
        use_case.execute(command)
    except Exception as e:
        logger.exception("An error occurred during execution.")
        raise typer.Exit(code=1)

@app.command()
def serve(
    host: str = typer.Option("localhost", help="Host to bind to."),
    port: int = typer.Option(8000, help="Port to bind to."),
    reload: bool = typer.Option(False, help="Enable auto-reload."),
    workers: int = typer.Option(1, help="Number of worker processes.")
):
    """
    Start the REST API server.
    """
    setup_logging()
    logger = logging.getLogger("ifc_splitter")
    
    # Ensure subprocesses can find the package
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    os.environ["PYTHONPATH"] = src_path + os.pathsep + os.environ.get("PYTHONPATH", "")

    logger.info(f"Starting Uvicorn server with {workers} worker(s)")
    logger.info(f"Host: {host}, Port: {port}, Reload: {reload}")
    
    # Use workers only if not in reload mode (reload requires single process)
    if reload:
        uvicorn.run("ifc_splitter.presentation.api.main:app", host=host, port=port, reload=True)
    else:
        uvicorn.run("ifc_splitter.presentation.api.main:app", host=host, port=port, workers=workers)

def main():
    app()

if __name__ == "__main__":
    main()
