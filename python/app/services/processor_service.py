from pathlib import Path
from typing import Optional, Dict, Any
import logging
import tempfile
import shutil
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import Settings
from app.core.exceptions import ProcessingError, ValidationError
from app.services.job_service import JobService

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from processor import TinfoilProcessor
from cog_loader import CogRegistry, build_pipeline

class ProcessorService:
    def __init__(self, settings: Settings, logger: logging.Logger, job_service: JobService):
        self.settings = settings
        self.logger = logger
        self.job_service = job_service
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def _validate_file_path(self, path: str) -> bool:
        if not path or len(path) > 4096:
            return False
        if '..' in path:
            return False
        return True
    
    def _validate_audio_file(self, path: Path) -> bool:
        if not path.exists():
            return False
        if not path.is_file():
            return False
        if path.suffix.lower() not in self.settings.SUPPORTED_AUDIO_FORMATS:
            return False
        return True
    
    def create_job(self, input_path: Optional[str] = None, output_path: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> str:
        if input_path and not self._validate_file_path(input_path):
            raise ValidationError("Invalid input path")
        if output_path and not self._validate_file_path(output_path):
            raise ValidationError("Invalid output path")
        
        return self.job_service.create_job(
            input_path=input_path,
            output_path=output_path,
            options=options
        )
    
    async def process_file(self, job_id: str, file_path: Path, output_dir: Path, options: Dict[str, Any]):
        str_path = str(file_path)
        
        self.job_service.update_file_progress(job_id, str_path, 0.1, "processing")
        self.job_service.update_job_progress(job_id, 0.1, "processing")
        
        if not self._validate_audio_file(file_path):
            self.job_service.update_file_progress(job_id, str_path, 1.0, "failed", "Invalid audio file")
            return False
        
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            self.executor,
            self._process_file_sync,
            job_id,
            file_path,
            output_dir,
            options
        )
        
        return success
    
    def _process_file_sync(self, job_id: str, file_path: Path, output_dir: Path, options: Dict[str, Any]) -> bool:
        str_path = str(file_path)
        
        force_update = options.get('force_update', False)
        output_pattern = options.get('output_pattern') or self.settings.DEFAULT_OUTPUT_PATTERN
        selected_cogs = options.get('selected_cogs')
        
        processor = TinfoilProcessor(
            api_key=self.settings.ACOUSTID_API_KEY,
            fpcalc_path=self.settings.get_fpcalc_path(),
            output_pattern=output_pattern,
            logger=self.logger
        )
        
        if selected_cogs:
            cog_registry = CogRegistry(logger=self.logger)
            custom_cogs = build_pipeline(cog_registry, selected_cogs)
            if custom_cogs:
                processor.cogs = custom_cogs
        
        self.job_service.update_file_progress(job_id, str_path, 0.3, "processing")
        
        success = processor.process_file(file_path, output_dir, force_update)
        
        if success:
            self.job_service.update_file_progress(job_id, str_path, 1.0, "completed")
        else:
            self.job_service.update_file_progress(job_id, str_path, 1.0, "failed", "Processing failed")
        
        return success
    
    async def process_directory(self, job_id: str, input_dir: Path, output_dir: Path, options: Dict[str, Any]):
        self.job_service.update_job_progress(job_id, 0.1, "processing")
        
        if not input_dir.exists() or not input_dir.is_dir():
            self.job_service.set_job_error(job_id, "Input directory not found")
            return
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._process_directory_sync,
            job_id,
            input_dir,
            output_dir,
            options
        )
    
    def _process_directory_sync(self, job_id: str, input_dir: Path, output_dir: Path, options: Dict[str, Any]):
        force_update = options.get('force_update', False)
        output_pattern = options.get('output_pattern') or self.settings.DEFAULT_OUTPUT_PATTERN
        selected_cogs = options.get('selected_cogs')
        tag_fallback = options.get('tag_fallback', True)
        
        processor = TinfoilProcessor(
            api_key=self.settings.ACOUSTID_API_KEY,
            fpcalc_path=self.settings.get_fpcalc_path(),
            output_pattern=output_pattern,
            logger=self.logger
        )
        
        if not tag_fallback:
            processor.cogs = [cog for cog in processor.cogs 
                             if cog.__class__.__name__ != 'TagBasedMatchCog']
        
        if selected_cogs:
            cog_registry = CogRegistry(logger=self.logger)
            custom_cogs = build_pipeline(cog_registry, selected_cogs)
            if custom_cogs:
                processor.cogs = custom_cogs
        
        self.job_service.update_job_progress(job_id, 0.2, "processing")
        
        audio_files = self._get_audio_files(input_dir)
        total_files = len(audio_files)
        
        if total_files == 0:
            self.job_service.set_job_error(job_id, "No audio files found")
            return
        
        for file_path in audio_files:
            str_path = str(file_path)
            self.job_service.update_file_progress(job_id, str_path, 0.0, "pending")
        
        processed_count = 0
        
        for i, file_path in enumerate(audio_files):
            str_path = str(file_path)
            
            self.job_service.update_file_progress(job_id, str_path, 0.1, "processing")
            
            success = processor.process_file(file_path, output_dir, force_update)
            
            if success:
                self.job_service.update_file_progress(job_id, str_path, 1.0, "completed")
                processed_count += 1
            else:
                self.job_service.update_file_progress(job_id, str_path, 1.0, "failed", "Processing failed")
            
            progress = (i + 1) / total_files
            self.job_service.update_job_progress(job_id, progress, "processing")
        
        result = {
            "total_files": total_files,
            "processed_files": processed_count,
            "failed_files": total_files - processed_count
        }
        
        self.job_service.set_job_result(job_id, result)
    
    def _get_audio_files(self, directory: Path) -> list:
        audio_files = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.settings.SUPPORTED_AUDIO_FORMATS:
                audio_files.append(file_path)
        
        return audio_files