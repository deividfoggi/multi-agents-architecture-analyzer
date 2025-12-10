"""
Microsoft Agent Framework Workflow Manager
Replaces Azure AI Agents SDK with direct MCP connectivity and explicit orchestration.
"""
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import json
import asyncio
import requests
from datetime import datetime

# Agent Framework imports
from agent_framework import ChatAgent, HostedMCPTool
from agent_framework.azure._chat_client import AzureOpenAIChatClient


class AgentFrameworkWorkflowManager:
    """
    Manages workflows using Microsoft Agent Framework.
    Provides direct MCP connectivity and explicit orchestration.
    
    Workflow:
    1. Extractor extracts architecture details
    2. Orchestrator analyzes and delegates to specialists (Container, Compute, Infrastructure, Database)
    3. Specialists use MCP to find Azure resources
    4. Orchestrator delegates to Calculator for pricing
    5. Orchestrator compiles final response
    """
    
    def __init__(
        self,
        azure_endpoint: str,
        api_key: str,
        deployment_name: str,
        api_version: str = "2024-05-01-preview",
        mcp_server_url: str = "https://learn.microsoft.com/api/mcp"
    ):
        self.logger = logging.getLogger(__name__)
        self.azure_endpoint = azure_endpoint
        self.api_key = api_key
        self.deployment_name = deployment_name
        self.api_version = api_version
        self.mcp_server_url = mcp_server_url
        
        # Agent definitions (will be created lazily)
        self.agents: Dict[str, Any] = {}
        
        # Create Azure OpenAI chat client
        self.chat_client = AzureOpenAIChatClient(
            endpoint=azure_endpoint,
            api_key=api_key,
            deployment_name=deployment_name,
            api_version=api_version
        )
        
        self.logger.info("Agent Framework initialized successfully")
        
        # Initialize agents
        self._initialize_agents()
    
    def _load_prompt(self, filename: str) -> str:
        """Load prompt template from file"""
        # Try different potential locations
        potential_paths = [
            Path(__file__).parent.parent.parent / filename,
            Path(__file__).parent.parent.parent.parent / filename,
            Path.cwd() / filename
        ]
        
        for prompt_path in potential_paths:
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8")
        
        self.logger.warning(f"Prompt file not found: {filename}")
        return f"You are a helpful AI agent. (Default instructions - {filename} not found)"
    
    def _initialize_agents(self):
        """Create all agents with their tools"""
        
        self.logger.info("Initializing agents...")
        
        try:
            from agent_framework import AIFunction
            
            # 1. Extractor Agent (no tools)
            self.logger.info("Creating ArchitectureDetailExtractor agent")
            self.agents["extractor"] = ChatAgent(
                chat_client=self.chat_client,
                name="ArchitectureDetailExtractor",
                instructions=self._load_prompt("prompt_template_extractor.txt")
            )
            
            # 2. MCP Tool for specialists
            self.logger.info(f"Creating MCP tool for: {self.mcp_server_url}")
            mcp_tool = HostedMCPTool(
                name="microsoft_learn",
                description="Access Microsoft Learn documentation for Azure services",
                url=self.mcp_server_url
            )
            
            # 3. Specialist Agents (with MCP)
            specialists = [
                ("container", "AzureContainersSpecialist", "prompt_template_containers.txt"),
                ("compute", "AzureComputeSpecialist", "prompt_template_compute.txt"),
                ("infrastructure", "AzureInfrastructureSpecialist", "prompt_template_infrastructure.txt"),
                ("database", "AzureDatabaseSpecialist", "prompt_template_database.txt")
            ]
            
            for key, name, prompt_file in specialists:
                self.logger.info(f"Creating {name} agent with MCP tool")
                self.agents[key] = ChatAgent(
                    chat_client=self.chat_client,
                    name=name,
                    instructions=self._load_prompt(prompt_file),
                    tools=[mcp_tool]
                )
            
            # 4. Pricing Tool Function
            pricing_tool = AIFunction(
                name="get_azure_pricing",
                func=self._get_azure_pricing,
                description="""Get Azure resource pricing from Azure Retail Prices API using flexible contains filters.
                
Args:
    service_name: Azure service name (e.g., "Virtual Machines", "Storage", "Application Gateway")
    sku_name: SKU identifier for filtering (e.g., "Standard_D2s_v3", "Premium_LRS", "WAF_v2")
    region: Azure region (default: "eastus", e.g., "westus2", "brazilsouth")
    product_name: Optional - Specific product name for contains filter (e.g., "Premium Block Blob", "Application Gateway WAF v2")
    meter_name: Optional - Specific meter name for contains filter (e.g., "GRS Data Stored", "P1 v3")
    
Returns:
    Pricing information including retail price per unit, currency, unit of measure, and product details.
    Uses multiple strategies with contains filters to find pricing flexibly.
    
Examples:
    - Virtual Machine: get_azure_pricing("Virtual Machines", "Standard_D2s_v3", "eastus")
    - Storage: get_azure_pricing("Storage", "Premium_LRS", "eastus", product_name="Premium Block Blob", meter_name="LRS")
    - App Gateway: get_azure_pricing("Application Gateway", "WAF_v2", "eastus", product_name="Application Gateway WAF v2")
    - Backup: get_azure_pricing("Backup", "Standard", "eastus", meter_name="GRS Data Stored")"""
            )
            
            # 5. Calculator Agent (with Pricing API tool)
            self.logger.info("Creating AzureCalculatorSpecialist agent with pricing tool")
            self.agents["calculator"] = ChatAgent(
                chat_client=self.chat_client,
                name="AzureCalculatorSpecialist",
                instructions=self._load_prompt("prompt_template_cost_calculator.txt"),
                tools=[pricing_tool],
                temperature=0.5,
                top_p=0.5
            )
            
            # 6. Orchestrator Agent (delegates to specialists)
            self.logger.info("Creating AzureResourcesSpecialist orchestrator agent")
            self.agents["orchestrator"] = ChatAgent(
                chat_client=self.chat_client,
                name="AzureResourcesSpecialist",
                instructions=self._load_prompt("prompt_template_azure_resources_specialist.txt"),
                temperature=0.75,
                top_p=0.75
            )
            
            self.logger.info(f"Successfully initialized {len(self.agents)} agents")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agents: {e}")
            raise
    
    def _get_azure_pricing(
        self,
        service_name: str,
        sku_name: str,
        region: str = "eastus",
        product_name: str = None,
        meter_name: str = None
    ) -> Dict[str, Any]:
        """
        Query Azure Retail Prices API for SKU pricing using flexible contains filters.
        Implementation of the pricing tool function.
        
        Args:
            service_name: Azure service name (e.g., 'Virtual Machines', 'Storage', 'Application Gateway')
            sku_name: SKU identifier (used in contains filter for productName or armSkuName)
            region: Azure region (default: eastus)
            product_name: Optional specific product name for filtering
            meter_name: Optional specific meter name for filtering
        
        Returns:
            Dict with pricing information or error details
        """
        base_url = "https://prices.azure.com/api/retail/prices"
        
        # Build OData filter with contains for flexible matching
        filters = [
            f"serviceName eq '{service_name}'",
            f"armRegionName eq '{region}'"
        ]
        
        # Try multiple strategies to find pricing
        strategies = []
        
        # Strategy 1: Exact armSkuName match
        if sku_name:
            strategies.append([
                *filters,
                f"armSkuName eq '{sku_name}'",
                "priceType eq 'Consumption'"
            ])
        
        # Strategy 2: Contains in productName
        if sku_name and not product_name:
            strategies.append([
                *filters,
                f"contains(productName, '{sku_name}')",
                "priceType eq 'Consumption'"
            ])
        
        # Strategy 3: Custom product_name with contains
        if product_name:
            strategy_filters = [
                *filters,
                f"contains(productName, '{product_name}')"
            ]
            if meter_name:
                strategy_filters.append(f"contains(meterName, '{meter_name}')")
            else:
                strategy_filters.append("priceType eq 'Consumption'")
            strategies.append(strategy_filters)
        
        # Strategy 4: Contains in meterName
        if meter_name and not product_name:
            strategies.append([
                *filters,
                f"contains(meterName, '{meter_name}')",
                "priceType eq 'Consumption'"
            ])
        
        # Try each strategy until we find pricing
        for strategy_filters in strategies:
            filter_str = " and ".join(strategy_filters)
            params = {
                "$filter": filter_str,
                "api-version": "2023-01-01-preview"
            }
            
            try:
                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get("Items"):
                    item = data["Items"][0]
                    return {
                        "success": True,
                        "service": service_name,
                        "sku": sku_name,
                        "region": region,
                        "retail_price": item.get("retailPrice", 0),
                        "unit_of_measure": item.get("unitOfMeasure", "1 Hour"),
                        "currency": item.get("currencyCode", "USD"),
                        "product_name": item.get("productName", ""),
                        "meter_name": item.get("meterName", ""),
                        "arm_sku_name": item.get("armSkuName", ""),
                        "query_used": filter_str
                    }
            except Exception as e:
                self.logger.warning(f"Pricing API strategy failed: {e}")
                continue
        
        # All strategies failed
        return {
            "success": False,
            "error": "No pricing found with any strategy",
            "service": service_name,
            "sku": sku_name,
            "region": region,
            "note": "Service may not be available in Retail Prices API (e.g., CDN, DDoS Protection flat fee)"
        }
    
    async def execute_workflow(
        self,
        document_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete architecture analysis workflow.
        
        Workflow:
        1. Extractor extracts architecture details
        2. Orchestrator analyzes and delegates to specialists
        3. Specialists return Azure resource recommendations (with MCP)
        4. Orchestrator delegates to calculator for pricing
        5. Orchestrator compiles final response
        """
        
        start_time = datetime.now()
        self.logger.info("Starting Agent Framework workflow execution")
        
        workflow_results = []
        
        try:
            # Step 1: Extract architecture details
            self.logger.info("Step 1: Running ArchitectureDetailExtractor")
            extractor_result = await self.agents["extractor"].run(
                f"""Analyze this architecture document and extract:
                - Architecture patterns used
                - Components and technologies mentioned
                - Infrastructure requirements
                - Data storage needs
                - Scalability and availability requirements
                
                Document:
                {document_content}
                
                Provide a detailed analysis that can be used by Azure specialists to recommend appropriate services.
                """
            )
            
            architecture_details = extractor_result.text
            self.logger.info(f"Extractor completed: {len(architecture_details)} chars")
            
            workflow_results.append({
                "agent": "ArchitectureDetailExtractor",
                "response": architecture_details,
                "duration": (datetime.now() - start_time).total_seconds()
            })
            
            # Step 2: Orchestrator analyzes and identifies which specialists to consult
            self.logger.info("Step 2: Running AzureResourcesSpecialist (orchestrator) - Initial Analysis")
            
            orchestrator_prompt = f"""
            You are the Azure Resources Specialist orchestrator. Based on the architecture analysis below,
            identify which specialist agents you need to consult and what specific questions to ask them.
            
            ARCHITECTURE ANALYSIS:
            {architecture_details}
            
            AVAILABLE SPECIALISTS:
            1. Container Specialist - For Kubernetes, container orchestration, Docker, AKS, ACR
            2. Compute Specialist - For VMs, App Service, Functions, serverless compute
            3. Infrastructure Specialist - For networking, load balancers, VPN, gateways, security
            4. Database Specialist - For databases, caching, storage accounts, data services
            
            YOUR TASK:
            Analyze the architecture and for EACH relevant specialist, create a delegation request.
            Format: "DELEGATE TO [SPECIALIST]: [specific question about Azure resources for this domain]"
            
            Only delegate to specialists whose domains are clearly needed based on the architecture.
            Be specific in your questions to help specialists provide the best Azure service recommendations.
            """
            
            orchestrator_analysis = await self.agents["orchestrator"].run(orchestrator_prompt)
            orchestrator_response = orchestrator_analysis.text
            
            self.logger.info("Orchestrator completed initial analysis")
            
            # Step 3: Parse delegation requests and execute specialists
            specialist_results = {}
            
            # Map specialist keywords to agent keys
            specialist_mapping = {
                "CONTAINER": ("container", "AzureContainersSpecialist"),
                "COMPUTE": ("compute", "AzureComputeSpecialist"),
                "INFRASTRUCTURE": ("infrastructure", "AzureInfrastructureSpecialist"),
                "DATABASE": ("database", "AzureDatabaseSpecialist")
            }
            
            for keyword, (agent_key, agent_name) in specialist_mapping.items():
                if f"DELEGATE TO {keyword}" in orchestrator_response.upper():
                    self.logger.info(f"Step 3: Executing {agent_name}")
                    
                    specialist_prompt = f"""
                    You are the {agent_name}. You have been consulted by the orchestrator
                    to provide Azure service recommendations for your domain.
                    
                    ARCHITECTURE ANALYSIS:
                    {architecture_details}
                    
                    ORCHESTRATOR'S QUESTION:
                    {orchestrator_response}
                    
                    YOUR TASK:
                    Use the Microsoft Learn MCP tool to search for and recommend the BEST Azure services
                    in your domain ({agent_name.replace('Azure', '').replace('Specialist', '').strip()}).
                    
                    For EACH recommended service:
                    1. Service name and purpose
                    2. Specific SKU recommendations with justification
                    3. Configuration recommendations
                    4. Why this service fits the architecture
                    
                    Be specific about SKU names (e.g., "Standard_D2s_v3", "S1", "Premium_LRS").
                    Focus on production-ready, scalable solutions.
                    """
                    
                    result = await self.agents[agent_key].run(specialist_prompt)
                    specialist_results[agent_key] = result.text
                    
                    self.logger.info(f"{agent_name} completed: {len(result.text)} chars")
                    
                    workflow_results.append({
                        "agent": agent_name,
                        "response": result.text,
                        "duration": (datetime.now() - start_time).total_seconds()
                    })
            
            # If no specialists were delegated, use all of them
            if not specialist_results:
                self.logger.warning("No specialists explicitly delegated, running all specialists")
                
                for agent_key, agent_name in [
                    ("container", "AzureContainersSpecialist"),
                    ("compute", "AzureComputeSpecialist"),
                    ("infrastructure", "AzureInfrastructureSpecialist"),
                    ("database", "AzureDatabaseSpecialist")
                ]:
                    specialist_prompt = f"""
                    Based on this architecture analysis, recommend Azure services in your domain:
                    
                    {architecture_details}
                    
                    Use the Microsoft Learn MCP tool to find appropriate services.
                    Provide specific SKU recommendations with justification.
                    """
                    
                    result = await self.agents[agent_key].run(specialist_prompt)
                    specialist_results[agent_key] = result.text
                    
                    workflow_results.append({
                        "agent": agent_name,
                        "response": result.text,
                        "duration": (datetime.now() - start_time).total_seconds()
                    })
            
            # Step 4: Calculator Specialist for pricing
            self.logger.info("Step 4: Running AzureCalculatorSpecialist")
            
            all_recommendations = "\n\n".join([
                f"=== {key.upper()} SPECIALIST RECOMMENDATIONS ===\n{result}"
                for key, result in specialist_results.items()
            ])
            
            calculator_prompt = f"""
            Based on these Azure resource recommendations, calculate pricing estimates:
            
            {all_recommendations}
            
            YOUR TASK:
            1. Identify all Azure services and SKUs mentioned
            2. For EACH SKU, use the get_azure_pricing tool to fetch current pricing
            3. Calculate cost estimates:
               - Hourly cost
               - Monthly cost (730 hours)
               - Annual cost
            4. Provide a summary table with all costs
            
            Use realistic assumptions for region (default: eastus) and include currency.
            If a SKU's pricing is not found, note it and provide a rough estimate if possible.
            """
            
            calculator_result = await self.agents["calculator"].run(calculator_prompt)
            pricing_info = calculator_result.text
            
            self.logger.info(f"Calculator completed: {len(pricing_info)} chars")
            
            workflow_results.append({
                "agent": "AzureCalculatorSpecialist",
                "response": pricing_info,
                "duration": (datetime.now() - start_time).total_seconds()
            })
            
            # Step 5: Final compilation by orchestrator
            self.logger.info("Step 5: Final compilation by orchestrator")
            
            final_prompt = f"""
            Compile the comprehensive architecture analysis report:
            
            ORIGINAL ARCHITECTURE:
            {architecture_details}
            
            SPECIALIST RECOMMENDATIONS:
            {all_recommendations}
            
            PRICING ESTIMATES:
            {pricing_info}
            
            YOUR TASK:
            Create a well-structured final report with:
            
            1. AZURE SERVICES: List each recommended Azure service with its SKU
            2. ARCHITECTURE PATTERNS: Key architectural patterns identified
            3. RECOMMENDATIONS: Best practices and implementation suggestions
            4. COST SUMMARY: Total estimated costs (monthly and annual)
            
            Format the response clearly for easy parsing and presentation to the user.
            """
            
            final_result = await self.agents["orchestrator"].run(final_prompt)
            final_response = final_result.text
            
            workflow_results.append({
                "agent": "AzureResourcesSpecialist",
                "response": final_response,
                "duration": (datetime.now() - start_time).total_seconds()
            })
            
            # Step 6: Extract structured insights and format results
            self.logger.info("Step 6: Extracting insights and formatting results")
            
            from analyzer.extractors.insights_extractor import InsightsExtractor
            from analyzer.processors.result_formatter import ResultFormatter
            
            insights_extractor = InsightsExtractor()
            result_formatter = ResultFormatter()
            
            # Extract insights from all responses
            all_responses = [wr["response"] for wr in workflow_results]
            insights = insights_extractor.extract_insights(all_responses)
            
            # Format final results
            formatted_result = result_formatter.format_workflow_result(
                agents_results=workflow_results,
                insights=insights,
                status="success"
            )
            
            # Add metadata
            formatted_result["metadata"] = {
                **(metadata or {}),
                "workflow_duration": (datetime.now() - start_time).total_seconds(),
                "workflow_type": "agent_framework",
                "mcp_server": self.mcp_server_url,
                "total_agents": len(self.agents),
                "agents_executed": len(workflow_results)
            }
            
            self.logger.info(
                f"Agent Framework workflow completed successfully in "
                f"{formatted_result.get('metadata', {}).get('workflow_duration', 0):.2f}s"
            )
            
            return formatted_result
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)
            
            # Return error response with partial results
            return {
                "error": str(e),
                "workflow_results": workflow_results,
                "metadata": {
                    **(metadata or {}),
                    "workflow_duration": (datetime.now() - start_time).total_seconds(),
                    "workflow_type": "agent_framework",
                    "status": "failed"
                }
            }
    
    def reinitialize_agents(self):
        """
        Reinitialize all agents by clearing the current agents and creating new ones.
        This is useful when prompt templates have been modified.
        """
        self.logger.info("Reinitializing all agents...")
        
        # Clear existing agents
        old_agent_names = list(self.agents.keys())
        self.agents.clear()
        
        # Reinitialize all agents
        self._initialize_agents()
        
        self.logger.info(f"Successfully reinitialized {len(self.agents)} agents")
        
        return {
            "deleted_agents": old_agent_names,
            "created_agents": list(self.agents.keys())
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up Agent Framework resources")
        # Agent Framework handles cleanup automatically
        pass
