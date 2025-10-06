from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from logging.handlers import RotatingFileHandler

from app.core.config import get_settings
from app.core.exceptions import TinfoilException
from app.api.v1.router import api_router

settings = get_settings()

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(settings.LOG_FORMAT)
    )
    logger.addHandler(console_handler)
    
    log_dir = settings.get_log_dir()
    file_handler = RotatingFileHandler(
        log_dir / 'tinfoil.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setFormatter(
        logging.Formatter(settings.LOG_FORMAT)
    )
    logger.addHandler(file_handler)

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.exception_handler(TinfoilException)
async def tinfoil_exception_handler(request: Request, exc: TinfoilException):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level=settings.LOG_LEVEL.lower()
    )