import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from foundry_agent_factory import FoundryAgentFactory
from sequential_workflow_manager import SequentialWorkflowManager

class PromptProcessor:
    """AI Foundry agents processor for document analysis using Azure AI Foundry agents"""
    
    def __init__(self, deployment_name: str, api_key: str, endpoint: str = None,
                 project_endpoint: str = None):
        
        self.base_model_config = {
            "deployment_name": deployment_name,
            "api_key": api_key,
            "endpoint": endpoint
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize foundry integration
        self.foundry_available = False
        self.agent_factory: Optional[FoundryAgentFactory] = None
        self.workflow_manager: Optional[SequentialWorkflowManager] = None
        
        if not project_endpoint:
            raise ValueError("Project endpoint is required for Azure AI Foundry integration")
        
        try:
            self.logger.info(f"Initializing Azure AI Foundry integration with endpoint: {project_endpoint}")
            self.logger.info(f"Base model: {self.base_model_config['deployment_name']}")
            
            self.agent_factory = FoundryAgentFactory(
                project_endpoint, 
                self.base_model_config
            )
            
            self.logger.info("FoundryAgentFactory created. Agent validation will be done on first use...")
            # Defer validation to async initialization
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Azure AI Foundry integration: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise Exception(f"Azure AI Foundry initialization failed: {e}")
    
    async def _initialize_foundry_agents(self) -> bool:
        """Initialize foundry agents asynchronously"""
        if not self.agent_factory:
            return False
            
        try:
            self.logger.info("Starting async foundry agents validation...")
            
            # Validate agents availability
            if await self.agent_factory.validate_agents_availability():
                self.logger.info("Agent validation successful, creating workflow manager...")
                self.workflow_manager = SequentialWorkflowManager(self.agent_factory)
                self.foundry_available = True
                self.logger.info("✅ Azure AI Foundry agents initialized successfully")
                return True
            else:
                self.logger.error("❌ Azure AI Foundry agents validation failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to validate Azure AI Foundry agents: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method using Azure AI Foundry agents"""
        
        # Initialize foundry agents if not already done
        if self.agent_factory and not self.foundry_available:
            self.logger.info("Attempting to initialize foundry agents...")
            await self._initialize_foundry_agents()
        
        if not self.agent_factory:
            error_msg = "No Azure AI Foundry agent factory available"
            self.logger.error(error_msg)
            raise Exception(error_msg)
            
        if not self.foundry_available:
            error_msg = "Azure AI Foundry agents are required but not available"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Process using foundry agents
        return await self._process_with_foundry_agents(payload)
    
    async def process_document_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process document analysis using the sequential workflow with Azure AI Foundry agents"""
        
        self.logger.info("=== PROCESS_DOCUMENT_ANALYSIS STARTED ===")
        self.logger.info(f"Foundry available: {self.foundry_available}")
        self.logger.info(f"Agent factory exists: {self.agent_factory is not None}")
        self.logger.info(f"Workflow manager exists: {self.workflow_manager is not None}")
        
        # Initialize foundry agents if not already done
        if self.agent_factory and not self.foundry_available:
            self.logger.info("Attempting to initialize foundry agents for document analysis...")
            await self._initialize_foundry_agents()
        
        if not self.foundry_available:
            error_msg = "Azure AI Foundry agents are required but not available"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        try:
            # Prepare input for sequential workflow
            workflow_input = {
                "content": payload.get("document_text", payload.get("content", "")),
                "analysis_parameters": payload.get("analysis_parameters", {}),
                "task_type": "document_analysis"
            }
            
            self.logger.info("=== ABOUT TO CALL WORKFLOW_MANAGER.EXECUTE_WORKFLOW ===")
            self.logger.info(f"Workflow input keys: {list(workflow_input.keys())}")
            self.logger.info(f"Content length: {len(workflow_input['content'])}")
            
            # Execute sequential workflow
            result = await self.workflow_manager.execute_workflow(workflow_input)
            
            self.logger.info("=== WORKFLOW_MANAGER.EXECUTE_WORKFLOW COMPLETED ===")
            self.logger.info(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            if result["success"]:
                self.logger.info("Document analysis completed using Foundry agents")
                return self._format_foundry_result(result, payload)
            else:
                error_msg = f"Foundry workflow failed: {result.get('error', 'Unknown error')}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            error_msg = f"Error in Foundry agents processing: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    async def continue_analysis(self, workflow_result: Dict[str, Any], 
                              additional_question: str) -> Dict[str, Any]:
        """Continue analysis in the same thread context"""
        
        if not self.foundry_available or not self.workflow_manager:
            return {
                "success": False,
                "error": "Foundry agents not available for conversation continuation"
            }
        
        try:
            result = await self.workflow_manager.continue_conversation(additional_question)
            return self._format_continuation_result(result)
            
        except Exception as e:
            self.logger.error(f"Error continuing analysis: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_with_foundry_agents(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process using Azure AI Foundry agents"""
        
        # Reset workflow for new processing
        self.workflow_manager.reset_workflow()
        
        # Prepare input based on payload type
        if self._is_document_analysis_payload(payload):
            return await self.process_document_analysis(payload)
        else:
            # For other types, use generic workflow
            workflow_input = {
                "content": self._extract_content_from_payload(payload),
                "analysis_parameters": payload.get("parameters", {}),
                "task_type": payload.get("type", "general_analysis")
            }
            
            result = await self.workflow_manager.execute_workflow(workflow_input)
            return self._format_foundry_result(result, payload)
    
    def _is_document_analysis_payload(self, payload: Dict[str, Any]) -> bool:
        """Check if payload is for document analysis"""
        
        indicators = [
            "document_text" in payload,
            "analysis_parameters" in payload,
            payload.get("type") == "document_analysis",
            payload.get("task_type") == "document_analysis"
        ]
        
        return any(indicators)
    
    def _extract_content_from_payload(self, payload: Dict[str, Any]) -> str:
        """Extract content from various payload formats"""
        
        content_fields = ["document_text", "content", "text"]
        
        for field in content_fields:
            if field in payload and payload[field]:
                return str(payload[field])
        
        # If no direct content field, try to extract from nested structures
        if "prompt" in payload:
            return str(payload["prompt"])
        
        # Last resort: stringify the entire payload (excluding metadata)
        filtered_payload = {k: v for k, v in payload.items() 
                           if k not in ["type", "timestamp", "id", "metadata"]}
        
        return json.dumps(filtered_payload)
    
    def _format_foundry_result(self, foundry_result: Dict[str, Any], 
                              original_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format Foundry workflow results for consistent output"""
        
        formatted_result = {
            "success": foundry_result["success"],
            "processing_type": "azure_foundry_agents",
            "workflow_type": foundry_result.get("workflow_type", "sequential"),
            "foundry_available": True
        }
        
        if foundry_result["success"]:
            formatted_result.update({
                "result": foundry_result.get("structured_result", {}),
                "agents_used": foundry_result.get("agents_used", []),
                "shared_thread_id": foundry_result.get("shared_thread_id"),
                "execution_summary": foundry_result.get("execution_summary", {}),
                "raw_responses": foundry_result.get("responses", [])
            })
        else:
            formatted_result.update({
                "error": foundry_result.get("error", "Unknown error"),
                "shared_thread_id": foundry_result.get("shared_thread_id")
            })
        
        return formatted_result
    
    def _format_continuation_result(self, continuation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format conversation continuation results"""
        
        return {
            "success": continuation_result["success"],
            "processing_type": "foundry_continuation",
            "conversation_continued": continuation_result.get("conversation_continued", False),
            "responses": continuation_result.get("responses", []),
            "shared_thread_id": continuation_result.get("shared_thread_id"),
            "error": continuation_result.get("error")
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processor status"""
        
        status = {
            "foundry_available": self.foundry_available,
            "has_agent_factory": self.agent_factory is not None,
            "has_workflow_manager": self.workflow_manager is not None
        }
        
        if self.workflow_manager:
            status["workflow_status"] = self.workflow_manager.get_workflow_status()
        
        return status