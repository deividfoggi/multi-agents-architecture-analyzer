import os
import time
import dotenv
import asyncio
import logging
import json
from typing import List, Union
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from prompt_processor import PromptProcessor

dotenv.load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Global processor instance
processor_instance = None

def validate_environment_variables():
    """
    Validate all required environment variables at startup.
    Raises ValueError with clear message if any variables are missing.
    """
    required_vars = {
        'AI_MODEL_NAME': os.getenv('AI_MODEL_NAME'),
        'AI_API_KEY': os.getenv('AI_API_KEY'),
        'AI_ENDPOINT': os.getenv('AI_ENDPOINT'),
        'API_VERSION': os.getenv('API_VERSION')
    }
    
    missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.critical(error_msg)
        logger.critical("Please ensure all required environment variables are set before starting the application.")
        raise ValueError(error_msg)
    
    logger.info("All required environment variables are present")
    return {var_name: var_value for var_name, var_value in required_vars.items()}

# Pydantic Models
class EvaluationRequest(BaseModel):
    """Request model for essay evaluation."""
    essay: str = Field(..., description="The essay text to evaluate", min_length=1)
    skills_list: List[str] = Field(..., description="List of skills to evaluate against", min_items=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "essay": "This is a sample essay about environmental conservation...",
                "skills_list": [
                    "Writing clarity and organization",
                    "Grammar and language usage", 
                    "Content depth and analysis"
                ]
            }
        }

class EvaluationResponse(BaseModel):
    """Response model for essay evaluation."""
    evaluation_result: str = Field(..., description="The detailed evaluation result from AI")
    status: str = Field(..., description="Processing status (success/error)")
    processing_time: float = Field(..., description="Time taken to process in seconds")
    timestamp: str = Field(..., description="ISO timestamp of evaluation")
    
class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str = "1.0.0"

class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str
    detail: str
    timestamp: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    global processor_instance
    
    # Startup
    logger.info("Starting Essay Evaluation API")
    try:
        env_vars = validate_environment_variables()
        
        # Initialize processor with validated environment variables
        processor_instance = PromptProcessor(
            deployment_name=env_vars['AI_MODEL_NAME'],
            api_key=env_vars['AI_API_KEY'],
            endpoint=env_vars['AI_ENDPOINT'],
            api_version=env_vars['API_VERSION']
        )
        logger.info(f"Initialized PromptProcessor with model: {env_vars['AI_MODEL_NAME']}")
        
    except Exception as e:
        logger.critical(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Essay Evaluation API")
    if processor_instance:
        try:
            await processor_instance.cleanup()
            logger.info("PromptProcessor cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Create FastAPI app with lifecycle management
app = FastAPI(
    title="Essay Evaluation API",
    description="AI-powered essay evaluation service using Semantic Kernel",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )

@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_essay(request: EvaluationRequest):
    """
    Evaluate an essay based on provided skills criteria.
    
    This endpoint processes the essay through the AI evaluation pipeline
    and returns detailed results with scoring and feedback.
    """
    start_time = time.time()
    
    try:
        if not processor_instance:
            raise HTTPException(
                status_code=500, 
                detail="Processor not initialized. Check server logs for startup errors."
            )
        
        logger.info(f"Processing evaluation request for essay of {len(request.essay)} characters with {len(request.skills_list)} skills")
        
        # Prepare payload in the same format as the original Service Bus message
        payload = {
            "essay": request.essay,
            "skills_list": request.skills_list
        }
        
        # Process using existing PromptProcessor logic
        # Handle potential uvloop conflicts
        try:
            evaluation_result = await processor_instance.process_payload(payload)
        except RuntimeError as e:
            if "event loop" in str(e).lower() or "uvloop" in str(e).lower() or "patch" in str(e).lower():
                # Event loop conflict detected, log and re-raise with better message
                logger.warning(f"Event loop conflict detected: {e}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Event loop conflict",
                        "detail": "Please restart the server with: uvicorn api:app --host 0.0.0.0 --port 8080 --loop asyncio",
                        "processing_time": round(time.time() - start_time, 3),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            else:
                raise
        
        processing_time = time.time() - start_time
        
        logger.info(f"Evaluation completed successfully in {processing_time:.2f} seconds")
        
        return EvaluationResponse(
            evaluation_result=str(evaluation_result),
            status="success",
            processing_time=round(processing_time, 3),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Evaluation failed: {str(e)}"
        logger.error(f"{error_msg} (processing time: {processing_time:.2f}s)")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Processing failed",
                "detail": str(e),
                "processing_time": round(processing_time, 3),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Essay Evaluation API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "evaluate": "/evaluate",
            "docs": "/docs"
        }
    }

# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return HTTPException(
        status_code=400,
        detail={
            "error": "Invalid input",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    logger.info(f"Starting server on {host}:{port}")
    logger.info("Using standard asyncio loop to avoid uvloop conflicts")
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level="info",
        loop="asyncio"  # Force standard asyncio instead of uvloop
    )