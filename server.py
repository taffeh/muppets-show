"""
The Muppet Show v3 — FastAPI web server.

Run locally:
  uvicorn server:app --reload --port 8080

Deploy to Cloud Run:
  gcloud run deploy muppets-show \
    --source . \
    --region europe-west2 \
    --project teletraan-one \
    --set-secrets GITHUB_TOKEN=github-token:latest \
    --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=teletraan-one,SHOW_LOCATION=London \
    --timeout 3600 \
    --allow-unauthenticated
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# ── Environment (mirrors muppets_chat_v3.py) ──────────────────────────────────
use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper() == "TRUE"
if not use_vertex:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
    os.environ["GOOGLE_API_KEY"] = (
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    )
    os.environ.pop("GEMINI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).parent / "muppets_agent_v4"))
from agent import run_show  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from sse_starlette.sse import EventSourceResponse  # noqa: E402

app = FastAPI(title="The Muppet Show")
app.mount("/static", StaticFiles(directory="static"), name="static")

_show_lock = asyncio.Lock()
_show_running = False


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/show/status")
async def show_status():
    return {"running": _show_running}


@app.get("/show/stream")
async def stream_show(request: Request):
    async def generate():
        global _show_running

        if _show_running:
            yield {
                "event": "busy",
                "data": json.dumps(
                    {"text": "A show is already running — please wait for it to finish."}
                ),
            }
            return

        async with _show_lock:
            _show_running = True
            try:
                yield {"event": "start", "data": json.dumps({"text": ""})}
                async for section in run_show():
                    if await request.is_disconnected():
                        break
                    yield {"event": "section", "data": json.dumps({"text": section})}
                yield {"event": "end", "data": json.dumps({"text": ""})}
            except Exception as exc:
                yield {"event": "error", "data": json.dumps({"text": str(exc)})}
            finally:
                _show_running = False

    # ping=20 sends a keepalive comment every 20s — prevents Cloud Run / proxies
    # from closing the SSE connection during long agent waits
    return EventSourceResponse(generate(), ping=20)
