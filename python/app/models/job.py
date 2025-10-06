from datetime import datetime
from typing import Dict, Any, Optional
import uuid

class Job:
    def __init__(
        self,
        input_path: Optional[str] = None,
        output_path: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid.uuid4())
        self.status = "pending"
        self.progress = 0.0
        self.result = None
        self.error = None
        self.file_progress: Dict[str, Dict[str, Any]] = {}
        self.input_path = input_path
        self.output_path = output_path
        self.options = options or {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def update_progress(self, progress: float, status: str):
        self.progress = progress
        self.status = status
        self.updated_at = datetime.utcnow()
    
    def set_error(self, error: str):
        self.error = error
        self.status = "failed"
        self.progress = 1.0
        self.updated_at = datetime.utcnow()
    
    def set_result(self, result: Dict[str, Any]):
        self.result = result
        self.status = "completed"
        self.progress = 1.0
        self.updated_at = datetime.utcnow()
    
    def update_file_progress(self, file_path: str, progress: float, status: str, error: Optional[str] = None):
        self.file_progress[file_path] = {
            "progress": progress,
            "status": status,
            "error": error
        }
        self.updated_at = datetime.utcnow()