from pathlib import Path
from typing import Optional, Dict, Any, List
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
from cog_loader import CogRegistry
from base_cog import BaseCog
from cogs.tag_based_match_cog import TagBasedMatchCog

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
    
    def _build_cog_pipeline(self, selected_cogs: Optional[List[str]] = None) -> List[BaseCog]:
        cog_registry = CogRegistry(logger=self.logger)
        cog_registry.load_cogs()

        pipeline = []
        
        cog_names_to_load = selected_cogs
        if not cog_names_to_load:
            cog_names_to_load = [
                'AcoustIDCog',
                'TagBasedMatchCog',
                'MusicBrainzCog',
                'CoverArtCog',
                'LrclibLyricsCog',
                'NeteaseLyricsCog',
                'GeniusLyricsCog'
            ]
            self.logger.info("No cogs selected, using default pipeline.")

        self.logger.info(f"Building pipeline with cogs: {cog_names_to_load}")
        for cog_name in cog_names_to_load:
            cog_class = cog_registry.get_cog_by_name(cog_name)
            if not cog_class:
                self.logger.warning(f"Cog '{cog_name}' not found, skipping.")
                continue

            try:
                # Build the arguments for the cog's constructor
                init_kwargs = {'logger': self.logger}
                is_configurable = True
                
                required_settings = getattr(cog_class, 'required_settings', [])
                for setting in required_settings:
                    key_name = setting['name']
                    config_name = key_name.upper() # e.g., 'acoustid_api_key' -> 'ACOUSTID_API_KEY'
                    
                    if hasattr(self.settings, config_name) and getattr(self.settings, config_name):
                        init_kwargs[key_name] = getattr(self.settings, config_name)
                    else:
                        self.logger.warning(f"Required setting '{config_name}' not configured for cog '{cog_name}'. Skipping.")
                        is_configurable = False
                        break # Stop if any required setting is missing
                
                if not is_configurable:
                    continue

                # Special handling for fpcalc_path which isn't a user-set API key
                if cog_name == 'AcoustIDCog':
                    init_kwargs['fpcalc_path'] = self.settings.get_fpcalc_path()

                # Instantiate the cog with the dynamically built arguments
                instance = cog_class(**init_kwargs)
                pipeline.append(instance)
            except Exception as e:
                self.logger.error(f"Failed to instantiate cog '{cog_name}': {e}")
        
        return pipeline

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
        
        pipeline = self._build_cog_pipeline(selected_cogs)
        if not pipeline:
            self.job_service.update_file_progress(job_id, str_path, 1.0, "failed", "Could not build processing pipeline.")
            return False

        processor = TinfoilProcessor(
            pipeline=pipeline,
            output_pattern=output_pattern,
            logger=self.logger
        )
        
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
        
        pipeline = self._build_cog_pipeline(selected_cogs)
        if not pipeline:
            self.job_service.set_job_error(job_id, "Could not build processing pipeline.")
            return

        if not tag_fallback:
            pipeline = [cog for cog in pipeline if not isinstance(cog, TagBasedMatchCog)]
            self.logger.info("Tag-based fallback matching is disabled.")

        processor = TinfoilProcessor(
            pipeline=pipeline,
            output_pattern=output_pattern,
            logger=self.logger
        )
        
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