"""
Sequential Workflow Manager for coordinating multiple AI agents in a specific order.
Each agent processes information and passes results to the next agent in the workflow.

Refactored to follow SOLID principles with delegated responsibilities.
"""
from semantic_kernel import Kernel
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentThread
from semantic_kernel.contents import ChatMessageContent
from analyzer.agents.foundry_agent_factory import FoundryAgentFactory
from typing import Dict, List, Optional, Any
import logging
import json
import asyncio

from analyzer.extractors.insights_extractor import InsightsExtractor
from analyzer.processors.result_formatter import ResultFormatter


class SequentialWorkflowManager:
    """
    Manages sequential workflows using Semantic Kernel's native orchestration.
    Simplified through delegation to specialized components.
    """
    
    def __init__(self, foundry_factory: FoundryAgentFactory):
        """
        Initialize the workflow manager.
        
        Args:
            foundry_factory: Factory for creating Azure AI Foundry agents
        """
        self.foundry_factory = foundry_factory
        self.logger = logging.getLogger(__name__)
        
        # Workflow state
        self.shared_thread: Optional[AzureAIAgentThread] = None
        self.current_workflow: Optional[List[AzureAIAgent]] = None
        
        # Delegated components
        self.insights_extractor = InsightsExtractor()
        self.result_formatter = ResultFormatter()
    
    async def create_document_analysis_workflow(self) -> List[AzureAIAgent]:
        """Create sequential workflow: Architecture Extractor → Azure Resources Specialist"""
        
        try:
            self.logger.info("=== WORKFLOW CREATION START ===")
            self.logger.info("Retrieving sequential agents from foundry factory")
            
            # Log cache status if available
            if hasattr(self.foundry_factory, 'get_cache_status'):
                cache_status = self.foundry_factory.get_cache_status()
                self.logger.info(f"Factory cache status: {cache_status}")
            
            # Get agents in sequential order
            agents = await self.foundry_factory.get_sequential_agents()
            
            self.logger.info(f"Retrieved {len(agents)} agents for sequential workflow")
            for i, agent in enumerate(agents):
                self.logger.info(f"Agent {i}: type={type(agent).__name__}, "
                               f"id={getattr(agent, 'id', 'N/A')}")
            
            # Store agents for sequential execution
            self.current_workflow = agents
            self.logger.info(f"Sequential workflow created successfully")
            
            return agents
            
        except Exception as e:
            self.logger.error(f"Failed to create document analysis workflow: {e}", exc_info=True)
            raise
    
    async def execute_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the sequential workflow with shared thread context.
        
        Args:
            input_data: Dictionary containing workflow input data
            
        Returns:
            Dictionary containing workflow execution results
        """
        
        self.logger.info("=== EXECUTE_WORKFLOW START ===")
        self.logger.info(f"Input data keys: {list(input_data.keys())}")
        
        # Ensure workflow exists
        if not self.current_workflow:
            self.logger.info("No current workflow, creating document analysis workflow")
            self.current_workflow = await self.create_document_analysis_workflow()
        
        try:
            # Ensure agent client is initialized
            await self.foundry_factory._ensure_agent_client()
            
            # Create or reuse shared thread
            await self._ensure_shared_thread()
            
            # Prepare input message
            input_text = self._prepare_workflow_input(input_data)
            
            # Execute sequential workflow
            responses = await self._execute_agents_sequentially(input_text)
            
            # Extract agent results
            agent_results = self._extract_agent_results(responses)
            
            # Structure final results
            structured_result = self._structure_workflow_results(agent_results, input_data)
            
            # Build successful response
            return {
                "success": True,
                "workflow_type": "sequential_foundry_agents",
                "shared_thread_id": getattr(self.shared_thread, 'id', 'shared_thread'),
                "agents_used": [r.get("agent", f"agent_{i+1}") 
                               for i, r in enumerate(responses)],
                "responses": responses,
                "structured_result": structured_result,
                "execution_summary": {
                    "total_agents": len(self.current_workflow),
                    "successful_responses": len(responses),
                    "sequential_execution": True,
                    "shared_thread": True
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in workflow execution: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "workflow_type": "sequential_foundry_agents"
            }
    
    async def continue_conversation(self, additional_input: str) -> Dict[str, Any]:
        """
        Continue conversation using the same workflow context.
        
        Args:
            additional_input: Additional message for continuation
            
        Returns:
            Dictionary containing continuation results
        """
        
        if not self.current_workflow:
            raise ValueError("No active workflow. Execute workflow first.")
        
        if not self.shared_thread:
            raise ValueError("No shared thread. Execute workflow first.")
        
        try:
            self.logger.info("Continuing conversation on shared thread")
            
            # Execute agents with continuation message
            responses = await self._execute_agents_sequentially(additional_input)
            
            return {
                "success": True,
                "responses": responses,
                "conversation_continued": True,
                "workflow_type": "continued_sequential",
                "shared_thread_id": getattr(self.shared_thread, 'id', 'shared_thread')
            }
            
        except Exception as e:
            self.logger.error(f"Error continuing conversation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "workflow_type": "continued_sequential"
            }
    
    async def reset_workflow(self):
        """Reset the workflow state for a new analysis"""
        if self.shared_thread:
            try:
                await self.shared_thread.delete()
                self.logger.info("Deleted shared thread")
            except Exception as e:
                self.logger.warning(f"Error deleting shared thread: {e}")
        
        self.shared_thread = None
        self.current_workflow = None
        self.logger.info("Workflow state reset")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        return {
            "has_active_workflow": self.current_workflow is not None,
            "has_shared_thread": self.shared_thread is not None,
            "shared_thread_id": getattr(self.shared_thread, 'id', None) if self.shared_thread else None,
            "agents_count": len(self.current_workflow) if self.current_workflow else 0
        }
    
    # Private helper methods
    
    async def _ensure_shared_thread(self):
        """Ensure shared thread exists, creating if necessary"""
        if not self.shared_thread:
            self.shared_thread = AzureAIAgentThread(client=self.foundry_factory.agent_client)
            self.logger.info("Created shared AzureAIAgentThread")
    
    async def _execute_agents_sequentially(self, initial_message: str) -> List[Dict[str, Any]]:
        """
        Execute all agents in sequence on the shared thread.
        
        Args:
            initial_message: The initial message for the workflow
            
        Returns:
            List of agent response dictionaries
        """
        responses = []
        
        self.logger.info(f"Executing {len(self.current_workflow)} agents sequentially")
        
        for i, agent in enumerate(self.current_workflow):
            try:
                self.logger.info(f"Executing agent {i+1}/{len(self.current_workflow)}")
                
                # Prepare message for this agent based on the documentation pattern
                if i == 0:
                    # First agent gets the full input
                    message_content = initial_message
                else:
                    # Subsequent agents get a clear instruction to continue the workflow
                    # They automatically see all previous messages in the thread
                    message_content = (
                        "Based on the architectural analysis provided in the previous messages, "
                        "please identify and recommend specific Azure resources, services, and "
                        "configurations that would best support the identified architecture patterns."
                    )
                
                # Execute agent with timeout
                response_content = await self._execute_single_agent(agent, message_content)
                
                # Get agent identifier
                agent_name = self._get_agent_name(agent, i)
                
                # Build response data
                response_data = {
                    "agent": agent_name,
                    "content": response_content,
                    "timestamp": self._get_timestamp(),
                    "thread_id": getattr(self.shared_thread, 'id', 'shared_thread')
                }
                responses.append(response_data)
                
                self.logger.info(f"Agent {agent_name} completed: "
                               f"{len(response_content)} characters")
                
            except Exception as e:
                self.logger.error(f"Error executing agent {i+1}: {e}")
                if "timeout" not in str(e).lower():
                    self.logger.error(f"Error details: {e}", exc_info=True)
                
                # Continue with error response
                responses.append({
                    "agent": f"agent_{i+1}_error",
                    "content": f"Error executing agent: {str(e)}",
                    "timestamp": self._get_timestamp(),
                    "error": True
                })
        
        return responses
    
    async def _execute_single_agent(self, agent: AzureAIAgent, message: str) -> str:
        """
        Execute a single agent with timeout protection.
        
        Args:
            agent: The agent to execute
            message: The message to send
            
        Returns:
            The agent's response content
        """
        try:
            async with asyncio.timeout(120):  # 2 minute timeout
                response = await agent.get_response(messages=message, thread=self.shared_thread)
                
                # Update thread reference for continuity
                self.shared_thread = response.thread
                
                # Extract response content
                return self._extract_response_content(response)
                
        except asyncio.TimeoutError:
            self.logger.warning(f"Agent timed out after 120 seconds")
            return "Agent timed out - no response received"
        except Exception as e:
            self.logger.error(f"Agent execution error: {e}")
            return f"Agent error: {str(e)}"
    
    def _extract_response_content(self, response) -> str:
        """
        Extract content from agent response.
        
        Args:
            response: The response object from agent
            
        Returns:
            Extracted content as string
        """
        if hasattr(response, 'content'):
            if hasattr(response.content, 'content'):
                return response.content.content
            elif isinstance(response.content, str):
                return response.content
            return str(response.content)
        return str(response)
    
    def _get_agent_name(self, agent: AzureAIAgent, index: int) -> str:
        """Get agent name or fallback to index-based name"""
        if hasattr(agent, 'name'):
            return agent.name
        elif hasattr(agent, 'id'):
            return agent.id
        return f"agent_{index+1}"
    
    def _prepare_workflow_input(self, input_data: Dict[str, Any]) -> str:
        """Prepare structured input for the sequential workflow"""
        
        workflow_input = {
            "task": "document_analysis",
            "instructions": [
                "Phase 1 (Architecture Extractor): Extract and analyze architectural details, "
                "patterns, and design decisions from the provided content.",
                "Phase 2 (Azure Resources Specialist): Based on the architectural analysis, "
                "identify specific Azure resources, services, configurations, and recommendations."
            ],
            "content": input_data.get("content", input_data.get("document_text", "")),
            "analysis_parameters": input_data.get("analysis_parameters", {}),
            "context": {
                "workflow_type": "sequential",
                "expected_agents": ["ArchitectureExtractor", "AzureResourcesSpecialist"],
                "maintain_context": True
            }
        }
        
        return json.dumps(workflow_input, indent=2)
    
    def _extract_agent_results(self, responses: List[Dict[str, Any]]) -> Dict[str, str]:
        """Extract agent name -> content mapping from responses"""
        return {
            response["agent"]: response["content"]
            for response in responses
            if not response.get("error", False)
        }
    
    def _structure_workflow_results(
        self,
        agent_results: Dict[str, str],
        original_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Structure the workflow results for better consumption"""
        
        structured = {
            "analysis_type": "sequential_document_analysis",
            "input_summary": {
                "content_length": len(str(original_input.get("content", ""))),
                "has_parameters": bool(original_input.get("analysis_parameters")),
                "processing_timestamp": self._get_timestamp()
            },
            "phases": {}
        }
        
        # Structure Architecture Extractor results
        if "ArchitectureExtractor" in agent_results:
            structured["phases"]["architecture_extraction"] = {
                "agent": "ArchitectureExtractor",
                "result": agent_results["ArchitectureExtractor"],
                "phase_order": 1,
                "description": "Architectural details and patterns analysis"
            }
        
        # Structure Azure Resources Specialist results
        if "AzureResourcesSpecialist" in agent_results:
            structured["phases"]["azure_resources_analysis"] = {
                "agent": "AzureResourcesSpecialist",
                "result": agent_results["AzureResourcesSpecialist"],
                "phase_order": 2,
                "description": "Azure resources and services identification"
            }
        
        # Extract key insights using delegated component
        insights = self._extract_insights_from_results(agent_results)
        structured["summary"] = insights
        
        return structured
    
    def _extract_insights_from_results(self, agent_results: Dict[str, str]) -> Dict[str, Any]:
        """Extract key insights using InsightsExtractor component"""
        
        # Convert agent_results to format expected by InsightsExtractor
        agents_results_list = [
            {"agent_name": name, "response": content, "status": "success"}
            for name, content in agent_results.items()
        ]
        
        return self.insights_extractor.extract_insights(agents_results_list)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
