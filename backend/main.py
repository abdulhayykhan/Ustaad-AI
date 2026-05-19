import asyncio
import json
import os
from contextlib import suppress
from typing import Set
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agents import UstaadOrchestrator
from backend.database import engine, Base
from backend.models import Provider

app = FastAPI(title="Ustaad-AI Agentic Service Orchestrator API")


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on app startup."""
    Base.metadata.create_all(bind=engine)


def _cors_origins() -> list[str]:
    raw_origins = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8550,http://127.0.0.1:8550",
    )
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["http://localhost:8550"]

# Setup CORS to allow the Flet mobile/web frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TraceBroadcaster:
    """Fan-out publisher for per-client SSE queues."""

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def publish(self, event: dict):
        async with self._lock:
            subscribers = list(self._subscribers)

        for queue in subscribers:
            with suppress(asyncio.QueueFull):
                queue.put_nowait(event)

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        async with self._lock:
            self._subscribers.discard(queue)


trace_broadcaster = TraceBroadcaster()

class ServiceRequest(BaseModel):
    text: str

@app.post("/api/request")
async def handle_request(req: ServiceRequest):
    """
    Main endpoint for triggering the agent orchestrator with natural language.
    """
    orchestrator = UstaadOrchestrator(trace_broadcaster.publish)
    # Execute the end-to-end agentic workflow
    result = await orchestrator.run(req.text)
    return result

@app.get("/api/agent-traces")
async def stream_traces(request: Request):
    """
    Server-Sent Events (SSE) endpoint that streams the internal "AI Thinking" logs.
    Judges will use this to verify the Traceability requirement.
    """
    subscriber_queue = await trace_broadcaster.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(subscriber_queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # SSE comment line to keep long-lived connections open.
                    yield ": keep-alive\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            await trace_broadcaster.unsubscribe(subscriber_queue)
                
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# For easy starting
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
