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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from analyzer.processors.prompt_processor import PromptProcessor
from analyzer.plugins.pdf_reader_plugin import PDFReaderPlugin
from analyzer.plugins.xlsx_reader_plugin import XLSXReaderPlugin

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
    Validate required environment variables for Agent Framework.
    Raises ValueError with clear message if any variables are missing.
    """
    required_vars = {
        'AZURE_OPENAI_DEPLOYMENT': os.getenv('AZURE_OPENAI_DEPLOYMENT') or os.getenv('MODEL_DEPLOYMENT_NAME'),
        'AZURE_OPENAI_API_KEY': os.getenv('AZURE_OPENAI_API_KEY') or os.getenv('AI_API_KEY'),
        'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT') or os.getenv('AI_ENDPOINT'),
        'AZURE_OPENAI_API_VERSION': os.getenv('AZURE_OPENAI_API_VERSION') or os.getenv('API_VERSION', '2024-05-01-preview')
    }
    
    missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.critical(error_msg)
        logger.critical("Please ensure all required environment variables are set before starting the application.")
        raise ValueError(error_msg)
    
    logger.info("All required environment variables are present")
    logger.info("Microsoft Agent Framework integration enabled")
    logger.info("MCP Server: " + os.getenv('MCP_SERVER_URL', 'https://learn.microsoft.com/api/mcp'))
    
    return required_vars

# Pydantic Models
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
    processing_type: str = Field(..., description="Type of processing used")
    agents_used: List[str] = Field(default=[], description="List of agents used in processing")
    shared_thread_id: Optional[str] = Field(default=None, description="Thread ID for conversation continuity")
    
class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str = "1.0.0"

# Get the absolute path to the static directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")

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
    logger.info("Starting API")
    try:
        env_vars = validate_environment_variables()
        
        # Initialize processor with Agent Framework
        processor_instance = PromptProcessor(
            deployment_name=env_vars['AZURE_OPENAI_DEPLOYMENT'],
            api_key=env_vars['AZURE_OPENAI_API_KEY'],
            endpoint=env_vars['AZURE_OPENAI_ENDPOINT'],
            api_version=env_vars['AZURE_OPENAI_API_VERSION'],
            use_agent_framework=True
        )
        
        logger.info(f"Initialized PromptProcessor with Microsoft Agent Framework using model: {env_vars['AZURE_OPENAI_DEPLOYMENT']}")
        
    except Exception as e:
        logger.critical(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Document Analysis API")
    if processor_instance:
        try:
            # Processor doesn't require explicit cleanup
            logger.info("PromptProcessor shutdown completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Create FastAPI app with lifecycle management
app = FastAPI(
    title="Multi-Agent Document Analysis API",
    description="AI-powered document analysis service using Microsoft Agent Framework with direct MCP connectivity",
    version="3.0.0",
    lifespan=lifespan
)

# Mount static files directory
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    """Serve the frontend application."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {
            "message": "Multi-Agent Architecture Analyzer API",
            "version": "2.0.0",
            "endpoints": {
                "health": "/health",
                "analyze_document": "/analyze-document",
                "analyze_pdf": "/analyze-pdf",
                "analyze_excel": "/analyze-excel"
            }
        }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )

# ============================================
# Agent Management Endpoints
# ============================================

@app.get("/api/agents/status")
async def get_agents_status():
    """
    Check the status of Agent Framework agents.
    Returns information about the configured agents.
    """
    try:
        # Agent Framework agents are always configured at startup
        status = processor_instance.get_workflow_status()
        
        return {
            "status": "success",
            "framework": status.get("framework", "Agent Framework"),
            "agents_configured": status.get("workflow_ready", True),
            "agents": status.get("agent_names", []),
            "total_agents": status.get("agents_configured", 7),
            "mcp_tool_available": status.get("mcp_tool_available", True),
            "pricing_api_available": status.get("pricing_api_available", True),
            "message": "Agent Framework agents are configured at startup - no setup needed",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to check agents status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check agents status: {str(e)}"
        )

@app.post("/api/agents/setup")
async def setup_agents():
    """
    Agent Framework setup status.
    With Agent Framework, agents are automatically configured at application startup.
    """
    try:
        logger.info("Agent Framework agents are pre-configured at startup")
        
        status = processor_instance.get_workflow_status()
        
        if not status.get("workflow_ready", False):
            raise HTTPException(
                status_code=500,
                detail="Agent Framework workflow not ready. Check application logs for initialization errors."
            )
        
        return {
            "status": "success",
            "message": "Agent Framework agents are configured and ready",
            "framework": "Agent Framework",
            "agents": status.get("agent_names", []),
            "total_agents": status.get("agents_configured", 7),
            "mcp_tool": "Direct MCP connectivity via HostedMCPTool",
            "pricing_api": "Azure Retail Prices API via AIFunction",
            "note": "No manual setup required - agents initialized at startup",
            "timestamp": datetime.utcnow().isoformat()
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check agents setup: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check agents setup: {str(e)}"
        )

@app.post("/api/agents/recreate")
async def recreate_agents():
    """
    Recreate Agent Framework agents.
    This reinitializes all agents by reloading prompt templates from disk.
    """
    try:
        # Reinitialize agents
        result = processor_instance.reinitialize_agents()
        
        return {
            "status": "success",
            "message": "Successfully recreated all agents from prompt templates",
            "deleted_agents": result["deleted_agents"],
            "created_agents": result["created_agents"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in recreate_agents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to recreate agents: {str(e)}"
        )

@app.get("/api/agents/list")
async def list_agents():
    """
    List all Agent Framework agents.
    """
    try:
        status = processor_instance.get_workflow_status()
        
        agents_info = [
            {
                "name": "ArchitectureDetailExtractor",
                "role": "Extractor",
                "description": "Identifies architectural patterns and components",
                "tools": []
            },
            {
                "name": "AzureResourcesSpecialist",
                "role": "Orchestrator",
                "description": "Coordinates workflow and consolidates recommendations",
                "tools": []
            },
            {
                "name": "AzureContainersSpecialist",
                "role": "Specialist",
                "description": "Analyzes container orchestration and registry services",
                "tools": ["HostedMCPTool (Microsoft Learn)"]
            },
            {
                "name": "AzureComputeSpecialist",
                "role": "Specialist",
                "description": "Analyzes compute, web hosting, and serverless resources",
                "tools": ["HostedMCPTool (Microsoft Learn)"]
            },
            {
                "name": "AzureInfrastructureSpecialist",
                "role": "Specialist",
                "description": "Analyzes networking, security, and connectivity resources",
                "tools": ["HostedMCPTool (Microsoft Learn)"]
            },
            {
                "name": "AzureDatabaseSpecialist",
                "role": "Specialist",
                "description": "Analyzes databases, caching, and data storage services",
                "tools": ["HostedMCPTool (Microsoft Learn)"]
            },
            {
                "name": "AzureCalculatorSpecialist",
                "role": "Calculator",
                "description": "Calculates costs using Azure Retail Prices API",
                "tools": ["AIFunction (Azure Pricing API)"]
            }
        ]
        
        return {
            "status": "success",
            "framework": "Agent Framework",
            "count": len(agents_info),
            "agents": agents_info,
            "workflow_ready": status.get("workflow_ready", True),
            "timestamp": datetime.utcnow().isoformat()
        }
            
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list agents: {str(e)}"
        )

@app.post("/api/agents/{agent_name}/update-instructions")
async def update_agent_instructions(agent_name: str):
    """
    Update agent instructions in Agent Framework.
    Agents load instructions from prompt template files at startup.
    """
    return {
        "status": "info",
        "message": f"Agent Framework agents load instructions from prompt templates at startup",
        "agent_name": agent_name,
        "note": "To update agent instructions, modify the prompt template files and restart the application",
        "prompt_files": [
            "prompt_template_extractor.txt",
            "prompt_template_azure_resources_specialist.txt",
            "prompt_template_containers.txt",
            "prompt_template_compute.txt",
            "prompt_template_infrastructure.txt",
            "prompt_template_database.txt",
            "prompt_template_cost_calculator.txt"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================
# Document Analysis Endpoints
# ============================================

@app.post("/analyze-document")
async def analyze_document(request: DocumentAnalysisRequest):
    """
    Analyze a document using Azure AI Foundry agents.
    
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
        
        # Process using PromptProcessor
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
            
            # Extract insights from structured_result - it now contains fields directly
            structured_result = result_data.get("structured_result", {})
            
            # Extract agent responses from responses array
            agent_responses_raw = result_data.get("responses", [])
            
            # Extract cost analysis from Calculator agent response
            cost_analysis = None
            for resp in agent_responses_raw:
                agent_name = resp.get("agent", "")
                content = resp.get("content", "")
                
                if "calculator" in agent_name.lower() or "cost" in agent_name.lower():
                    try:
                        if isinstance(content, str):
                            import re
                            json_match = re.search(r'\{[\s\S]*"calculation_status"[\s\S]*\}', content)
                            if json_match:
                                cost_analysis = json.loads(json_match.group(0))
                                logger.info("Successfully extracted cost analysis from Calculator agent (doc endpoint)")
                        elif isinstance(content, dict):
                            cost_analysis = content
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse cost analysis JSON: {e}")
            
            # Transform agent responses for frontend compatibility
            agent_responses = [
                {
                    "agent_name": resp.get("agent", f"Agent {i+1}"),
                    "content": resp.get("content", ""),
                    "timestamp": resp.get("timestamp", ""),
                    "thread_id": resp.get("thread_id", ""),
                    "status": resp.get("status", "error" if resp.get("error") else "success")
                }
                for i, resp in enumerate(agent_responses_raw)
            ]
            
            # Build frontend-compatible response structure
            frontend_result = {
                "processing_time_seconds": round(processing_time, 2),
                "status": "success",
                "agent_responses": agent_responses,
                "agents_used": len(agent_responses),
                "azure_services": structured_result.get("azure_services", []),
                "architecture_patterns": structured_result.get("architecture_patterns", []),
                "recommendations": structured_result.get("recommendations", []),
                "summary": structured_result.get("summary", ""),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if cost_analysis:
                frontend_result["cost_analysis"] = cost_analysis
                logger.info("Cost analysis included in response")
            
            processing_type = analysis_result.get("processing_type", "azure_foundry_agents")
            agents_used_names = analysis_result.get("agents_used", [])
            shared_thread_id = analysis_result.get("shared_thread_id")
            
            logger.info(f"Document analysis completed successfully in {processing_time:.2f} seconds using {processing_type}")
            
            # Return data directly without wrapper
            return frontend_result
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

@app.post("/analyze-pdf")
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
        
        # Process using PromptProcessor
        try:
            logger.info("=== API: ABOUT TO CALL PROCESSOR.PROCESS_DOCUMENT_ANALYSIS ===")
            logger.info(f"Processor instance type: {type(processor_instance)}")
            logger.info(f"Payload keys: {list(payload.keys())}")
            
            analysis_result = await processor_instance.process_document_analysis(payload)
            
            logger.info("=== API: PROCESSOR.PROCESS_DOCUMENT_ANALYSIS COMPLETED ===")
            logger.info(f"Analysis result type: {type(analysis_result)}")
            logger.info(f"Analysis result success: {analysis_result.get('success') if isinstance(analysis_result, dict) else 'N/A'}")
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
            
            # Extract insights from structured_result - it now contains fields directly
            structured_result = result_data.get("structured_result", {})
            
            # Extract agent responses from responses array
            agent_responses_raw = result_data.get("responses", [])
            
            # Extract cost analysis from Calculator agent response
            cost_analysis = None
            for resp in agent_responses_raw:
                agent_name = resp.get("agent", "")
                content = resp.get("content", "")
                
                if "calculator" in agent_name.lower() or "cost" in agent_name.lower():
                    try:
                        if isinstance(content, str):
                            import re
                            json_match = re.search(r'\{[\s\S]*"calculation_status"[\s\S]*\}', content)
                            if json_match:
                                cost_analysis = json.loads(json_match.group(0))
                                logger.info("Successfully extracted cost analysis from Calculator agent (pdf endpoint)")
                        elif isinstance(content, dict):
                            cost_analysis = content
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse cost analysis JSON: {e}")
            
            # Transform agent responses for frontend compatibility
            agent_responses = [
                {
                    "agent_name": resp.get("agent", f"Agent {i+1}"),
                    "content": resp.get("content", ""),
                    "timestamp": resp.get("timestamp", ""),
                    "thread_id": resp.get("thread_id", ""),
                    "status": resp.get("status", "error" if resp.get("error") else "success")
                }
                for i, resp in enumerate(agent_responses_raw)
            ]
            
            # Build frontend-compatible response structure
            frontend_result = {
                "processing_time_seconds": round(processing_time, 2),
                "status": "success",
                "agent_responses": agent_responses,
                "agents_used": len(agent_responses),
                "azure_services": structured_result.get("azure_services", []),
                "architecture_patterns": structured_result.get("architecture_patterns", []),
                "recommendations": structured_result.get("recommendations", []),
                "summary": structured_result.get("summary", ""),
                "pdf_extraction_metadata": extraction_result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if cost_analysis:
                frontend_result["cost_analysis"] = cost_analysis
                logger.info("Cost analysis included in response")
            
            processing_type = analysis_result.get("processing_type", "azure_foundry_agents")
            agents_used_names = analysis_result.get("agents_used", [])
            shared_thread_id = analysis_result.get("shared_thread_id")
            
            logger.info(f"PDF document analysis completed successfully in {processing_time:.2f} seconds using {processing_type}")
            
            # Return data directly without wrapper
            return frontend_result
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

@app.post("/analyze-excel")
async def analyze_excel_document(
    file: UploadFile = File(..., description="Excel file to analyze"),
    analysis_parameters: str = Form(default="{}", description="JSON string of analysis parameters")
):
    """
    Analyze an Excel document using Azure AI Foundry agents with Excel data extraction.
    
    This endpoint:
    1. Extracts data from the uploaded Excel file using the XLSXReaderPlugin
    2. Converts the extracted data to a readable text format
    3. Processes the text through the sequential workflow:
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
        if not (file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls')):
            raise HTTPException(
                status_code=400,
                detail="Only Excel files (.xlsx, .xls) are supported"
            )
        
        logger.info(f"Processing Excel analysis request for file: {file.filename}")
        
        # Read Excel file content
        excel_content = await file.read()
        if not excel_content:
            raise HTTPException(
                status_code=400,
                detail="Empty Excel file"
            )
        
        # Convert to base64 for the Excel reader plugin
        excel_base64 = base64.b64encode(excel_content).decode('utf-8')
        
        # Extract data using XLSXReaderPlugin
        xlsx_reader = XLSXReaderPlugin()
        extraction_result = xlsx_reader.extract_xlsx_from_base64(
            base64_content=excel_base64,
            max_rows_per_sheet=1000
        )
        
        if not extraction_result.success:
            raise HTTPException(
                status_code=400,
                detail=f"Excel data extraction failed: {extraction_result.error_message}"
            )
        
        # Convert extracted data to readable text format
        extracted_text_parts = []
        extracted_text_parts.append(f"Excel File Analysis: {file.filename}")
        extracted_text_parts.append(f"Total Sheets: {extraction_result.metadata.get('total_sheets', 0)}")
        extracted_text_parts.append("\n" + "="*80 + "\n")
        
        for sheet_name, rows in extraction_result.sheets.items():
            sheet_meta = extraction_result.metadata.get('sheet_metadata', {}).get(sheet_name, {})
            extracted_text_parts.append(f"\n### Sheet: {sheet_name}")
            extracted_text_parts.append(f"Rows: {sheet_meta.get('row_count', 0)}, Columns: {sheet_meta.get('column_count', 0)}")
            
            if sheet_meta.get('truncated', False):
                extracted_text_parts.append("(Note: Data truncated to 1000 rows)")
            
            extracted_text_parts.append("\nData:")
            
            # Convert rows to text format
            for i, row in enumerate(rows[:100]):  # Limit to first 100 rows for text representation
                row_text = " | ".join([str(cell) for cell in row])
                extracted_text_parts.append(f"Row {i+1}: {row_text}")
            
            if len(rows) > 100:
                extracted_text_parts.append(f"... and {len(rows) - 100} more rows")
            
            extracted_text_parts.append("\n" + "-"*80)
        
        extracted_text = "\n".join(extracted_text_parts)
        
        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No data content found in Excel file"
            )
        
        # Parse analysis parameters
        try:
            analysis_params = json.loads(analysis_parameters) if analysis_parameters else {}
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid analysis_parameters JSON format"
            )
        
        logger.info(f"Extracted data from {extraction_result.metadata.get('total_sheets', 0)} sheets")
        
        # Prepare payload for document analysis with extracted text
        payload = {
            "document_text": extracted_text,
            "analysis_parameters": analysis_params,
            "type": "excel_analysis",
            "source_file": file.filename,
            "extraction_metadata": extraction_result.metadata
        }
        
        # Process using PromptProcessor
        try:
            logger.info("=== API: ABOUT TO CALL PROCESSOR.PROCESS_DOCUMENT_ANALYSIS ===")
            logger.info(f"Processor instance type: {type(processor_instance)}")
            logger.info(f"Payload keys: {list(payload.keys())}")
            
            analysis_result = await processor_instance.process_document_analysis(payload)
            
            logger.info("=== API: PROCESSOR.PROCESS_DOCUMENT_ANALYSIS COMPLETED ===")
            logger.info(f"Analysis result type: {type(analysis_result)}")
            logger.info(f"Analysis result success: {analysis_result.get('success') if isinstance(analysis_result, dict) else 'N/A'}")
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
            
            # Debug logging
            logger.info(f"=== API EXTRACT DEBUG ===")
            logger.info(f"Analysis result keys: {list(analysis_result.keys())}")
            logger.info(f"Result data keys: {list(result_data.keys())}")
            
            # Extract insights from structured_result - it now contains fields directly
            structured_result = result_data.get("structured_result", {})
            logger.info(f"Structured result type: {type(structured_result)}")
            logger.info(f"Structured result keys: {list(structured_result.keys()) if isinstance(structured_result, dict) else 'NOT A DICT'}")
            if isinstance(structured_result, dict):
                logger.info(f"Azure services: {structured_result.get('azure_services', [])}")
                logger.info(f"Architecture patterns: {structured_result.get('architecture_patterns', [])}")
                logger.info(f"Recommendations count: {len(structured_result.get('recommendations', []))}")
                logger.info(f"Summary length: {len(structured_result.get('summary', ''))}")
            
            # Extract agent responses from responses array
            agent_responses_raw = result_data.get("responses", [])
            logger.info(f"Agent responses count: {len(agent_responses_raw)}")
            
            # Extract cost analysis and detailed resources from agent responses
            cost_analysis = None
            resources_content = None
            detailed_resources = []
            specialist_analyses = {}
            
            for resp in agent_responses_raw:
                agent_name = resp.get("agent", "")
                content = resp.get("content", "")
                
                # Parse JSON content from agent response
                try:
                    if isinstance(content, str):
                        parsed_agent_content = json.loads(content)
                    elif isinstance(content, dict):
                        parsed_agent_content = content
                    else:
                        continue
                    
                    # Check if this is the Calculator specialist
                    if "calculator" in agent_name.lower() or "cost" in agent_name.lower():
                        cost_analysis = parsed_agent_content
                        logger.info("Successfully extracted cost analysis from Calculator agent")
                    
                    # Check if this is the Resources specialist (orchestrator)
                    if "resources" in agent_name.lower() and "specialist" in agent_name.lower():
                        resources_content = content
                        logger.info(f"Found orchestrator agent: {agent_name}")
                        logger.info(f"Orchestrator has specialist_results: {'specialist_results' in parsed_agent_content}")
                        
                        # Extract detailed resources from specialist_results
                        if "specialist_results" in parsed_agent_content:
                            sr = parsed_agent_content["specialist_results"]
                            logger.info(f"Specialist results domains: {list(sr.keys())}")
                            
                            # Extract from each specialist domain
                            for domain in ["compute", "infrastructure", "database", "containers"]:
                                if domain in sr and "resources" in sr[domain]:
                                    domain_resources = sr[domain]["resources"]
                                    logger.info(f"Found {len(domain_resources)} resources in {domain} domain")
                                    
                                    # Add to detailed resources with category tag
                                    for resource in domain_resources:
                                        resource["category"] = domain
                                        detailed_resources.append(resource)
                                    
                                    # Also store in specialist_analyses for frontend compatibility
                                    specialist_analyses[f"{domain}_analysis"] = {
                                        "analysis": domain_resources,
                                        "specialist": sr[domain].get("specialist", ""),
                                        "unmapped_items": sr[domain].get("unmapped_items", [])
                                    }
                        
                        logger.info(f"Extracted {len(detailed_resources)} detailed resources from orchestrator")
                        logger.info(f"Built specialist_analyses with {len(specialist_analyses)} domains: {list(specialist_analyses.keys())}")
                    
                    # Check if this is a domain specialist (fallback if orchestrator doesn't have full data)
                    elif any(domain in agent_name.lower() for domain in ["compute", "infrastructure", "database", "container"]):
                        if "resources" in parsed_agent_content:
                            specialist_resources = parsed_agent_content["resources"]
                            
                            # Determine category from agent name
                            category = "compute" if "compute" in agent_name.lower() else \
                                      "infrastructure" if "infrastructure" in agent_name.lower() else \
                                      "database" if "database" in agent_name.lower() else \
                                      "containers"
                            
                            # Add to detailed resources
                            for resource in specialist_resources:
                                resource["category"] = category
                                if resource not in detailed_resources:  # Avoid duplicates
                                    detailed_resources.append(resource)
                            
                            logger.info(f"Extracted {len(specialist_resources)} resources from {agent_name}")
                    
                except json.JSONDecodeError as e:
                    logger.debug(f"Could not parse JSON from {agent_name}: {e}")
                except Exception as e:
                    logger.debug(f"Error processing {agent_name} response: {e}")
            
            # Transform agent responses for frontend compatibility
            agent_responses = [
                {
                    "agent_name": resp.get("agent", f"Agent {i+1}"),
                    "content": resp.get("content", ""),
                    "timestamp": resp.get("timestamp", ""),
                    "thread_id": resp.get("thread_id", ""),
                    "status": resp.get("status", "error" if resp.get("error") else "success")
                }
                for i, resp in enumerate(agent_responses_raw)
            ]
            
            # Build frontend-compatible response structure
            frontend_result = {
                "processing_time_seconds": round(processing_time, 2),
                "status": "success",
                "agent_responses": agent_responses,
                "agents_used": len(agent_responses),
                "azure_services": structured_result.get("azure_services", []),
                "architecture_patterns": structured_result.get("architecture_patterns", []),
                "recommendations": structured_result.get("recommendations", []),
                "summary": structured_result.get("summary", ""),
                "excel_extraction_metadata": extraction_result.to_dict(),
                "timestamp": datetime.utcnow().isoformat(),
                # Add detailed resources for frontend table rendering
                "resources": detailed_resources,
                "recommended_azure_resources": detailed_resources  # Alias for compatibility
            }
            
            # Add specialist analyses if available (for frontend compatibility)
            if specialist_analyses:
                frontend_result["specialist_analyses"] = specialist_analyses
                logger.info(f"Included specialist_analyses with {len(specialist_analyses)} domains")
            
            # Add cost analysis if available
            if cost_analysis:
                frontend_result["cost_analysis"] = cost_analysis
                logger.info("Cost analysis included in response")
            else:
                logger.warning("Cost analysis not found in agent responses")
            
            processing_type = analysis_result.get("processing_type", "azure_foundry_agents")
            agents_used_names = analysis_result.get("agents_used", [])
            shared_thread_id = analysis_result.get("shared_thread_id")
            
            logger.info(f"Excel document analysis completed successfully in {processing_time:.2f} seconds using {processing_type}")
            
            # Return data directly without wrapper
            return frontend_result
        else:
            # Handle error case
            error_msg = analysis_result.get("error", "Unknown error") if isinstance(analysis_result, dict) else "Processing failed"
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Excel document analysis failed",
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
        error_msg = f"Excel document analysis failed: {str(e)}"
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
        "message": "Multi-Agent Document Analysis API",
        "version": "2.0.0",
        "capabilities": {
            "document_analysis": "Sequential document analysis using Azure AI Foundry agents",
            "pdf_analysis": "PDF document analysis with text extraction and AI processing",
            "excel_analysis": "Excel document analysis with data extraction and AI processing",
            "multi_agent_workflow": "Architecture and Azure resources analysis via specialized agents"
        },
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "analyze_document": "/analyze-document",
            "analyze_pdf": "/analyze-pdf",
            "analyze_excel": "/analyze-excel",
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