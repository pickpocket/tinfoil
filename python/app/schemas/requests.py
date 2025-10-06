from pydantic import BaseModel, Field, validator
from typing import Optional

class ProcessFileRequest(BaseModel):
    force_update: bool = False
    output_pattern: Optional[str] = None
    selected_cogs: Optional[list[str]] = Field(default=None, max_items=50)
    
    @validator('output_pattern')
    def validate_output_pattern(cls, v):
        if v is None:
            return v
        if '..' in v or v.startswith('/') or '\\' in v:
            raise ValueError('Invalid output pattern')
        if len(v) > 500:
            raise ValueError('Output pattern too long')
        return v
    
    @validator('selected_cogs')
    def validate_cogs(cls, v):
        if v is None:
            return v
        for cog in v:
            if not isinstance(cog, str) or len(cog) > 100:
                raise ValueError('Invalid cog name')
        return v

class ProcessDirectoryRequest(BaseModel):
    input_path: str = Field(..., min_length=1, max_length=4096)
    output_path: str = Field(..., min_length=1, max_length=4096)
    force_update: bool = False
    output_pattern: Optional[str] = None
    tag_fallback: bool = True
    api_key: Optional[str] = Field(default=None, max_length=100)
    selected_cogs: Optional[list[str]] = Field(default=None, max_items=50)
    
    @validator('input_path', 'output_path')
    def validate_paths(cls, v):
        if '..' in v:
            raise ValueError('Path traversal not allowed')
        return v