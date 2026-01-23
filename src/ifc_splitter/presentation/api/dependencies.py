from functools import lru_cache
from ifc_splitter.presentation.api.jobs import JobManager
import os

@lru_cache()
def get_job_manager() -> JobManager:
    # Use /data for persistent storage on Render (mounted disk)
    # Falls back to ./data for local development
    if os.path.exists("/data"):
        base_dir = "/data"
    else:
        base_dir = os.path.join(os.getcwd(), "data")
    
    upload_dir = os.path.join(base_dir, "uploads")
    output_dir = os.path.join(base_dir, "processed")
    
    return JobManager(upload_dir, output_dir)
