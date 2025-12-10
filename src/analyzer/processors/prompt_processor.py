"""
Prompt Processor: Main facade for Agent Framework processing.
Refactored to use Microsoft Agent Framework with direct MCP connectivity.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from analyzer.workflows.agent_framework_workflow_manager import AgentFrameworkWorkflowManager
from analyzer.workflows.payload_processor import PayloadProcessor
from analyzer.processors.result_formatter import ResultFormatter


class PromptProcessor:
    """
    Facade for Microsoft Agent Framework processing.
    Simplified through delegation to specialized components.
    """
    
    def __init__(self, deployment_name: str, api_key: str, endpoint: str,
                 api_version: str = "2024-05-01-preview", use_agent_framework: bool = True):
        """
        Initialize the prompt processor.
        
        Args:
            deployment_name: Azure OpenAI deployment name
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint
            api_version: Azure OpenAI API version
            use_agent_framework: Use Microsoft Agent Framework (default: True)
        """
        
        self.base_model_config = {
            "deployment_name": deployment_name,
            "api_key": api_key,
            "endpoint": endpoint,
            "api_version": api_version
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Delegated components
        self.payload_processor = PayloadProcessor()
        self.result_formatter = ResultFormatter()
        
        # Agent Framework workflow integration
        self.workflow_manager: Optional[AgentFrameworkWorkflowManager] = None
        
        if use_agent_framework:
            self.logger.info(f"Initializing Microsoft Agent Framework integration")
            self.logger.info(f"Azure OpenAI endpoint: {endpoint}")
            self.logger.info(f"Model deployment: {deployment_name}")
            
            try:
                mcp_server_url = os.getenv('MCP_SERVER_URL', 'https://learn.microsoft.com/api/mcp')
                
                self.workflow_manager = AgentFrameworkWorkflowManager(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    deployment_name=deployment_name,
                    api_version=api_version,
                    mcp_server_url=mcp_server_url
                )
                self.logger.info("Agent Framework Workflow Manager created successfully")
                self.logger.info(f"MCP Server configured: {mcp_server_url}")
            except Exception as e:
                self.logger.error(f"Failed to initialize Agent Framework: {e}", exc_info=True)
                raise
        else:
            error_msg = "use_agent_framework must be True for current implementation"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    async def _ensure_foundry_initialized(self) -> bool:
        """
        Ensure Agent Framework workflow manager is initialized and ready.
        
        Returns:
            True if initialized successfully, False otherwise
        """
        if not self.workflow_manager:
            self.logger.error("No workflow manager available")
            return False
        
        try:
            self.logger.info("Agent Framework workflow manager is ready")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to verify Agent Framework workflow: {e}", exc_info=True)
            return False
    
    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method using Microsoft Agent Framework.
        
        Args:
            payload: Input payload containing content to process
            
        Returns:
            Processing results dictionary
            
        Raises:
            Exception: If agents not available or processing fails
        """
        
        self.logger.info("=== PROCESS START ===")
        
        # Ensure agents are initialized
        if not await self._ensure_foundry_initialized():
            error_msg = "Agent Framework agents are required but not available"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Validate payload
        if not self.payload_processor.validate_payload(payload):
            error_msg = "Invalid payload: missing content"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Extract content from payload
        content = self.payload_processor.extract_content(payload)
        self.logger.info(f"Extracted content: {len(content)} characters")
        
        # Process with workflow manager
        try:
            metadata = payload.get("metadata", {})
            result = await self.workflow_manager.execute_workflow(content, metadata)
            
            return self.result_formatter.format_foundry_result(result)
            
        except Exception as e:
            self.logger.error(f"Error processing with Agent Framework: {e}", exc_info=True)
            return self.result_formatter.format_error(e, "workflow_execution")
    
    async def process_document_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process document analysis using the sequential workflow.
        
        Args:
            payload: Input payload containing document to analyze
            
        Returns:
            Analysis results dictionary
            
        Raises:
            Exception: If workflow not available or processing fails
        """
        
        self.logger.info("=== PROCESS_DOCUMENT_ANALYSIS START ===")
        
        # Ensure agents are initialized
        if not await self._ensure_foundry_initialized():
            error_msg = "Agent Framework agents are required but not available"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Validate payload
        if not self.payload_processor.validate_payload(payload):
            error_msg = "Invalid payload: missing content"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Extract content
        content = self.payload_processor.extract_content(payload)
        self.logger.info(f"Processing document: {len(content)} characters")
        
        # Execute workflow
        try:
            metadata = payload.get("analysis_parameters", {})
            
            result = await self.workflow_manager.execute_workflow(content, metadata)
            
            self.logger.info("Document analysis completed successfully")
            return self.result_formatter.format_foundry_result(result)
            
        except Exception as e:
            self.logger.error(f"Error in document analysis: {e}", exc_info=True)
            return self.result_formatter.format_error(e, "document_analysis")
    
    async def continue_analysis(
        self,
        continuation_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Continue an existing analysis conversation.
        
        Args:
            continuation_message: Additional message for continuation
            context: Optional context from previous interactions
            
        Returns:
            Continuation results dictionary
            
        Raises:
            ValueError: If no active workflow exists
        """
        
        self.logger.info("=== CONTINUE_ANALYSIS START ===")
        
        if not self.workflow_manager:
            error_msg = "No active workflow. Process a document first."
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Note: Continuation not yet implemented in AzureAIWorkflowManager
            # Would need to add message to existing thread and re-run agents
            result = {
                "success": False,
                "error": "Continuation not yet implemented for Azure AI SDK workflow"
            }
            
            self.logger.warning("Continuation feature not yet implemented")
            return self.result_formatter.format_continuation_result(result)
            
        except Exception as e:
            self.logger.error(f"Error in continuation: {e}", exc_info=True)
            return self.result_formatter.format_error(e, "continuation")
    
    async def reset_workflow(self):
        """Reset the workflow state for a new analysis"""
        self.logger.info("Resetting workflow state")
        
        if self.workflow_manager:
            await self.workflow_manager.reset_workflow()
            self.logger.info("Workflow reset completed")
    
    async def cleanup(self):
        """Clean up workflow manager resources."""
        if self.workflow_manager:
            self.logger.info("Agent Framework workflow manager cleanup - no action needed")
    
    def reinitialize_agents(self) -> Dict[str, Any]:
        """
        Reinitialize all agents by clearing and recreating them.
        This reloads the prompt templates from disk.
        
        Returns:
            Dictionary with deleted and created agent information
        """
        if not self.workflow_manager:
            raise ValueError("Workflow manager not initialized")
        
        self.logger.info("Reinitializing agents via PromptProcessor")
        return self.workflow_manager.reinitialize_agents()
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get current workflow status.
        
        Returns:
            Status dictionary with workflow information
        """
        if self.workflow_manager:
            return {
                "framework": "Agent Framework",
                "agents_configured": 7,
                "agent_names": [
                    "extractor",
                    "container_specialist",
                    "compute_specialist",
                    "infrastructure_specialist",
                    "database_specialist",
                    "cost_calculator",
                    "orchestrator"
                ],
                "mcp_tool_available": True,
                "pricing_api_available": True,
                "workflow_ready": True
            }
        
        return {
            "framework": "Agent Framework",
            "workflow_ready": False,
            "error": "Workflow manager not initialized"
        }
