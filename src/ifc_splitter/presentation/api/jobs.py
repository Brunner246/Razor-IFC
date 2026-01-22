import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
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

        self.executor = self._create_executor()
        self.job_timeout = int(os.getenv("JOB_TIMEOUT_SECONDS", "300"))  # 5 min default

    def _create_executor(self):
        mw_env = os.getenv("MAX_WORKERS")
        max_workers = int(mw_env) if mw_env else 1
        logger.info(f"Starting ThreadPoolExecutor with max_workers={max_workers}")
        return ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ifc_worker")

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
        logger.info(f"Submitting job {job_id} for processing")

        try:
            future = self.executor.submit(
                process_file_task,
                job.input_path,
                job.output_path,
                guids,
                ifc_types,
                storeys
            )

            # Attach a callback to handle completion/failure
            future.add_done_callback(lambda f: self._on_job_complete(job_id, f))
        except Exception as e:
            logger.error(f"Failed to submit job {job_id}: {e}", exc_info=True)
            job.status = JobStatus.FAILED
            job.error = f"Failed to submit job: {str(e)}"

    def _restart_executor(self):
        """Restart the executor if it becomes unhealthy"""
        try:
            self.executor.shutdown(wait=False, cancel_futures=True)
        except Exception as e:
            logger.warning(f"Executor shutdown error: {e}")
        self.executor = self._create_executor()
        logger.info("Executor restarted successfully")

    def _on_job_complete(self, job_id: str, future):
        job = self.jobs.get(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found in completion callback")
            return

        try:
            # Wait for result with timeout
            future.result(timeout=self.job_timeout)
            job.status = JobStatus.COMPLETED
            logger.info(f"Job {job_id} completed successfully")
        except FuturesTimeoutError:
            job.status = JobStatus.FAILED
            job.error = f"Job timed out after {self.job_timeout} seconds"
            logger.error(f"Job {job_id} timed out")
        except MemoryError as e:
            job.status = JobStatus.FAILED
            job.error = "Out of memory - file may be too large for this server"
            logger.error(f"Job {job_id} failed with MemoryError: {e}")
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)


def process_file_task(input_path: str, output_path: str, guids: list[str], ifc_types: list[str], storeys: list[str]):
    """
    Process an IFC file in a worker thread.
    This runs with better error handling and logging.
    """
    import gc
    
    try:
        logger.info(f"Starting processing task for {input_path}")
        
        loader = IfcOpenShellLoader()
        saver = IfcOpenShellSaver()
        selector = IfcOpenShellSelector()
        pruner = IfcOpenShellPruner()

        use_case = SplitIfcFileUseCase(loader, saver, selector, pruner)

        criteria = FilterCriteria(guids=guids or [], ifc_types=ifc_types or [], storeys=storeys or [])
        command = SplitCommand(source_path=input_path, dest_path=output_path, criteria=criteria)

        use_case.execute(command)
        
        # Force garbage collection to free memory
        gc.collect()
        logger.info(f"Task completed successfully for {input_path}")
        
    except MemoryError as e:
        logger.error(f"Memory error processing {input_path}: {e}")
        gc.collect()  # Try to free memory
        raise MemoryError("Out of memory - file may be too large for this server") from e
    except Exception as e:
        logger.error(f"Error processing {input_path}: {e}", exc_info=True)
        gc.collect()  # Try to free memory
        raise
