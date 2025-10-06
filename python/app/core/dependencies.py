from functools import lru_cache
from app.core.config import get_settings, Settings
from app.services.job_service import JobService
from app.services.processor_service import ProcessorService
import logging

_job_service = None
_processor_service = None

def get_job_service() -> JobService:
    global _job_service
    if _job_service is None:
        _job_service = JobService()
    return _job_service

def get_processor_service() -> ProcessorService:
    global _processor_service
    if _processor_service is None:
        settings = get_settings()
        logger = logging.getLogger("processor_service")
        _processor_service = ProcessorService(settings, logger, get_job_service())
    return _processor_service