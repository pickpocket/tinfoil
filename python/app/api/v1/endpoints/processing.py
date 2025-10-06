from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from pathlib import Path
import tempfile
import shutil
from typing import Optional

from app.core.dependencies import get_processor_service
from app.services.processor_service import ProcessorService
from app.schemas.requests import ProcessDirectoryRequest
from app.schemas.responses import JobStatusResponse
from app.core.config import get_settings

router = APIRouter(prefix="/process", tags=["processing"])

@router.post("/file", response_model=JobStatusResponse)
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force_update: bool = Form(False),
    output_pattern: Optional[str] = Form(None),
    selected_cogs: Optional[str] = Form(None),
    processor_service: ProcessorService = Depends(get_processor_service)
):
    settings = get_settings()
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.endswith('.flac'):
        raise HTTPException(status_code=400, detail="Only FLAC files are supported")
    
    if len(file.filename) > 255:
        raise HTTPException(status_code=400, detail="Filename too long")
    
    cog_list = None
    if selected_cogs:
        cog_list = [cog.strip() for cog in selected_cogs.split(",") if cog.strip()]
        if len(cog_list) > 50:
            raise HTTPException(status_code=400, detail="Too many cogs selected")
    
    temp_dir = Path(tempfile.gettempdir()) / "tinfoil" / "uploads"
    if not temp_dir.exists():
        temp_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = temp_dir / file.filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    output_dir = settings.get_default_output_dir()
    
    options = {
        'force_update': force_update,
        'output_pattern': output_pattern,
        'selected_cogs': cog_list
    }
    
    job_id = processor_service.create_job(
        input_path=str(file_path),
        output_path=str(output_dir),
        options=options
    )
    
    background_tasks.add_task(
        processor_service.process_file,
        job_id,
        file_path,
        output_dir,
        options
    )
    
    job = processor_service.job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to create job")
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        result=job.result,
        error=job.error,
        file_progress=job.file_progress,
        created_at=job.created_at,
        updated_at=job.updated_at
    )

@router.post("/directory", response_model=JobStatusResponse)
async def process_directory(
    request: ProcessDirectoryRequest,
    background_tasks: BackgroundTasks,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    input_dir = Path(request.input_path)
    output_dir = Path(request.output_path)
    
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail="Input directory not found")
    
    if not input_dir.is_dir():
        raise HTTPException(status_code=400, detail="Input path is not a directory")
    
    options = {
        'force_update': request.force_update,
        'output_pattern': request.output_pattern,
        'selected_cogs': request.selected_cogs,
        'tag_fallback': request.tag_fallback
    }
    
    job_id = processor_service.create_job(
        input_path=str(input_dir),
        output_path=str(output_dir),
        options=options
    )
    
    background_tasks.add_task(
        processor_service.process_directory,
        job_id,
        input_dir,
        output_dir,
        options
    )
    
    job = processor_service.job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to create job")
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        result=job.result,
        error=job.error,
        file_progress=job.file_progress,
        created_at=job.created_at,
        updated_at=job.updated_at
    )

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    if len(job_id) > 100:
        raise HTTPException(status_code=400, detail="Invalid job ID")
    
    job = processor_service.job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        result=job.result,
        error=job.error,
        file_progress=job.file_progress,
        created_at=job.created_at,
        updated_at=job.updated_at
    )