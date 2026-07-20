# Preview-environment adapter.
# Production entrypoint is orchestrator/main.py (uvicorn orchestrator.main:app).
# This shim lets the platform supervisor (uvicorn server:app in /app/backend,
# port 8001) serve the same FastAPI orchestrator app.
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.main import app  # noqa: E402,F401
