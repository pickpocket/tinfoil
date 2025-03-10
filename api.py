"""
@file api.py
@brief REST API for the Tinfoil application.
"""
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
import os
import logging
import shutil
import tempfile
import traceback

from config import Config
from processor import TinfoilProcessor
from cog_loader import CogRegistry, build_pipeline


# Custom middleware to ensure CORS works
class CORSMiddlewareWithDebug(CORSMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        logger = logging.getLogger("cors-debug")
        logger.info(f"Processing request: {scope.get('path', 'unknown path')}")
        logger.info(f"Request headers: {scope.get('headers', [])}")
        
        return await super().__call__(scope, receive, send)


# Create FastAPI app
app = FastAPI(
    title="Tinfoil API", 
    description="REST API for Tinfoil FLAC audio fingerprinting and metadata management",
    version=Config.VERSION
)

# Add custom CORS middleware
app.add_middleware(
    CORSMiddlewareWithDebug,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"]  # Expose all headers
)

# Setup logging
logger = logging.getLogger("tinfoil-api")

# Models
class ProcessRequest(BaseModel):
    """Request model for processing files"""
    force_update: bool = False
    output_pattern: Optional[str] = None
    selected_cogs: Optional[List[str]] = None
    lyrics_source: str = "genius"

class CogInfo(BaseModel):
    """Information about a cog"""
    name: str
    input_tags: List[str]
    output_tags: List[str]
    description: Optional[str] = None

class JobStatus(BaseModel):
    """Status of a processing job"""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class PipelineRequest(BaseModel):
    """Request model for building a pipeline"""
    required_outputs: List[str]
    include_cogs: Optional[List[str]] = None
    exclude_cogs: Optional[List[str]] = None

# In-memory job storage
job_store = {}

# Dependency for adding CORS headers to every response
async def get_cors_headers(request: Request):
    # Get the origin from the request
    origin = request.headers.get("origin", "*")
    return {
        "access-control-allow-origin": origin,
        "access-control-allow-methods": "GET, POST, PUT, DELETE, OPTIONS",
        "access-control-allow-headers": "Content-Type, Authorization",
        "access-control-max-age": "86400",
    }

# Helper to create a JSONResponse with CORS headers
def create_cors_response(content, status_code=200, headers=None):
    all_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }
    if headers:
        all_headers.update(headers)
    return JSONResponse(content=content, status_code=status_code, headers=all_headers)

# API endpoints
@app.options("/{rest_of_path:path}")
async def options_route(rest_of_path: str):
    """Handle CORS preflight requests."""
    return create_cors_response({})

@app.post("/process", response_model=JobStatus)
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force_update: bool = Form(False),
    output_pattern: Optional[str] = Form(None),
    selected_cogs: Optional[str] = Form(None),
    lyrics_source: str = Form("genius")
):
    """Process a single audio file and return metadata."""
    try:
        job_id = str(uuid.uuid4())
        
        # Parse selected cogs
        cog_list = None
        if selected_cogs:
            cog_list = [cog.strip() for cog in selected_cogs.split(",")]
        
        # Save uploaded file to temporary location
        temp_dir = Path(tempfile.gettempdir()) / "tinfoil" / job_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Initialize job status
        job_store[job_id] = {
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None
        }
        
        # Process file in background
        background_tasks.add_task(
            process_file_task, 
            job_id, 
            file_path, 
            force_update,
            output_pattern,
            cog_list,
            lyrics_source
        )
        
        return JobStatus(job_id=job_id, status="pending")
    
    except Exception as e:
        logger.exception(f"Error in process_file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_file_task(
    job_id: str,
    file_path: Path,
    force_update: bool,
    output_pattern: Optional[str],
    selected_cogs: Optional[List[str]],
    lyrics_source: str
):
    """Background task to process a file."""
    try:
        # Update job status
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["progress"] = 0.1  # Show some initial progress
        
        logger.info(f"Processing file: {file_path}")
        
        # Build processor with selected cogs
        processor = TinfoilProcessor(
            api_key=Config.ACOUSTID_API_KEY,
            fpcalc_path=Config.get_fpcalc_path(),
            output_pattern=output_pattern or Config.DEFAULT_OUTPUT_PATTERN,
            logger=logger,
            lyrics_source=lyrics_source
        )
        
        job_store[job_id]["progress"] = 0.2  # Processor created
        
        if selected_cogs:
            # Build custom pipeline
            logger.info(f"Building custom pipeline with cogs: {selected_cogs}")
            cog_registry = CogRegistry(logger=logger)
            processor.cogs = build_pipeline(cog_registry, selected_cogs)
            
            if not processor.cogs:
                raise ValueError("Failed to build pipeline with selected cogs")
            
            logger.info(f"Custom pipeline built with {len(processor.cogs)} cogs")
        
        job_store[job_id]["progress"] = 0.3  # Pipeline built
        
        # Process the file
        output_dir = Config.get_default_output_dir() / job_id
        logger.info(f"Processing file to output directory: {output_dir}")
        
        success = processor.process_file(file_path, output_dir, force_update)
        
        job_store[job_id]["progress"] = 0.9  # Processing complete
        
        if success:
            # Get the output file path
            audio_files = list(output_dir.glob('**/*.flac'))
            output_file = str(audio_files[0]) if audio_files else None
            
            logger.info(f"Processing succeeded, output file: {output_file}")
            
            # Update job status
            job_store[job_id].update({
                "status": "completed",
                "progress": 1.0,
                "result": {
                    "success": True,
                    "output_path": output_file,
                    "output_dir": str(output_dir)
                }
            })
        else:
            logger.error(f"Processing failed for file: {file_path}")
            
            # Update job status
            job_store[job_id].update({
                "status": "failed",
                "progress": 1.0,
                "error": "Processing failed"
            })
        
    except Exception as e:
        logger.exception(f"Error processing file: {e}")
        job_store[job_id].update({
            "status": "failed",
            "progress": 1.0,
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a job."""
    try:
        if job_id not in job_store:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = job_store[job_id]
        
        # Create JobStatus model to validate and return
        status = JobStatus(
            job_id=job_id,
            status=job["status"],
            progress=job["progress"],
            result=job["result"],
            error=job.get("error")
        )
        
        # Return with CORS headers
        return status
        
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.exception(f"Error in get_job_status: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        raise

@app.get("/cogs", response_model=List[CogInfo])
async def list_cogs():
    """List all available cogs."""
    try:
        logger.info("Loading cogs for API request")
        cog_registry = CogRegistry(logger=logger)
        all_cogs = cog_registry.get_all_cogs()
        
        logger.info(f"Found {len(all_cogs)} cogs")
        
        cog_info_list = []
        for name, cog in all_cogs.items():
            # Get documentation if available
            doc = getattr(cog, "__doc__", "").strip() if hasattr(cog, "__doc__") else None
            
            # Get input/output tags, defaulting to empty lists
            input_tags = getattr(cog, "input_tags", [])
            output_tags = getattr(cog, "output_tags", [])
            
            # Create CogInfo instance
            cog_info = CogInfo(
                name=name,
                input_tags=input_tags,
                output_tags=output_tags,
                description=doc
            )
            
            cog_info_list.append(cog_info)
        
        return cog_info_list
        
    except Exception as e:
        logger.exception(f"Error in list_cogs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pipeline", response_model=List[str])
async def build_processing_pipeline(request: PipelineRequest):
    """Build an optimal processing pipeline for the required outputs."""
    try:
        cog_registry = CogRegistry(logger=logger)
        pipeline = cog_registry.build_pipeline_for_outputs(
            request.required_outputs,
            include_cogs=request.include_cogs,
            exclude_cogs=request.exclude_cogs
        )
        
        # Extract class names
        pipeline_names = [cog.__class__.__name__ for cog in pipeline]
        return pipeline_names
        
    except Exception as e:
        logger.exception(f"Error in build_processing_pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_config():
    """Get the current configuration."""
    try:
        config_data = {
            "app_name": Config.APP_NAME,
            "version": Config.VERSION,
            "default_output_pattern": Config.DEFAULT_OUTPUT_PATTERN,
            "supported_formats": Config.SUPPORTED_AUDIO_FORMATS,
            "fpcalc_path": Config.get_fpcalc_path(),
            "lyrics_sources": ["genius", "lrclib", "netease", "none"]
        }
        
        return config_data
        
    except Exception as e:
        logger.exception(f"Error in get_config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Handle 404 errors
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    return create_cors_response(
        {"detail": "The requested resource was not found"},
        status_code=404
    )

# Handle other exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return create_cors_response(
        {"detail": str(exc)},
        status_code=500
    )