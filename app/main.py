from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import config
from app.auth import verify_token
from app.routes.hackrx_router import hackrx_router

app = FastAPI(
    title="LLM Query Engine",
    description="HackRx Document QA API",
    version="1.0.0"
)

# ✅ CORS settings for Streamlit or frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root endpoint (for browser visits)
@app.get("/")
def read_root():
    return {"message": "LLM Query Engine is running 🚀"}

# ✅ Health check
@app.get("/health")
def health_check():
    return {"status": "ok"}

# ✅ Include HackRx API routes
app.include_router(hackrx_router)
