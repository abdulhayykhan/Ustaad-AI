import asyncio
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agents import UstaadOrchestrator

app = FastAPI(title="Ustaad-AI Agentic Service Orchestrator API")

# Setup CORS to allow the Flet mobile/web frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global queue for streaming agent reasoning logs to the frontend via SSE.
# Note: For the hackathon prototype, a global queue is sufficient to show the traces.
global_trace_queue = asyncio.Queue()

class ServiceRequest(BaseModel):
    text: str

@app.post("/api/request")
async def handle_request(req: ServiceRequest):
    """
    Main endpoint for triggering the agent orchestrator with natural language.
    """
    orchestrator = UstaadOrchestrator(global_trace_queue)
    # Execute the end-to-end agentic workflow
    result = await orchestrator.run(req.text)
    return result

@app.get("/api/agent-traces")
async def stream_traces(request: Request):
    """
    Server-Sent Events (SSE) endpoint that streams the internal "AI Thinking" logs.
    Judges will use this to verify the Traceability requirement.
    """
    async def event_generator():
        while True:
            # Gracefully break if the frontend disconnects
            if await request.is_disconnected():
                break
            
            try:
                # Wait for the next log event from the orchestrator
                event = await global_trace_queue.get()
                # SSE format requires 'data: <json>\n\n'
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.CancelledError:
                break
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# For easy starting
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
