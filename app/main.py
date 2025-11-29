import asyncio
import time
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from app.settings import settings
from app.types import QuizRequest
from app.solver import QuizSolver

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# In-memory store for request start times
request_timestamps = {}

@app.post("/quiz")
async def solve_quiz(request: QuizRequest):
    """Main endpoint for quiz solving"""
    
    # Validate secret using settings
    if not settings.validate_user_secret(request.email, request.secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret"
        )
    
    # Check if Gemini API key is configured
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_actual_gemini_api_key_here":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API key not configured. Please update the .env file."
        )
    
    # Store start time for timeout tracking
    start_time = time.time()
    request_timestamps[request.email] = start_time
    
    # Acknowledge immediately with 200
    response = JSONResponse(
        content={"status": "accepted", "message": "Quiz solving started"},
        status_code=status.HTTP_200_OK
    )
    
    # Start solving in background
    asyncio.create_task(
        solve_quiz_background(request, start_time)
    )
    
    return response

async def solve_quiz_background(request: QuizRequest, start_time: float):
    """Background task to solve the quiz chain"""
    try:
        solver = QuizSolver(request, start_time)
        await solver.solve_chain()
    except Exception as e:
        print(f"Error solving quiz for {request.email}: {str(e)}")
    finally:
        # Clean up
        if request.email in request_timestamps:
            del request_timestamps[request.email]

@app.get("/")
async def root():
    return {"message": "Quiz Solver API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "gemini_configured": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_actual_gemini_api_key_here"),
        "browser_ready": True,
        "timestamp": time.time()
    }
    return health_status

@app.get("/config")
async def show_config():
    """Show current configuration (without sensitive data)"""
    config = {
        "app_name": settings.APP_NAME,
        "debug": settings.DEBUG,
        "gemini_model_primary": settings.GEMINI_MODEL_PRIMARY,
        "browser_headless": settings.BROWSER_HEADLESS,
        "max_attempts": settings.MAX_ATTEMPTS,
        "total_timeout": settings.TOTAL_TIMEOUT,
        "registered_users": list(settings.VALID_SECRETS.keys())
    }
    return config