"""
Insights Extractor: Extracts key insights from agent results.
Follows Single Responsibility Principle (SRP).
"""
from typing import Dict, Any, List, Set
import logging
import re

logger = logging.getLogger(__name__)


class InsightsExtractor:
    """
    Responsible for extracting key insights from agent analysis results.
    Identifies patterns, Azure services, and generates summaries.
    """
    
    # Common Azure services to identify
    AZURE_SERVICES = {
        "Azure App Service", "Azure Functions", "Azure Container Apps",
        "Azure Kubernetes Service", "AKS", "Azure Storage", "Blob Storage",
        "Azure SQL", "Cosmos DB", "Azure Database", "PostgreSQL", "MySQL",
        "Azure Key Vault", "Application Insights", "Azure Monitor",
        "Azure API Management", "APIM", "Azure Service Bus", "Event Grid",
        "Azure Cache", "Redis", "Azure Front Door", "Azure CDN",
        "Azure Active Directory", "Azure AD", "Entra ID",
        "Azure Virtual Network", "VNet", "Azure Load Balancer"
    }
    
    # Architecture patterns to identify
    ARCHITECTURE_PATTERNS = {
        "microservices", "monolithic", "serverless", "event-driven",
        "layered", "n-tier", "three-tier", "multi-tier",
        "hexagonal", "clean architecture", "domain-driven",
        "CQRS", "event sourcing", "saga", "orchestration",
        "choreography", "API gateway", "BFF", "backend for frontend"
    }
    
    def extract_insights(
        self,
        agents_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract comprehensive insights from agent results.
        
        Args:
            agents_results: List of agent execution results
            
        Returns:
            Dictionary containing extracted insights
        """
        try:
            insights = {
                "azure_services": self._extract_azure_services(agents_results),
                "architecture_patterns": self._extract_patterns(agents_results),
                "key_findings": self._extract_key_findings(agents_results),
                "recommendations": self._extract_recommendations(agents_results),
                "summary": self._generate_summary(agents_results)
            }
            
            logger.info(f"Extracted insights: {len(insights['azure_services'])} services, "
                       f"{len(insights['architecture_patterns'])} patterns")
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to extract insights: {e}", exc_info=True)
            return {
                "azure_services": [],
                "architecture_patterns": [],
                "key_findings": [],
                "recommendations": [],
                "summary": "Unable to extract insights due to error",
                "error": str(e)
            }
    
    def _extract_azure_services(
        self,
        agents_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract mentioned Azure services from results."""
        services: Set[str] = set()
        
        for result in agents_results:
            response = result.get("response", "")
            if isinstance(response, str):
                response_lower = response.lower()
                for service in self.AZURE_SERVICES:
                    if service.lower() in response_lower:
                        services.add(service)
        
        return sorted(list(services))
    
    def _extract_patterns(
        self,
        agents_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract mentioned architecture patterns from results."""
        patterns: Set[str] = set()
        
        for result in agents_results:
            response = result.get("response", "")
            if isinstance(response, str):
                response_lower = response.lower()
                for pattern in self.ARCHITECTURE_PATTERNS:
                    if pattern.lower() in response_lower:
                        patterns.add(pattern)
        
        return sorted(list(patterns))
    
    def _extract_key_findings(
        self,
        agents_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract key findings from agent responses."""
        findings = []
        
        for result in agents_results:
            agent_name = result.get("agent_name", "Unknown")
            response = result.get("response", "")
            
            if isinstance(response, str) and response:
                # Look for bullet points or numbered lists
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    # Match lines starting with bullets or numbers
                    if re.match(r'^[-*•]\s+|^\d+\.\s+', line):
                        finding = re.sub(r'^[-*•]\s+|^\d+\.\s+', '', line).strip()
                        if finding and len(finding) > 20:  # Meaningful findings
                            findings.append(f"{agent_name}: {finding}")
        
        return findings[:10]  # Limit to top 10 findings
    
    def _extract_recommendations(
        self,
        agents_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract recommendations from agent responses."""
        recommendations = []
        
        for result in agents_results:
            response = result.get("response", "")
            
            if isinstance(response, str):
                # Look for recommendation keywords
                if any(keyword in response.lower() for keyword in 
                       ["recommend", "should", "consider", "suggest", "best practice"]):
                    
                    # Extract sentences with recommendations
                    sentences = response.split('.')
                    for sentence in sentences:
                        if any(keyword in sentence.lower() for keyword in 
                               ["recommend", "should", "consider", "suggest"]):
                            rec = sentence.strip()
                            if rec and len(rec) > 30:
                                recommendations.append(rec)
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _generate_summary(
        self,
        agents_results: List[Dict[str, Any]]
    ) -> str:
        """Generate a brief summary of the analysis."""
        total_agents = len(agents_results)
        successful_agents = sum(1 for r in agents_results if r.get("status") == "success")
        
        summary_parts = [
            f"Analysis completed with {successful_agents}/{total_agents} agents."
        ]
        
        # Add agent-specific summaries
        for result in agents_results[:3]:  # First 3 agents
            agent_name = result.get("agent_name", "Unknown")
            status = result.get("status", "unknown")
            if status == "success":
                response = result.get("response", "")
                if isinstance(response, str) and len(response) > 50:
                    # Get first sentence or first 150 chars
                    first_sentence = response.split('.')[0][:150]
                    summary_parts.append(f"{agent_name}: {first_sentence}...")
        
        return " ".join(summary_parts)
