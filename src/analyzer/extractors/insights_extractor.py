"""
Insights Extractor: Extracts key insights from agent results.
Follows Single Responsibility Principle (SRP).
"""
from typing import Dict, Any, List, Set
import logging
import re
import json

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
        "Azure Virtual Network", "VNet", "Azure Load Balancer",
        "Azure Virtual Machines", "Azure VM", "Virtual Machines",
        "Azure Application Gateway", "Application Gateway",
        "Azure DDoS Protection", "DDoS Protection",
        "Azure Recovery Services", "Recovery Services Vault",
        "Azure Content Delivery Network", "Content Delivery Network"
    }
    
    def extract_insights(
        self,
        agents_results: List[Any]
    ) -> Dict[str, Any]:
        """
        Extract comprehensive insights from agent results.
        
        Args:
            agents_results: List of agent execution results (can be strings or dicts)
            
        Returns:
            Dictionary containing extracted insights
        """
        try:
            insights = {
                "azure_services": self._extract_azure_services(agents_results),
                "key_findings": self._extract_key_findings(agents_results),
                "recommendations": self._extract_recommendations(agents_results),
                "summary": self._generate_summary(agents_results)
            }
            
            logger.info(f"Extracted insights: {len(insights['azure_services'])} services")
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to extract insights: {e}", exc_info=True)
            return {
                "azure_services": [],
                "key_findings": [],
                "recommendations": [],
                "summary": "Unable to extract insights due to error",
                "error": str(e)
            }
    
    def _extract_azure_services(
        self,
        agents_results: List[Any]
    ) -> List[str]:
        """Extract mentioned Azure services from results."""
        services: Set[str] = set()
        
        for result in agents_results:
            # Handle different result formats
            response = ""
            if isinstance(result, dict):
                # Support both 'response' and 'content' fields
                response = result.get("response") or result.get("content", "")
            elif isinstance(result, str):
                response = result
            else:
                continue
            
            # Try to parse as JSON
            parsed_content = None
            if isinstance(response, str):
                try:
                    parsed_content = json.loads(response)
                except json.JSONDecodeError:
                    pass
            
            # Extract from structured content
            if parsed_content and isinstance(parsed_content, dict):
                # Look for summary_report.azure_services array
                summary_report = parsed_content.get("summary_report", {})
                if isinstance(summary_report, dict):
                    azure_services_list = summary_report.get("azure_services", [])
                    if isinstance(azure_services_list, list):
                        for svc_item in azure_services_list:
                            if isinstance(svc_item, dict):
                                svc_name = svc_item.get("service")
                                if svc_name:
                                    services.add(svc_name)
                            elif isinstance(svc_item, str):
                                services.add(svc_item)
                
                # Generic structured extraction
                services.update(self._extract_services_from_structured(parsed_content))
            
            # Text-based extraction
            if isinstance(response, str):
                response_lower = response.lower()
                for service in self.AZURE_SERVICES:
                    if service.lower() in response_lower:
                        services.add(service)
        
        return sorted(list(services))
    
    def _extract_services_from_structured(self, content: Any) -> Set[str]:
        """Extract Azure services from structured JSON content."""
        services = set()
        
        if isinstance(content, dict):
            # Look for service names in various fields
            for key, value in content.items():
                if "service" in key.lower() or "azure" in key.lower():
                    if isinstance(value, str):
                        # Extract service name
                        for azure_service in self.AZURE_SERVICES:
                            if azure_service.lower() in value.lower():
                                services.add(azure_service)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                services.update(self._extract_services_from_structured(item))
                            elif isinstance(item, str):
                                for azure_service in self.AZURE_SERVICES:
                                    if azure_service.lower() in item.lower():
                                        services.add(azure_service)
                elif isinstance(value, dict):
                    services.update(self._extract_services_from_structured(value))
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            services.update(self._extract_services_from_structured(item))
        
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    services.update(self._extract_services_from_structured(item))
                elif isinstance(item, str):
                    for azure_service in self.AZURE_SERVICES:
                        if azure_service.lower() in item.lower():
                            services.add(azure_service)
        
        return services
    
    def _extract_key_findings(
        self,
        agents_results: List[Any]
    ) -> List[str]:
        """Extract key findings and architecture patterns from agent responses."""
        findings = []
        
        for result in agents_results:
            agent_name = "Unknown"
            response = ""
            
            if isinstance(result, dict):
                agent_name = result.get("agent_name") or result.get("agent", "Unknown")
                response = result.get("response") or result.get("content", "")
            elif isinstance(result, str):
                response = result
            
            # Try to parse as JSON first
            parsed_content = None
            if isinstance(response, str):
                try:
                    parsed_content = json.loads(response)
                except json.JSONDecodeError:
                    pass
            
            # Extract from structured JSON content
            if parsed_content:
                # Look for architecture_patterns field
                if isinstance(parsed_content, dict):
                    patterns = parsed_content.get("architecture_patterns", [])
                    if isinstance(patterns, list):
                        findings.extend(patterns)
                    
                    # Also check in summary_report
                    summary_report = parsed_content.get("summary_report", {})
                    if isinstance(summary_report, dict):
                        patterns = summary_report.get("architecture_patterns", [])
                        if isinstance(patterns, list):
                            findings.extend(patterns)
                    
                    # Look for technical_requirements
                    tech_req = parsed_content.get("technical_requirements", [])
                    if isinstance(tech_req, list):
                        findings.extend(tech_req[:5])  # Add first 5 requirements
            
            # Fallback to text-based extraction
            if isinstance(response, str) and response and not findings:
                # Look for bullet points or numbered lists
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    # Match lines starting with bullets or numbers
                    if re.match(r'^[-*•]\s+|^\d+\.\s+', line):
                        finding = re.sub(r'^[-*•]\s+|^\d+\.\s+', '', line).strip()
                        if finding and len(finding) > 20:  # Meaningful findings
                            findings.append(finding)
        
        return findings[:15]  # Return top 15 findings
    
    def _extract_recommendations(
        self,
        agents_results: List[Any]
    ) -> List[str]:
        """Extract recommendations from agent responses."""
        recommendations = []
        
        for result in agents_results:
            response = ""
            if isinstance(result, dict):
                # Support both 'response' and 'content' fields
                response = result.get("response") or result.get("content", "")
            elif isinstance(result, str):
                response = result
            
            # Try to parse as JSON first
            parsed_content = None
            if isinstance(response, str):
                try:
                    parsed_content = json.loads(response)
                except json.JSONDecodeError:
                    pass
            
            # Extract from structured JSON content
            if parsed_content and isinstance(parsed_content, dict):
                # Look for recommendations field directly
                recs = parsed_content.get("recommendations", [])
                if isinstance(recs, list):
                    recommendations.extend(recs)
                
                # Also check in summary_report
                summary_report = parsed_content.get("summary_report", {})
                if isinstance(summary_report, dict):
                    recs = summary_report.get("recommendations", [])
                    if isinstance(recs, list):
                        recommendations.extend(recs)
                
                # Check configuration_recommendations
                config_recs = parsed_content.get("configuration_recommendations")
                if isinstance(config_recs, str) and config_recs:
                    recommendations.append(config_recs)
                elif isinstance(config_recs, list):
                    recommendations.extend(config_recs)
            
            # Fallback to text-based extraction
            if isinstance(response, str) and not recommendations:
                # Look for recommendation keywords
                if any(keyword in response.lower() for keyword in 
                       ["recommend", "should", "consider", "suggest", "best practice"]):
                    
                    # Extract sentences with recommendations
                    sentences = response.split('.')
                    for sentence in sentences:
                        if any(keyword in sentence.lower() for keyword in 
                               ["recommend", "should", "consider", "suggest"]):
                            rec = sentence.strip()
                            if rec and len(rec) > 30 and len(rec) < 300:
                                recommendations.append(rec)
        
        return recommendations[:15]  # Return top 15 recommendations
    
    def _extract_from_structured_content(self, content: Any) -> List[str]:
        """Extract recommendations from structured JSON content."""
        recommendations = []
        
        # Handle different JSON structures
        if isinstance(content, dict):
            # Look for resource_mappings with recommendations
            if "resource_mappings" in content:
                for mapping in content["resource_mappings"]:
                    if isinstance(mapping, dict):
                        component = mapping.get("component", "")
                        azure_service = mapping.get("azure_service", "")
                        recommendation = mapping.get("recommendation", "")
                        
                        if recommendation:
                            rec_text = f"{azure_service} for {component}: {recommendation}"
                            if len(rec_text) < 500:
                                recommendations.append(rec_text)
                        elif azure_service:
                            # If no explicit recommendation field, use purpose
                            purpose = mapping.get("purpose", "")
                            if purpose:
                                rec_text = f"{azure_service} for {component}: {purpose}"
                                if len(rec_text) < 500:
                                    recommendations.append(rec_text)
            
            # Look for recommendations in AzureResourcesRecommendations
            if "AzureResourcesRecommendations" in content:
                for rec in content["AzureResourcesRecommendations"]:
                    if isinstance(rec, dict):
                        aspect = rec.get("ArchitectureAspect", "")
                        services = rec.get("RecommendedAzureServices", [])
                        
                        for service in services:
                            if isinstance(service, dict):
                                service_name = service.get("ServiceName", "")
                                description = service.get("Description", "")
                                recommendation = service.get("Recommendation", service.get("BestPractice", ""))
                                
                                if service_name and recommendation:
                                    rec_text = f"{service_name}: {recommendation}"
                                    if len(rec_text) < 500:
                                        recommendations.append(rec_text)
                                elif service_name and description:
                                    rec_text = f"{service_name}: {description}"
                                    if len(rec_text) < 500:
                                        recommendations.append(rec_text)
            
            # Look for other recommendation patterns
            for key, value in content.items():
                if "recommend" in key.lower() and isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and len(item) > 30:
                            recommendations.append(item)
        
        elif isinstance(content, list):
            # Handle list of recommendations
            for item in content:
                if isinstance(item, dict):
                    # Look for mapping or recommendation fields
                    if "mapping" in item:
                        mapping = item["mapping"]
                        if isinstance(mapping, dict):
                            service = mapping.get("service", "")
                            why = mapping.get("why", "")
                            recommendation = mapping.get("recommendation", "")
                            if service and recommendation:
                                rec_text = f"{service}: {recommendation}"
                                if len(rec_text) < 500:
                                    recommendations.append(rec_text)
                            elif service and why:
                                rec_text = f"{service}: {why}"
                                if len(rec_text) < 500:
                                    recommendations.append(rec_text)
                    
                    # Look for resource recommendations
                    if "resource" in item or "component" in item:
                        resource = item.get("resource", item.get("component", ""))
                        azure_svc = item.get("azure_service", item.get("service", ""))
                        recommendation = item.get("recommendation", item.get("best_practice", ""))
                        why = item.get("why", item.get("purpose", ""))
                        
                        if azure_svc and recommendation:
                            rec_text = f"{azure_svc} for {resource}: {recommendation}"
                            if len(rec_text) < 500:
                                recommendations.append(rec_text)
                        elif azure_svc and why:
                            rec_text = f"{azure_svc} for {resource}: {why}"
                            if len(rec_text) < 500:
                                recommendations.append(rec_text)
        
        return recommendations
    
    def _generate_summary(
        self,
        agents_results: List[Any]
    ) -> str:
        """Generate a brief summary of the analysis."""
        total_agents = len(agents_results)
        successful_agents = 0
        
        summary_parts = []
        
        # Count successful agents
        for r in agents_results:
            if isinstance(r, dict):
                if r.get("status") == "success" or not r.get("error"):
                    successful_agents += 1
            elif isinstance(r, str) and r:  # Non-empty strings are considered successful
                successful_agents += 1
        
        summary_parts.append(f"Analysis completed with {successful_agents}/{total_agents} agents.")
        
        # Add agent-specific summaries
        for result in agents_results[:3]:  # First 3 agents
            agent_name = "Unknown"
            response = ""
            
            if isinstance(result, dict):
                agent_name = result.get("agent_name") or result.get("agent", "Unknown")
                response = result.get("response") or result.get("content", "")
            elif isinstance(result, str):
                response = result
            
            if isinstance(response, str) and len(response) > 50:
                # Get first sentence or first 150 chars
                first_sentence = response.split('.')[0][:150]
                summary_parts.append(f"{agent_name}: {first_sentence}...")
        
        return " ".join(summary_parts)
