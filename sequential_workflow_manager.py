from semantic_kernel import Kernel
from semantic_kernel.agents import AzureAIAgent
from semantic_kernel.contents import ChatMessageContent
from foundry_agent_factory import FoundryAgentFactory
from typing import Dict, List, Optional, Any
import logging
import json
import asyncio

class SequentialWorkflowManager:
    """Manages sequential workflows using Semantic Kernel's native orchestration"""
    
    def __init__(self, foundry_factory: FoundryAgentFactory):
        self.foundry_factory = foundry_factory
        self.logger = logging.getLogger(__name__)
        
        # Workflow state
        self.shared_thread = None
        self.current_workflow: Optional[List[AzureAIAgent]] = None
    
    async def create_document_analysis_workflow(self) -> List[AzureAIAgent]:
        """Create sequential workflow: Architecture Extractor → Azure Resources Specialist"""
        
        try:
            # Get agents in sequential order - use direct agent invocation instead of AgentGroupChat
            agents = await self.foundry_factory.get_sequential_agents()
            
            self.logger.info(f"Retrieved {len(agents)} agents for workflow")
            for i, agent in enumerate(agents):
                self.logger.info(f"Agent {i}: type={type(agent)}, has_id={hasattr(agent, 'id')}")
                if hasattr(agent, 'id'):
                    self.logger.info(f"Agent {i} id: {agent.id}")
            
            # Store agents for sequential execution
            self.current_workflow = agents
            self.logger.info(f"Created sequential workflow with {len(agents)} agents")
            
            return agents
            
        except Exception as e:
            self.logger.error(f"Failed to create document analysis workflow: {e}")
            raise
    
    async def execute_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the sequential workflow with shared thread context"""
        
        if not self.current_workflow:
            self.current_workflow = await self.create_document_analysis_workflow()
        
        try:
            # Prepare input message
            input_text = self._prepare_workflow_input(input_data)
            input_message = ChatMessageContent(
                role="user",
                content=input_text
            )
            
            # Execute sequential workflow - invoke agents one by one
            responses = []
            agent_results = {}
            
            self.logger.info("Starting sequential agent execution...")
            current_input = input_text
            
            for i, agent in enumerate(self.current_workflow):
                try:
                    self.logger.info(f"Executing agent {i+1}/{len(self.current_workflow)}: {type(agent)}")
                    
                    # Create message for current agent
                    agent_message = ChatMessageContent(
                        role="user",
                        content=current_input
                    )
                    
                    # Invoke the agent with timeout handling
                    self.logger.info(f"Invoking agent with message: {agent_message.content[:100]}...")
                    
                    # Use the agent's invoke method with timeout handling
                    agent_responses = []
                    try:
                        # Add a timeout wrapper around the agent invoke
                        async with asyncio.timeout(120):  # 2 minute timeout
                            async for response in agent.invoke(agent_message):
                                if hasattr(response, 'content'):
                                    # Handle ChatMessageContent objects
                                    content = response.content
                                    if isinstance(content, str):
                                        agent_responses.append(content)
                                    else:
                                        agent_responses.append(str(content))
                                else:
                                    agent_responses.append(str(response))
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Agent {i+1} timed out after 120 seconds, continuing with partial results...")
                        if not agent_responses:
                            agent_responses.append(f"Agent {i+1} timed out - no response received")
                    except Exception as agent_error:
                        self.logger.warning(f"Agent {i+1} encountered error: {agent_error}, continuing...")
                        if not agent_responses:
                            agent_responses.append(f"Agent {i+1} error: {str(agent_error)}")
                    
                    # Combine all responses from this agent
                    response_content = "\n".join(agent_responses) if agent_responses else "No response"
                    
                    agent_name = f"agent_{i+1}"  # Use index-based naming for now
                    if hasattr(agent, 'name'):
                        agent_name = agent.name
                    elif hasattr(agent, 'id'):
                        agent_name = agent.id
                    
                    response_data = {
                        "agent": agent_name,
                        "content": response_content,
                        "timestamp": self._get_timestamp()
                    }
                    responses.append(response_data)
                    agent_results[agent_name] = response_content
                    
                    # Use this agent's output as input for the next agent
                    current_input = f"Previous analysis:\n{response_content}\n\nPlease continue the analysis based on the above information."
                    
                    self.logger.info(f"Received response from {agent_name}: {len(response_content)} characters")
                    
                except Exception as e:
                    self.logger.error(f"Error executing agent {i+1}: {e}")
                    # Don't log full traceback for timeout errors to reduce noise
                    if "timeout" not in str(e).lower():
                        import traceback
                        self.logger.error(f"Full traceback: {traceback.format_exc()}")
                    
                    # Continue with next agent even if one fails
                    error_response = {
                        "agent": f"agent_{i+1}_error",
                        "content": f"Error executing agent: {str(e)}",
                        "timestamp": self._get_timestamp()
                    }
                    responses.append(error_response)
            
            # Process and structure the results
            structured_result = self._structure_workflow_results(agent_results, input_data)
            
            return {
                "success": True,
                "workflow_type": "sequential_foundry_agents",
                "agents_used": [f"agent_{i+1}" for i in range(len(self.current_workflow))],
                "responses": responses,
                "structured_result": structured_result,
                "execution_summary": {
                    "total_agents": len(self.current_workflow),
                    "successful_responses": len(responses),
                    "sequential_execution": True
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in workflow execution: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow_type": "sequential_foundry_agents"
            }
    
    async def continue_conversation(self, additional_input: str) -> Dict[str, Any]:
        """Continue conversation using the same workflow context"""
        
        if not self.current_workflow:
            raise ValueError("No active workflow. Execute workflow first.")
        
        try:
            # Execute agents sequentially with the additional input
            responses = []
            current_input = additional_input
            
            for i, agent in enumerate(self.current_workflow):
                try:
                    continue_message = ChatMessageContent(
                        role="user",
                        content=current_input
                    )
                    
                    # Handle async generator response
                    agent_responses = []
                    async for response in agent.invoke(continue_message):
                        if hasattr(response, 'content'):
                            # Handle ChatMessageContent objects  
                            content = response.content
                            if isinstance(content, str):
                                agent_responses.append(content)
                            else:
                                agent_responses.append(str(content))
                        else:
                            agent_responses.append(str(response))
                    
                    response_content = "\n".join(agent_responses) if agent_responses else "No response"
                    
                    agent_name = f"agent_{i+1}"
                    if hasattr(agent, 'name'):
                        agent_name = agent.name
                    
                    response_data = {
                        "agent": agent_name,
                        "content": response_content,
                        "timestamp": self._get_timestamp()
                    }
                    responses.append(response_data)
                    
                    # Chain the responses
                    current_input = f"Previous analysis:\n{response_content}\n\nContinue analysis:"
                    
                except Exception as e:
                    self.logger.error(f"Error in continue conversation for agent {i+1}: {e}")
            
            return {
                "success": True,
                "responses": responses,
                "conversation_continued": True,
                "workflow_type": "continued_sequential"
            }
            
        except Exception as e:
            self.logger.error(f"Error continuing conversation: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow_type": "continued_sequential"
            }
    
    def _prepare_workflow_input(self, input_data: Dict[str, Any]) -> str:
        """Prepare structured input for the sequential workflow"""
        
        workflow_input = {
            "task": "document_analysis",
            "instructions": [
                "Phase 1 (Architecture Extractor): Extract and analyze architectural details, patterns, and design decisions from the provided content.",
                "Phase 2 (Azure Resources Specialist): Based on the architectural analysis, identify specific Azure resources, services, configurations, and recommendations."
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
    
    def _structure_workflow_results(self, agent_results: Dict[str, str], 
                                  original_input: Dict[str, Any]) -> Dict[str, Any]:
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
        
        # Try to extract key insights
        structured["summary"] = self._extract_key_insights(agent_results)
        
        return structured
    
    def _extract_key_insights(self, agent_results: Dict[str, str]) -> Dict[str, Any]:
        """Extract key insights from agent results"""
        
        insights = {
            "architecture_patterns": [],
            "azure_services": [],
            "recommendations": [],
            "complexity_assessment": "unknown"
        }
        
        # Basic keyword extraction (in a real implementation, you might use NLP)
        all_content = " ".join(agent_results.values()).lower()
        
        # Common architecture patterns
        patterns = ["microservices", "monolith", "serverless", "event-driven", "layered", "hexagonal"]
        insights["architecture_patterns"] = [p for p in patterns if p in all_content]
        
        # Common Azure services
        services = ["app service", "azure functions", "cosmos db", "sql database", "storage account", 
                   "service bus", "event grid", "api management", "container instances", "kubernetes"]
        insights["azure_services"] = [s for s in services if s in all_content]
        
        return insights
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def reset_workflow(self):
        """Reset the workflow state for a new analysis"""
        self.shared_thread = None
        self.current_workflow = None
        self.logger.info("Workflow state reset")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        return {
            "has_active_workflow": self.current_workflow is not None,
            "agents_count": len(self.current_workflow) if self.current_workflow else 0
        }