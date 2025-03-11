"""
@file api.py
@brief REST API for the Tinfoil application.
"""
from cors_middleware import configure_cors
import os
from pathlib import Path
import json
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, Response
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
app = configure_cors(app)

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

class FileProgress(BaseModel):
    """Progress information for a specific file"""
    progress: float = 0.0
    status: str = "pending"  # "pending", "processing", "completed", "failed"
    error: Optional[str] = None

class JobStatus(BaseModel):
    """Status of a processing job"""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    file_progress: Optional[Dict[str, FileProgress]] = None

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

@app.get("/analyze_file")
async def analyze_file(file_path: str):
    """Analyze a FLAC file and return its metadata."""
    try:
        from mutagen.flac import FLAC
        
        logger.info(f"Analyzing file: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # Load the FLAC file
        audio = FLAC(file_path)
        
        # Extract metadata
        metadata = {}
        for key, value in audio.items():
            # Mutagen returns lists for tag values
            metadata[key.lower()] = value[0] if len(value) == 1 else value
        
        # Check for cover art
        metadata['has_cover_art'] = len(audio.pictures) > 0
        
        # Return the metadata
        return metadata
    
    except Exception as e:
        logger.exception(f"Error analyzing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_cover_art")
async def get_cover_art(file_path: str):
    """Extract and return cover art from a FLAC file."""
    try:
        from mutagen.flac import FLAC
        
        logger.info(f"Extracting cover art from: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # Load the FLAC file
        audio = FLAC(file_path)
        
        # Check if cover art exists
        if not audio.pictures:
            raise HTTPException(status_code=404, detail="No cover art found")
        
        # Get the first picture (usually the cover art)
        picture = audio.pictures[0]
        
        # Return the picture data with appropriate content type
        return Response(
            content=picture.data,
            media_type=picture.mime,
            headers={
                "Content-Disposition": f"inline; filename=cover.{picture.mime.split('/')[-1]}",
                "Cache-Control": "max-age=3600",
                "Access-Control-Allow-Origin": "*"
            }
        )
    
    except Exception as e:
        logger.exception(f"Error extracting cover art: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # Initialize job status with file progress
        job_store[job_id] = {
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None,
            "file_progress": {
                str(file_path): {
                    "progress": 0.0,
                    "status": "pending",
                    "error": None
                }
            }
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
        
        return JobStatus(
            job_id=job_id, 
            status="pending",
            file_progress=job_store[job_id]["file_progress"]
        )
    
    except Exception as e:
        logger.exception(f"Error in process_file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process_directory")
async def process_directory(
    background_tasks: BackgroundTasks,
    request: Request
):
    """Process a directory of audio files with selected cogs."""
    try:
        job_id = str(uuid.uuid4())
        
        # Parse request body
        body = await request.json()
        input_path = body.get('input_path')
        output_path = body.get('output_path')
        force_update = body.get('force_update', False)
        output_pattern = body.get('output_pattern')
        lyrics_source = body.get('lyrics_source', 'genius')
        tag_fallback = body.get('tag_fallback', True)
        api_key = body.get('api_key')
        selected_cogs = body.get('selected_cogs')
        
        # Parse selected cogs
        cog_list = None
        if selected_cogs:
            if isinstance(selected_cogs, str):
                cog_list = [cog.strip() for cog in selected_cogs.split(",")]
            elif isinstance(selected_cogs, list):
                cog_list = selected_cogs
        
        # Validate required parameters
        if not input_path or not output_path:
            raise HTTPException(
                status_code=400,
                detail="input_path and output_path are required"
            )
        
        # Initialize job status
        job_store[job_id] = {
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None,
            "file_progress": {}  # Will be populated with files from the directory
        }
        
        # Process directory in background
        background_tasks.add_task(
            process_directory_task, 
            job_id, 
            input_path, 
            output_path,
            force_update,
            output_pattern,
            lyrics_source,
            tag_fallback,
            api_key,
            cog_list
        )
        
        return JobStatus(job_id=job_id, status="pending")
    
    except Exception as e:
        logger.exception(f"Error in process_directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_directory_task(
    job_id: str,
    input_path: str,
    output_path: str,
    force_update: bool,
    output_pattern: Optional[str],
    lyrics_source: str,
    tag_fallback: bool,
    api_key: Optional[str],
    selected_cogs: Optional[List[str]] = None
):
    """Background task to process a directory with custom cog selection and file progress tracking."""
    try:
        # Update job status
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["progress"] = 0.1  # Show some initial progress
        
        logger.info(f"Processing directory: {input_path}")
        
        # Build processor with options
        processor = TinfoilProcessor(
            api_key=api_key or Config.ACOUSTID_API_KEY,
            fpcalc_path=Config.get_fpcalc_path(),
            output_pattern=output_pattern or Config.DEFAULT_OUTPUT_PATTERN,
            logger=logger,
            lyrics_source=lyrics_source
        )
        
        # Configure tag-based fallback
        if not tag_fallback:
            processor.cogs = [cog for cog in processor.cogs 
                             if cog.__class__.__name__ != 'TagBasedMatchCog']
        
        # If selected cogs are provided, build custom pipeline
        if selected_cogs and len(selected_cogs) > 0:
            logger.info(f"Building custom pipeline with selected cogs: {selected_cogs}")
            cog_registry = CogRegistry(logger=logger)
            custom_cogs = build_pipeline(cog_registry, selected_cogs)
            
            if custom_cogs:
                processor.cogs = custom_cogs
                logger.info(f"Custom pipeline built with {len(custom_cogs)} cogs")
            else:
                logger.warning(f"Failed to build pipeline with selected cogs, using default")
        
        job_store[job_id]["progress"] = 0.2  # Processor created
        
        # Process the directory
        input_dir = Path(input_path)
        output_dir = Path(output_path)
        
        # Get all compatible audio files
        audio_files = processor._get_audio_files(input_dir)
        total_files = len(audio_files)
        processed_files = []
        
        logger.info(f"Found {total_files} compatible audio files in {input_dir}")
        
        # Initialize file progress tracking
        for file_path in audio_files:
            str_path = str(file_path)
            job_store[job_id]["file_progress"][str_path] = {
                "progress": 0.0,
                "status": "pending",
                "error": None
            }
        
        # Process each file with progress updates
        for i, file_path in enumerate(audio_files):
            str_path = str(file_path)
            try:
                # Update file status to processing
                job_store[job_id]["file_progress"][str_path]["status"] = "processing"
                job_store[job_id]["file_progress"][str_path]["progress"] = 0.1
                
                # Process the file
                success = processor.process_file(file_path, output_dir, force_update)
                
                if success:
                    processed_files.append(str_path)
                    job_store[job_id]["file_progress"][str_path]["status"] = "completed"
                    job_store[job_id]["file_progress"][str_path]["progress"] = 1.0
                else:
                    job_store[job_id]["file_progress"][str_path]["status"] = "failed"
                    job_store[job_id]["file_progress"][str_path]["error"] = "Processing failed"
                    job_store[job_id]["file_progress"][str_path]["progress"] = 1.0
                
                # Update overall progress based on files processed
                progress = 0.2 + (0.8 * (i + 1) / total_files)
                job_store[job_id]["progress"] = progress
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error processing file {file_path}: {error_msg}")
                job_store[job_id]["file_progress"][str_path]["status"] = "failed"
                job_store[job_id]["file_progress"][str_path]["error"] = error_msg
                job_store[job_id]["file_progress"][str_path]["progress"] = 1.0
        
        # Update job status
        job_store[job_id].update({
            "status": "completed",
            "progress": 1.0,
            "result": {
                "success": True,
                "processed_files": len(processed_files),
                "total_files": total_files,
                "output_dir": str(output_dir),
                "cogs_used": [cog.__class__.__name__ for cog in processor.cogs]
            }
        })
        
        logger.info(f"Successfully processed {len(processed_files)} of {total_files} files")
    
    except Exception as e:
        logger.exception(f"Error processing directory: {e}")
        job_store[job_id].update({
            "status": "failed",
            "progress": 1.0,
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.get("/validate_setup")
async def validate_setup(api_key: Optional[str] = None):
    """Validate the setup of the application."""
    try:
        # Create processor with the provided API key
        processor = TinfoilProcessor(
            api_key=api_key or Config.ACOUSTID_API_KEY,
            fpcalc_path=Config.get_fpcalc_path(),
            logger=logger
        )
        
        # Validate setup
        validations = processor.validate_setup()
        
        return {
            "valid": all(validations.values()),
            "validations": validations,
            "fpcalc_path": Config.get_fpcalc_path(),
            "api_key": "valid" if validations.get('api_key', False) else "invalid"
        }
        
    except Exception as e:
        logger.exception(f"Error validating setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
async def process_file_task(
    job_id: str,
    file_path: Path,
    force_update: bool,
    output_pattern: Optional[str],
    selected_cogs: Optional[List[str]],
    lyrics_source: str
):
    """Background task to process a file with progress tracking."""
    str_path = str(file_path)
    try:
        # Update job and file status
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["progress"] = 0.1
        job_store[job_id]["file_progress"][str_path]["status"] = "processing"
        job_store[job_id]["file_progress"][str_path]["progress"] = 0.1
        
        logger.info(f"Processing file: {file_path}")
        
        # Build processor with selected cogs
        processor = TinfoilProcessor(
            api_key=Config.ACOUSTID_API_KEY,
            fpcalc_path=Config.get_fpcalc_path(),
            output_pattern=output_pattern or Config.DEFAULT_OUTPUT_PATTERN,
            logger=logger,
            lyrics_source=lyrics_source
        )
        
        # Update progress
        job_store[job_id]["progress"] = 0.2
        job_store[job_id]["file_progress"][str_path]["progress"] = 0.2
        
        if selected_cogs:
            # Build custom pipeline
            logger.info(f"Building custom pipeline with cogs: {selected_cogs}")
            cog_registry = CogRegistry(logger=logger)
            processor.cogs = build_pipeline(cog_registry, selected_cogs)
            
            if not processor.cogs:
                raise ValueError("Failed to build pipeline with selected cogs")
            
            logger.info(f"Custom pipeline built with {len(processor.cogs)} cogs")
        
        # Update progress
        job_store[job_id]["progress"] = 0.3
        job_store[job_id]["file_progress"][str_path]["progress"] = 0.3
        
        # Process the file
        output_dir = Config.get_default_output_dir() / job_id
        logger.info(f"Processing file to output directory: {output_dir}")
        
        # Update progress before main processing
        job_store[job_id]["progress"] = 0.5
        job_store[job_id]["file_progress"][str_path]["progress"] = 0.5
        
        success = processor.process_file(file_path, output_dir, force_update)
        
        # Update progress after processing
        job_store[job_id]["progress"] = 0.9
        job_store[job_id]["file_progress"][str_path]["progress"] = 0.9
        
        if success:
            # Get the output file path
            audio_files = list(output_dir.glob('**/*.flac'))
            output_file = str(audio_files[0]) if audio_files else None
            
            logger.info(f"Processing succeeded, output file: {output_file}")
            
            # Update job and file status
            job_store[job_id].update({
                "status": "completed",
                "progress": 1.0,
                "result": {
                    "success": True,
                    "output_path": output_file,
                    "output_dir": str(output_dir),
                    "cogs_used": [cog.__class__.__name__ for cog in processor.cogs]
                }
            })
            job_store[job_id]["file_progress"][str_path]["status"] = "completed"
            job_store[job_id]["file_progress"][str_path]["progress"] = 1.0
        else:
            logger.error(f"Processing failed for file: {file_path}")
            
            # Update job and file status
            job_store[job_id].update({
                "status": "failed",
                "progress": 1.0,
                "error": "Processing failed"
            })
            job_store[job_id]["file_progress"][str_path]["status"] = "failed"
            job_store[job_id]["file_progress"][str_path]["progress"] = 1.0
            job_store[job_id]["file_progress"][str_path]["error"] = "Processing failed"
        
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Error processing file: {error_msg}")
        
        # Update job and file status
        job_store[job_id].update({
            "status": "failed",
            "progress": 1.0,
            "error": error_msg,
            "traceback": traceback.format_exc()
        })
        job_store[job_id]["file_progress"][str_path]["status"] = "failed"
        job_store[job_id]["file_progress"][str_path]["progress"] = 1.0
        job_store[job_id]["file_progress"][str_path]["error"] = error_msg

@app.get("/system_info")
async def get_system_info():
    """Get system information for the Electron app."""
    try:
        # Check for required dependencies
        fpcalc_path = Config.get_fpcalc_path()
        acoustid_key = Config.ACOUSTID_API_KEY
        
        # Check system paths
        app_dir = str(Config.get_app_dir())
        log_dir = str(Config.get_log_dir())
        output_dir = str(Config.get_default_output_dir())
        
        return {
            "fpcalc_installed": fpcalc_path is not None,
            "fpcalc_path": fpcalc_path or "Not found",
            "acoustid_key_configured": acoustid_key is not None and len(acoustid_key) > 0,
            "app_dir": app_dir,
            "log_dir": log_dir,
            "default_output_dir": output_dir,
            "system": os.name,
            "version": Config.VERSION,
        }
    except Exception as e:
        logger.exception(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/get_config")
async def get_config():
    """Get application configuration."""
    try:
        # Filter out sensitive information
        config_data = {
            "app_name": Config.APP_NAME,
            "version": Config.VERSION,
            "description": Config.DESCRIPTION,
            "default_output_pattern": Config.DEFAULT_OUTPUT_PATTERN,
            "supported_audio_formats": Config.SUPPORTED_AUDIO_FORMATS,
            "max_filename_length": Config.MAX_FILENAME_LENGTH,
        }
        
        # Include API key information if it exists (masked)
        if Config.ACOUSTID_API_KEY:
            masked_key = Config.ACOUSTID_API_KEY[:4] + "*" * (len(Config.ACOUSTID_API_KEY) - 8) + Config.ACOUSTID_API_KEY[-4:]
            config_data["acoustid_api_key_masked"] = masked_key
            config_data["has_api_key"] = True
        else:
            config_data["has_api_key"] = False
        
        return config_data
        
    except Exception as e:
        logger.exception(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save_config")
async def save_config(config_data: dict):
    """Save user configuration to a file."""
    try:
        # Get the config file path
        config_file = Config.get_app_dir() / "user_config.json"
        
        # Save the config
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)
        
        return {"success": True, "message": "Configuration saved successfully"}
    except Exception as e:
        logger.exception(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list_files")
async def list_files(directory: str):
    """List FLAC files in a directory."""
    try:
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Directory not found: {directory}")
        
        # Find all compatible audio files
        audio_files = []
        for file_path in dir_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in Config.SUPPORTED_AUDIO_FORMATS:
                # Get relative path
                rel_path = file_path.relative_to(dir_path)
                
                # Get file info
                size = file_path.stat().st_size
                # Format size
                size_str = ""
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                
                audio_files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "relative_path": str(rel_path),
                    "size": size,
                    "size_human": size_str
                })
        
        return {
            "directory": directory,
            "file_count": len(audio_files),
            "files": audio_files
        }
        
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.exception(f"Error listing files: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        raise
    
@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a job, including individual file progress."""
    try:
        if job_id not in job_store:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = job_store[job_id]
        
        # Convert file progress to proper model instances
        file_progress = {}
        if "file_progress" in job:
            for file_path, progress_data in job["file_progress"].items():
                file_progress[file_path] = FileProgress(
                    progress=progress_data.get("progress", 0.0),
                    status=progress_data.get("status", "pending"),
                    error=progress_data.get("error")
                )
        
        # Create JobStatus model to validate and return
        status = JobStatus(
            job_id=job_id,
            status=job["status"],
            progress=job["progress"],
            result=job["result"],
            error=job.get("error"),
            file_progress=file_progress
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

@app.post("/update_metadata")
async def update_metadata(request: Request):
    """Update metadata for a FLAC file."""
    try:
        from mutagen.flac import FLAC
        
        # Parse request body
        body = await request.json()
        file_path = body.get('file_path')
        metadata = body.get('metadata', {})
        
        # Validate request
        if not file_path:
            raise HTTPException(status_code=400, detail="file_path is required")
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        logger.info(f"Updating metadata for file: {file_path}")
        
        # Load the FLAC file
        audio = FLAC(file_path)
        
        # Store if file had cover art
        had_cover_art = len(audio.pictures) > 0
        
        # Clear existing metadata (except cover art)
        audio.clear()
        
        # Add new metadata
        for key, value in metadata.items():
            # Skip cover_art flag
            if key == 'has_cover_art':
                continue
                
            # Add tag if value is not empty
            if value is not None and value != "":
                audio[key] = str(value)
        
        # Save changes
        audio.save()
        
        logger.info(f"Metadata updated successfully for: {file_path}")
        
        return {
            "success": True,
            "message": "Metadata updated successfully",
            "file_path": file_path,
            "has_cover_art": had_cover_art
        }
        
    except Exception as e:
        logger.exception(f"Error updating metadata: {e}")
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