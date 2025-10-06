from fastapi import APIRouter, HTTPException, Depends
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from cog_loader import CogRegistry
from app.schemas.responses import CogInfo

router = APIRouter(prefix="/cogs", tags=["cogs"])

@router.get("/list", response_model=list[CogInfo])
async def list_cogs():
    cog_registry = CogRegistry()
    all_cogs = cog_registry.get_all_cogs()
    
    cog_info_list = []
    for name, cog in all_cogs.items():
        doc = getattr(cog, "__doc__", "").strip() if hasattr(cog, "__doc__") else None
        input_tags = getattr(cog, "input_tags", [])
        output_tags = getattr(cog, "output_tags", [])
        
        cog_info = CogInfo(
            name=name,
            input_tags=input_tags,
            output_tags=output_tags,
            description=doc
        )
        cog_info_list.append(cog_info)
    
    return cog_info_list

@router.post("/pipeline")
async def build_pipeline(required_outputs: list[str], include_cogs: list[str] = None, exclude_cogs: list[str] = None):
    if len(required_outputs) > 50:
        raise HTTPException(status_code=400, detail="Too many required outputs")
    
    if include_cogs and len(include_cogs) > 50:
        raise HTTPException(status_code=400, detail="Too many cogs to include")
    
    if exclude_cogs and len(exclude_cogs) > 50:
        raise HTTPException(status_code=400, detail="Too many cogs to exclude")
    
    cog_registry = CogRegistry()
    pipeline = cog_registry.build_pipeline_for_outputs(
        required_outputs,
        include_cogs=include_cogs,
        exclude_cogs=exclude_cogs
    )
    
    pipeline_names = [cog.__class__.__name__ for cog in pipeline]
    return {"pipeline": pipeline_names}