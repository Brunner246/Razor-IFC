import logging
import os
import uuid
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from ifc_splitter.application.service import SplitIfcFileUseCase, SplitCommand
from ifc_splitter.core.ports import FilterCriteria
from ifc_splitter.infrastructure.ifc_adapter import IfcOpenShellLoader, IfcOpenShellSaver, IfcOpenShellSelector, \
    IfcOpenShellPruner

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    status: JobStatus
    input_path: str
    output_path: str
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class JobManager:
    def __init__(self, upload_dir: str, output_dir: str):
        self.jobs: Dict[str, Job] = {}
        self.upload_dir = Path(upload_dir)
        self.output_dir = Path(output_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # ProcessPoolExecutor because IFC processing is CPU intensive and want to avoid GIL
        # If a worker crashes hard (e.g. segfault in C library), the executor might break.
        # We start with a reasonable number of workers.
        self.executor = ProcessPoolExecutor()

    def create_job(self) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            status=JobStatus.PENDING,
            input_path=str(self.upload_dir / f"{job_id}.ifc"),
            output_path=str(self.output_dir / f"{job_id}_filtered.ifc")
        )
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id, None)

    def cleanup_old_jobs(self, max_compound_seconds: int = 3600):
        """Removes jobs and files older than the specified duration (default 1 hour)."""
        now = datetime.now()
        threshold = now - timedelta(seconds=max_compound_seconds)

        jobs_to_remove = []

        for job_id, job in self.jobs.items():
            if job.created_at < threshold:
                jobs_to_remove.append(job_id)

                # Cleanup Files
                try:
                    if os.path.exists(job.input_path):
                        os.remove(job.input_path)
                    if os.path.exists(job.output_path):
                        os.remove(job.output_path)
                except Exception as e:
                    logger.error(f"Failed to delete files for job {job_id}: {e}")

        for job_id in jobs_to_remove:
            del self.jobs[job_id]

        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs.")

    def submit_processing(self, job_id: str, guids: list[str], ifc_types: list[str], storeys: list[str]):
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JobStatus.PROCESSING

        try:
            future = self.executor.submit(
                process_file_task,
                job.input_path,
                job.output_path,
                guids,
                ifc_types,
                storeys
            )

            # Attach a callback to handle competition/failure
            # Note: add_done_callback runs in the thread that waits for the future, usually the main thread or a helper thread.
            future.add_done_callback(lambda f: self._on_job_complete(job_id, f))
        except Exception as e:
            # Check for BrokenProcessPool specifically if needed, or catch all submit errors
            logger.error(f"Failed to submit job {job_id}: {e}")
            job.status = JobStatus.FAILED
            job.error = f"System Error: {str(e)}"

            # If the pool is broken, we might need to restart it
            if "broken" in str(e).lower() or "terminated" in str(e).lower():
                logger.critical("ProcessPoolExecutor is broken. Restarting executor service...")
                self._restart_executor()
                # Retry submission once
                self.submit_processing(job_id, guids, ifc_types, storeys)

    def _restart_executor(self):
        try:
            self.executor.shutdown(wait=False)
        except RuntimeError as e:
            logger.warning(f"Executor shutdown error: {e}")
        self.executor = ProcessPoolExecutor()

    def _on_job_complete(self, job_id: str, future):
        job = self.jobs.get(job_id)
        if not job:
            return

        try:
            future.result()  # Will raise exception if task failed
            job.status = JobStatus.COMPLETED
            logger.info(f"Job {job_id} completed successfully.")
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            logger.error(f"Job {job_id} failed: {e}")


def process_file_task(input_path: str, output_path: str, guids: list[str], ifc_types: list[str], storeys: list[str]):
    loader = IfcOpenShellLoader()
    saver = IfcOpenShellSaver()
    selector = IfcOpenShellSelector()
    pruner = IfcOpenShellPruner()

    use_case = SplitIfcFileUseCase(loader, saver, selector, pruner)

    criteria = FilterCriteria(guids=guids or [], ifc_types=ifc_types or [], storeys=storeys or [])
    command = SplitCommand(source_path=input_path, dest_path=output_path, criteria=criteria)

    use_case.execute(command)
