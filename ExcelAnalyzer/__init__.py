import azure.functions as func
import logging
import json
from typing import Dict, Any, Optional
import sys
import os

# Import our custom services
from .shared.excel_extraction_service import ExcelExtractionService, ExcelExtractionResponse
# Import the main agent orchestration service from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_orchestration_service import AgentOrchestrationService

class ExcelAnalysisResponse:
    def __init__(self):
        self.success: bool = False
        self.architecture_section: Optional[str] = None
        self.azure_resources: Optional[str] = None
        self.extraction_metadata: Optional[Dict[str, Any]] = None
        self.agent_metadata: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "architectureSection": self.architecture_section,
            "azureResources": self.azure_resources,
            "extractionMetadata": self.extraction_metadata,
            "agentMetadata": self.agent_metadata,
            "errorMessage": self.error_message
        }

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to analyze Excel documents using text extraction and AI agent orchestration.
    """
    logging.info("ExcelAnalyzer function triggered.")
    logging.info(f"Request method: {req.method}")
    logging.info(f"Request URL: {req.url}")
    
    try:
        # Validate request has files
        files = req.files
        if not files:
            logging.warning("No files found in request.")
            response = ExcelAnalysisResponse()
            response.error_message = "No Excel file provided. Please upload an Excel file (.xlsx or .xls)."
            return func.HttpResponse(
                json.dumps(response.to_dict()),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get the first file
        file_data = None
        file_name = None
        content_type = None
        
        for file_key in files:
            file = files[file_key]
            file_data = file.read()
            file_name = file.filename
            content_type = file.content_type
            break
        
        if not file_data or not file_name:
            logging.warning("Invalid file data received.")
            response = ExcelAnalysisResponse()
            response.error_message = "Invalid file data received."
            return func.HttpResponse(
                json.dumps(response.to_dict()),
                status_code=400,
                mimetype="application/json"
            )
        
        # Validate file extension
        if not file_name.lower().endswith(('.xlsx', '.xls')):
            logging.warning(f"Invalid file type: {file_name}")
            response = ExcelAnalysisResponse()
            response.error_message = "Invalid file type. Please upload an Excel file (.xlsx or .xls)."
            return func.HttpResponse(
                json.dumps(response.to_dict()),
                status_code=400,
                mimetype="application/json"
            )
        
        # Step 1: Extract text from Excel
        logging.info(f"Starting Excel text extraction for file: {file_name}")
        excel_extraction_service = ExcelExtractionService()
        text_extraction_result = excel_extraction_service.extract_text_from_excel(
            file_data, file_name
        )
        
        if not text_extraction_result.success:
            response = ExcelAnalysisResponse()
            response.error_message = text_extraction_result.error_message
            response.extraction_metadata = text_extraction_result.to_dict().get("extractionMetadata")
            return func.HttpResponse(
                json.dumps(response.to_dict()),
                status_code=400,
                mimetype="application/json"
            )
        
        logging.info(f"Text extraction completed. Text length: {len(text_extraction_result.extracted_text) if text_extraction_result.extracted_text else 0}")
        
        # Step 2: Orchestrate the agents to process the extracted text
        agent_orchestration_service = AgentOrchestrationService()
        agent_result = await agent_orchestration_service.process_document_async(text_extraction_result.extracted_text)
        
        if not agent_result.success:
            response = ExcelAnalysisResponse()
            response.error_message = agent_result.error_message
            response.extraction_metadata = text_extraction_result.to_dict().get("extractionMetadata")
            response.agent_metadata = agent_result.to_dict().get("agentMetadata")
            return func.HttpResponse(
                json.dumps(response.to_dict()),
                status_code=500,
                mimetype="application/json"
            )
        
        # Step 3: Return combined results
        response = ExcelAnalysisResponse()
        response.success = True
        response.architecture_section = agent_result.architecture_section
        response.azure_resources = agent_result.azure_resources
        response.extraction_metadata = text_extraction_result.to_dict().get("extractionMetadata")
        response.agent_metadata = agent_result.to_dict().get("agentMetadata")
        
        logging.info("Excel analysis completed successfully.")
        return func.HttpResponse(
            json.dumps(response.to_dict()),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as ex:
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"Error during Excel analysis: {ex}")
        logging.error(f"Full traceback: {error_details}")
        
        response = ExcelAnalysisResponse()
        response.error_message = f"Internal server error: {str(ex)}"
        return func.HttpResponse(
            json.dumps(response.to_dict()),
            status_code=500,
            mimetype="application/json"
        )
