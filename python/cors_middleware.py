"""
CORS middleware for the Tinfoil API.
This enables Electron to communicate with the Python API.
"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import logging

def configure_cors(app: FastAPI):
    """Configure CORS for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Setup CORS
    origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        # Electron app URLs
        "file://"
    ]
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
    
    logger = logging.getLogger("cors-config")
    logger.info(f"CORS configured with origins: {origins}")
    
    return app