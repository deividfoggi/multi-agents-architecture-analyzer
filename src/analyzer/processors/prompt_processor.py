"""
Prompt Processor: Main facade for AI Foundry agent processing.
Refactored to follow SOLID principles with delegated responsibilities.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from analyzer.agents.foundry_agent_factory import FoundryAgentFactory
from analyzer.workflows.sequential_workflow_manager import SequentialWorkflowManager

from analyzer.agents.agent_initialization_manager import AgentInitializationManager
from analyzer.workflows.payload_processor import PayloadProcessor
from analyzer.processors.result_formatter import ResultFormatter


class PromptProcessor:
    """
    Facade for Azure AI Foundry agent processing.
    Simplified through delegation to specialized components.
    """
    
    def __init__(self, deployment_name: str, api_key: str, endpoint: str = None,
                 project_endpoint: str = None):
        """
        Initialize the prompt processor.
        
        Args:
            deployment_name: Azure OpenAI deployment name
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint (optional)
            project_endpoint: Azure AI Foundry project endpoint (required for agents)
        """
        
        self.base_model_config = {
            "deployment_name": deployment_name,
            "api_key": api_key,
            "endpoint": endpoint
        }
        
        self.logger = logging.getLogger(__name__)
        self.project_endpoint = project_endpoint
        
        # Delegated components
        self.agent_init_manager = AgentInitializationManager()
        self.payload_processor = PayloadProcessor()
        self.result_formatter = ResultFormatter()
        
        # Foundry integration
        self.agent_factory: Optional[FoundryAgentFactory] = None
        self.workflow_manager: Optional[SequentialWorkflowManager] = None
        
        if project_endpoint:
            self.logger.info(f"Initializing Azure AI Foundry integration")
            self.logger.info(f"Project endpoint: {project_endpoint}")
            
            try:
                self.agent_factory = FoundryAgentFactory(
                    project_endpoint,
                    self.base_model_config
                )
                self.logger.info("FoundryAgentFactory created. Agents will be validated on first use.")
            except Exception as e:
                self.logger.error(f"Failed to initialize Azure AI Foundry: {e}", exc_info=True)
                raise
        else:
            error_msg = "Project endpoint is required for Azure AI Foundry agents"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    async def _ensure_foundry_initialized(self) -> bool:
        """
        Ensure Azure AI Foundry agents are initialized and ready.
        
        Returns:
            True if initialized successfully, False otherwise
        """
        if not self.agent_factory:
            self.logger.error("No agent factory available")
            return False
        
        # Check if already initialized
        if self.workflow_manager:
            return True
        
        try:
            self.logger.info("Validating Azure AI Foundry agents...")
            
            # Validate agents availability
            agents_available = await self.agent_factory.validate_agents_availability()
            
            if not agents_available:
                self.logger.error("Azure AI Foundry agents validation failed")
                return False
            
            # Create workflow manager
            self.logger.info("Creating workflow manager...")
            self.workflow_manager = SequentialWorkflowManager(self.agent_factory)
            
            self.logger.info("✅ Azure AI Foundry agents initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure AI Foundry agents: {e}", exc_info=True)
            return False
    
    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method using Azure AI Foundry agents.
        
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
            error_msg = "Azure AI Foundry agents are required but not available"
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
            workflow_input = {"content": content}
            result = await self.workflow_manager.execute_workflow(workflow_input)
            
            return self.result_formatter.format_foundry_result(result)
            
        except Exception as e:
            self.logger.error(f"Error processing with foundry agents: {e}", exc_info=True)
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
            error_msg = "Azure AI Foundry agents are required but not available"
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
            workflow_input = {
                "content": content,
                "analysis_parameters": payload.get("analysis_parameters", {})
            }
            
            result = await self.workflow_manager.execute_workflow(workflow_input)
            
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
            result = await self.workflow_manager.continue_conversation(continuation_message)
            
            self.logger.info("Continuation completed successfully")
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
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get current workflow status.
        
        Returns:
            Status dictionary with workflow information
        """
        if self.workflow_manager:
            return self.workflow_manager.get_workflow_status()
        
        return {
            "has_active_workflow": False,
            "has_shared_thread": False,
            "shared_thread_id": None,
            "agents_count": 0,
            "foundry_available": self.agent_factory is not None
        }
