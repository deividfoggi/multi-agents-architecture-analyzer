import os
import time
from dotenv import load_dotenv
import asyncio
import logging
import json
import base64
from typing import List, Union, Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from prompt_processor import PromptProcessor
from pdf_reader_plugin import PDFReaderPlugin

load_dotenv()

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
        'MODEL_DEPLOYMENT_NAME': os.getenv('MODEL_DEPLOYMENT_NAME'),
        'AI_API_KEY': os.getenv('AI_API_KEY'),
        'AI_ENDPOINT': os.getenv('AI_ENDPOINT'),
        'API_VERSION': os.getenv('API_VERSION')
    }
    
    # Optional Azure AI Foundry variables (for enhanced processing)
    optional_foundry_vars = {
        'AZURE_AI_PROJECT_ENDPOINT': os.getenv('AZURE_AI_PROJECT_ENDPOINT'),
        'ARCHITECTURE_EXTRACTOR_AGENT_ID': os.getenv('ARCHITECTURE_EXTRACTOR_AGENT_ID'),
        'AZURE_RESOURCES_SPECIALIST_AGENT_ID': os.getenv('AZURE_RESOURCES_SPECIALIST_AGENT_ID')
    }
    
    missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.critical(error_msg)
        logger.critical("Please ensure all required environment variables are set before starting the application.")
        raise ValueError(error_msg)
    
    logger.info("All required environment variables are present")
    
    # Check if Azure AI Foundry variables are available
    foundry_available = all(optional_foundry_vars.values())
    if foundry_available:
        logger.info("Azure AI Foundry variables detected - enhanced processing will be available")
    else:
        logger.info("Azure AI Foundry variables not found - using fallback processing only")
    
    # Combine all variables
    all_vars = {**required_vars, **optional_foundry_vars}
    all_vars['FOUNDRY_AVAILABLE'] = foundry_available
    
    return all_vars

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
    processing_type: str = Field(default="fallback", description="Type of processing used (foundry/fallback)")
    foundry_available: bool = Field(default=False, description="Whether Azure AI Foundry agents were available")

class DocumentAnalysisRequest(BaseModel):
    """Request model for document analysis."""
    document_text: str = Field(..., description="The document text to analyze", min_length=1)
    analysis_parameters: Dict[str, Any] = Field(default={}, description="Additional analysis parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_text": "This document describes a cloud architecture using Azure services...",
                "analysis_parameters": {
                    "focus_areas": ["architecture", "azure_resources"],
                    "detail_level": "comprehensive"
                }
            }
        }

class DocumentAnalysisResponse(BaseModel):
    """Response model for document analysis."""
    analysis_result: Dict[str, Any] = Field(..., description="The structured analysis result")
    status: str = Field(..., description="Processing status (success/error)")
    processing_time: float = Field(..., description="Time taken to process in seconds")
    timestamp: str = Field(..., description="ISO timestamp of analysis")
    processing_type: str = Field(..., description="Type of processing used (foundry/fallback)")
    foundry_available: bool = Field(..., description="Whether Azure AI Foundry agents were available")
    agents_used: List[str] = Field(default=[], description="List of agents used in processing")
    shared_thread_id: Optional[str] = Field(default=None, description="Thread ID for conversation continuity")
    
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
        
        # Initialize enhanced processor with validated environment variables
        processor_instance = PromptProcessor(
            deployment_name=env_vars['MODEL_DEPLOYMENT_NAME'],
            api_key=env_vars['AI_API_KEY'],
            endpoint=env_vars['AI_ENDPOINT'],
            project_endpoint=env_vars.get('AZURE_AI_PROJECT_ENDPOINT')
        )
        
        foundry_status = "with Azure AI Foundry integration" if env_vars.get('FOUNDRY_AVAILABLE') else "with fallback processing only"
        logger.info(f"Initialized EnhancedPromptProcessor {foundry_status} using model: {env_vars['MODEL_DEPLOYMENT_NAME']}")
        
    except Exception as e:
        logger.critical(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Essay Evaluation API")
    if processor_instance:
        try:
            # Enhanced processor doesn't require explicit cleanup like the old one
            logger.info("EnhancedPromptProcessor shutdown completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Create FastAPI app with lifecycle management
app = FastAPI(
    title="Enhanced Document Analysis API",
    description="AI-powered document analysis and essay evaluation service using Semantic Kernel and Azure AI Foundry agents",
    version="2.0.0",
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
        
        # Prepare payload for enhanced processor
        payload = {
            "essay_text": request.essay,
            "skills_list": request.skills_list,
            "type": "essay_evaluation"
        }
        
        # Process using EnhancedPromptProcessor
        try:
            evaluation_result = await processor_instance.process(payload)
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
        
        # Extract result information
        if isinstance(evaluation_result, dict):
            result_text = evaluation_result.get("result", str(evaluation_result))
            processing_type = evaluation_result.get("processing_type", "unknown")
            foundry_available = evaluation_result.get("foundry_available", False)
        else:
            result_text = str(evaluation_result)
            processing_type = "legacy"
            foundry_available = False
        
        logger.info(f"Evaluation completed successfully in {processing_time:.2f} seconds using {processing_type}")
        
        return EvaluationResponse(
            evaluation_result=result_text,
            status="success",
            processing_time=round(processing_time, 3),
            timestamp=datetime.utcnow().isoformat(),
            processing_type=processing_type,
            foundry_available=foundry_available
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

@app.post("/analyze-document", response_model=DocumentAnalysisResponse)
async def analyze_document(request: DocumentAnalysisRequest):
    """
    Analyze a document using Azure AI Foundry agents or fallback processing.
    
    This endpoint processes documents through the sequential workflow:
    1. Architecture Detail Extractor - identifies architectural patterns and components
    2. Azure Resources Specialist - analyzes Azure services and configurations
    """
    start_time = time.time()
    
    try:
        if not processor_instance:
            raise HTTPException(
                status_code=500,
                detail="Processor not initialized. Check server logs for startup errors."
            )
        
        logger.info(f"Processing document analysis request for {len(request.document_text)} characters")
        
        # Prepare payload for document analysis
        payload = {
            "document_text": request.document_text,
            "analysis_parameters": request.analysis_parameters,
            "type": "document_analysis"
        }
        
        # Process using EnhancedPromptProcessor
        try:
            analysis_result = await processor_instance.process_document_analysis(payload)
        except RuntimeError as e:
            if "event loop" in str(e).lower() or "uvloop" in str(e).lower():
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
        
        # Extract result information
        if isinstance(analysis_result, dict) and analysis_result.get("success"):
            result_data = analysis_result.get("result", {})
            processing_type = analysis_result.get("processing_type", "unknown")
            foundry_available = analysis_result.get("foundry_available", False)
            agents_used = analysis_result.get("agents_used", [])
            shared_thread_id = analysis_result.get("shared_thread_id")
            
            logger.info(f"Document analysis completed successfully in {processing_time:.2f} seconds using {processing_type}")
            
            return DocumentAnalysisResponse(
                analysis_result=result_data,
                status="success",
                processing_time=round(processing_time, 3),
                timestamp=datetime.utcnow().isoformat(),
                processing_type=processing_type,
                foundry_available=foundry_available,
                agents_used=agents_used,
                shared_thread_id=shared_thread_id
            )
        else:
            # Handle error case
            error_msg = analysis_result.get("error", "Unknown error") if isinstance(analysis_result, dict) else "Processing failed"
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Document analysis failed",
                    "detail": error_msg,
                    "processing_time": round(processing_time, 3),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Document analysis failed: {str(e)}"
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

@app.post("/analyze-pdf", response_model=DocumentAnalysisResponse)
async def analyze_pdf_document(
    file: UploadFile = File(..., description="PDF file to analyze"),
    analysis_parameters: str = Form(default="{}", description="JSON string of analysis parameters")
):
    """
    Analyze a PDF document using Azure AI Foundry agents with PDF text extraction.
    
    This endpoint:
    1. Extracts text from the uploaded PDF using the PDFReaderPlugin
    2. Processes the extracted text through the sequential workflow:
       - Architecture Detail Extractor - identifies architectural patterns and components
       - Azure Resources Specialist - analyzes Azure services and configurations
    """
    start_time = time.time()
    
    try:
        if not processor_instance:
            raise HTTPException(
                status_code=500,
                detail="Processor not initialized. Check server logs for startup errors."
            )
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        logger.info(f"Processing PDF analysis request for file: {file.filename}")
        
        # Read PDF file content
        pdf_content = await file.read()
        if not pdf_content:
            raise HTTPException(
                status_code=400,
                detail="Empty PDF file"
            )
        
        # Convert to base64 for the PDF reader plugin
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Extract text using PDFReaderPlugin
        pdf_reader = PDFReaderPlugin()
        extraction_result_json = pdf_reader.extract_pdf_from_base64(pdf_base64)
        extraction_result = json.loads(extraction_result_json)
        
        if "error" in extraction_result:
            raise HTTPException(
                status_code=400,
                detail=f"PDF text extraction failed: {extraction_result['error']}"
            )
        
        extracted_text = extraction_result.get("text_content", "")
        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No text content found in PDF file"
            )
        
        # Parse analysis parameters
        try:
            analysis_params = json.loads(analysis_parameters) if analysis_parameters else {}
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid analysis_parameters JSON format"
            )
        
        logger.info(f"Extracted {len(extracted_text)} characters from PDF ({extraction_result.get('page_count', 0)} pages)")
        
        # Prepare payload for document analysis with extracted text
        payload = {
            "document_text": extracted_text,
            "analysis_parameters": analysis_params,
            "type": "document_analysis",
            "source_file": file.filename,
            "extraction_metadata": {
                "page_count": extraction_result.get("page_count", 0),
                "file_size_bytes": extraction_result.get("file_size_bytes", 0),
                "extraction_method": extraction_result.get("extraction_method", "PyMuPDF")
            }
        }
        
        # Process using EnhancedPromptProcessor
        try:
            analysis_result = await processor_instance.process_document_analysis(payload)
        except RuntimeError as e:
            if "event loop" in str(e).lower() or "uvloop" in str(e).lower():
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
        
        # Extract result information
        if isinstance(analysis_result, dict) and analysis_result.get("success"):
            result_data = analysis_result.get("result", {})
            
            # Add PDF extraction metadata to the result
            if isinstance(result_data, dict):
                result_data["pdf_extraction_metadata"] = extraction_result
            
            processing_type = analysis_result.get("processing_type", "unknown")
            foundry_available = analysis_result.get("foundry_available", False)
            agents_used = analysis_result.get("agents_used", [])
            shared_thread_id = analysis_result.get("shared_thread_id")
            
            logger.info(f"PDF document analysis completed successfully in {processing_time:.2f} seconds using {processing_type}")
            
            return DocumentAnalysisResponse(
                analysis_result=result_data,
                status="success",
                processing_time=round(processing_time, 3),
                timestamp=datetime.utcnow().isoformat(),
                processing_type=processing_type,
                foundry_available=foundry_available,
                agents_used=agents_used,
                shared_thread_id=shared_thread_id
            )
        else:
            # Handle error case
            error_msg = analysis_result.get("error", "Unknown error") if isinstance(analysis_result, dict) else "Processing failed"
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "PDF document analysis failed",
                    "detail": error_msg,
                    "processing_time": round(processing_time, 3),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"PDF document analysis failed: {str(e)}"
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

@app.get("/status")
async def get_status():
    """Get current processor status and capabilities."""
    if not processor_instance:
        return {
            "status": "error",
            "message": "Processor not initialized",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        status_info = processor_instance.get_status()
        return {
            "status": "healthy",
            "processor_status": status_info,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get status: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Enhanced Document Analysis API",
        "version": "2.0.0",
        "capabilities": {
            "essay_evaluation": "AI-powered essay evaluation with skills assessment",
            "document_analysis": "Sequential document analysis using Azure AI Foundry agents",
            "pdf_analysis": "PDF document analysis with text extraction and AI processing",
            "fallback_processing": "Automatic fallback to traditional processing when agents unavailable"
        },
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "evaluate": "/evaluate",
            "analyze_document": "/analyze-document",
            "analyze_pdf": "/analyze-pdf",
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