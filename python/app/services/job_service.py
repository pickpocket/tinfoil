from typing import Dict, Optional
from datetime import datetime, timedelta
from app.models.job import Job
import asyncio
import logging

class JobService:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.logger = logging.getLogger("job_service")
        self._cleanup_task = None
    
    def create_job(self, **kwargs) -> str:
        job = Job(**kwargs)
        self.jobs[job.id] = job
        return job.id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)
    
    def update_job_progress(self, job_id: str, progress: float, status: str):
        job = self.jobs.get(job_id)
        if job:
            job.update_progress(progress, status)
    
    def set_job_error(self, job_id: str, error: str):
        job = self.jobs.get(job_id)
        if job:
            job.set_error(error)
    
    def set_job_result(self, job_id: str, result: Dict):
        job = self.jobs.get(job_id)
        if job:
            job.set_result(result)
    
    def update_file_progress(self, job_id: str, file_path: str, progress: float, status: str, error: Optional[str] = None):
        job = self.jobs.get(job_id)
        if job:
            job.update_file_progress(file_path, progress, status, error)
    
    def cleanup_old_jobs(self, max_age: timedelta = timedelta(hours=24)):
        now = datetime.utcnow()
        to_remove = [
            job_id for job_id, job in self.jobs.items()
            if now - job.updated_at > max_age
        ]
        for job_id in to_remove:
            del self.jobs[job_id]
        if len(to_remove) > 0:
            self.logger.info(f"Cleaned up {len(to_remove)} old jobs")