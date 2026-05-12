from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.core.bot import AIAgent
import uvicorn
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Web Chat")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent
logger.info("Initializing AIAgent...")
agent = AIAgent()
logger.info("AIAgent initialized successfully.")

# Request model
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    logger.info(f"Received message: {request.message}")
    try:
        # Use a more descriptive variable name
        response_text = agent.ask(request.message, session_id=request.session_id)
        logger.info("Agent response generated.")
        return {"response": response_text}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# Mount static files
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
