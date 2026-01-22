from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class FilterConfig(BaseModel):
    guids: Optional[List[str]] = Field(default=None, description="List of GlobalIds to keep")
    ifc_types: Optional[List[str]] = Field(default=None, description="List of IfcTypes to keep")
    storeys: Optional[List[str]] = Field(default=None, description="List of Storey names to keep")

class JobSubmitResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None
    input_file: Optional[str] = None
    output_file: Optional[str] = None
    error: Optional[str] = None
