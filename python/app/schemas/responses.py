from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class FileProgress(BaseModel):
    progress: float = 0.0
    status: str = "pending"
    error: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    file_progress: Optional[Dict[str, FileProgress]] = None
    created_at: datetime
    updated_at: datetime

class CogSettingInfo(BaseModel):
    name: str
    label: str
    type: str = "text"
    is_configured: bool

class CogInfo(BaseModel):
    name: str
    input_tags: list[str]
    output_tags: list[str]
    description: Optional[str] = None
    settings: List[CogSettingInfo] = []

class SystemInfo(BaseModel):
    fpcalc_installed: bool
    fpcalc_path: Optional[str]
    acoustid_key_configured: bool
    app_dir: str
    log_dir: str
    default_output_dir: str
    system: str
    version: str

class HealthCheck(BaseModel):
    status: str
    version: str
    fpcalc_available: bool