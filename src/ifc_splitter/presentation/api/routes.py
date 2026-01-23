from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional
import shutil
import json

from ifc_splitter.presentation.api.schemas import JobSubmitResponse, JobStatusResponse
from ifc_splitter.presentation.api.dependencies import get_job_manager
from ifc_splitter.presentation.api.jobs import JobManager, JobStatus

router = APIRouter()

@router.post("/process", response_model=JobSubmitResponse)
async def submit_processing_job(
    file: UploadFile = File(...),
    guids: Optional[str] = Form(None, description="Comma separated list of GUIDs"),
    ifc_types: Optional[str] = Form(None, description="Comma separated list of IfcTypes"),
    storeys: Optional[str] = Form(None, description="Comma separated list of Storey names"),
    callback_url: Optional[str] = Form(None, description="Webhook URL to notify when job completes"),
    job_manager: JobManager = Depends(get_job_manager)
):
    """
    Upload an IFC file and start a filtering job.
    Returns a Job ID to track progress.
    """
    job = job_manager.create_job(callback_url=callback_url)

    try:
        with open(job.input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")
    
    parsed_guids = [g.strip() for g in guids.split(",")] if guids else []
    parsed_types = [t.strip() for t in ifc_types.split(",")] if ifc_types else []
    parsed_storeys = [s.strip() for s in storeys.split(",")] if storeys else []

    job_manager.submit_processing(job.id, parsed_guids, parsed_types, parsed_storeys)
    
    return JobSubmitResponse(
        job_id=job.id,
        status=job.status.value,
        message="File uploaded and processing started."
    )

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, job_manager: JobManager = Depends(get_job_manager)):
    """
    Check the status of a job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        message="Processing..." if job.status == JobStatus.PROCESSING else "Completed" if job.status == JobStatus.COMPLETED else "Failed",
        error=job.error,
        output_file=job.output_path if job.status == JobStatus.COMPLETED else None
    )

@router.get("/jobs/{job_id}/download")
async def download_job_result(job_id: str, job_manager: JobManager = Depends(get_job_manager)):
    """
    Download the result of a completed job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job is not stable. Current status: {job.status}")
        
    return FileResponse(
        path=job.output_path,
        filename=f"filtered_{job_id}.ifc",
        media_type='application/x-step' # Standard MIME for IFC (STEP)
    )
