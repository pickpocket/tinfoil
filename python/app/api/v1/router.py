from fastapi import APIRouter
from app.api.v1.endpoints import processing, analysis, cogs, system

api_router = APIRouter()

api_router.include_router(processing.router)
api_router.include_router(analysis.router)
api_router.include_router(cogs.router)
api_router.include_router(system.router)