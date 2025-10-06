import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=9211,
        log_level="info"
    )