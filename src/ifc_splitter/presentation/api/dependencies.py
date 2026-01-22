from functools import lru_cache
from ifc_splitter.presentation.api.jobs import JobManager
import os

@lru_cache()
def get_job_manager() -> JobManager:
    # Use current working directory / specific folder
    base_dir = os.getcwd()
    upload_dir = os.path.join(base_dir, "data", "uploads")
    output_dir = os.path.join(base_dir, "data", "processed")
    
    return JobManager(upload_dir, output_dir)
