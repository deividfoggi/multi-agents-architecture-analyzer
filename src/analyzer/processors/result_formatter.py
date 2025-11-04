"""
Result Formatter: Handles formatting of workflow results.
Follows Single Responsibility Principle (SRP).
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResultFormatter:
    """
    Responsible for formatting workflow results in a consistent structure.
    Handles both foundry agent results and continuation results.
    """
    
    def format_foundry_result(
        self,
        foundry_result: Dict[str, Any],
        status: str = "success"
    ) -> Dict[str, Any]:
        """
        Format results from Azure AI Foundry agents.
        
        Args:
            foundry_result: Raw result from foundry workflow
            status: Overall status of the workflow
            
        Returns:
            Formatted result dictionary
        """
        # Extract workflow info from foundry_result
        success = foundry_result.get("success", status == "success")
        processing_type = foundry_result.get("workflow_type", "sequential_foundry_agents")
        agents_used = foundry_result.get("agents_used", [])
        shared_thread_id = foundry_result.get("shared_thread_id")
        
        return {
            "success": success,
            "status": status,
            "result": foundry_result,
            "timestamp": datetime.now().isoformat(),
            "processing_type": processing_type,
            "foundry_available": True,
            "agents_used": agents_used,
            "shared_thread_id": shared_thread_id
        }
    
    def format_continuation_result(
        self,
        continuation_result: Dict[str, Any],
        status: str = "success"
    ) -> Dict[str, Any]:
        """
        Format results from continuation workflows.
        
        Args:
            continuation_result: Raw continuation result
            status: Overall status of the continuation
            
        Returns:
            Formatted result dictionary
        """
        success = continuation_result.get("success", status == "success")
        
        return {
            "success": success,
            "status": status,
            "result": continuation_result,
            "timestamp": datetime.now().isoformat()
        }
    
    def format_error(
        self,
        error: Exception,
        context: str = "processing"
    ) -> Dict[str, Any]:
        """
        Format error responses consistently.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            
        Returns:
            Formatted error dictionary
        """
        return {
            "status": "error",
            "error": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
    
    def format_agent_response(
        self,
        agent_name: str,
        response: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format individual agent responses.
        
        Args:
            agent_name: Name of the agent
            response: Agent response content
            additional_data: Optional additional data to include
            
        Returns:
            Formatted agent response
        """
        result = {
            "agent": agent_name,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
        
        if additional_data:
            result.update(additional_data)
        
        return result
    
    def format_workflow_result(
        self,
        agents_results: List[Dict[str, Any]],
        insights: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ) -> Dict[str, Any]:
        """
        Format complete workflow results with agent outputs and insights.
        
        Args:
            agents_results: List of agent result dictionaries
            insights: Optional extracted insights
            status: Overall workflow status
            
        Returns:
            Formatted workflow result
        """
        result = {
            "status": status,
            "agents_results": agents_results,
            "timestamp": datetime.now().isoformat()
        }
        
        if insights:
            result["insights"] = insights
        
        return result
