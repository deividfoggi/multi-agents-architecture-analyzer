from semantic_kernel import Kernel
from semantic_kernel.agents import AzureAIAgent
from semantic_kernel.agents.azure_ai.azure_ai_agent_settings import AzureAIAgentSettings
from azure.identity.aio import DefaultAzureCredential
from microsoft_learn_mcp_plugin import MicrosoftLearnMcpPlugin
from pdf_reader_plugin import PDFReaderPlugin
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import os

@dataclass
class FoundryAgentConfig:
    """Configuration for existing Azure AI Foundry agents"""
    agent_id: str
    name: str
    description: str
    required_plugins: List[str] = None

class FoundryAgentFactory:
    """Factory that retrieves existing Azure AI Foundry agents and creates workflows"""
    
    def __init__(self, project_endpoint: str, base_model_config: Dict[str, str]):
        self.project_endpoint = project_endpoint
        self.base_model_config = base_model_config
        self.logger = logging.getLogger(__name__)
        
        # These will be created in async context manager
        self.agent_client = None
        self.credential_context = None
        self.client_context = None
        self._client_initialized = False
        
        # Cache for retrieved agents
        self._agent_cache: Dict[str, AzureAIAgent] = {}
        
        # Define your existing Azure AI Foundry agents
        self.foundry_agents = {
            "architecture_extractor": FoundryAgentConfig(
                agent_id=os.getenv("ARCHITECTURE_EXTRACTOR_AGENT_ID", "architecture-extractor-id"),
                name="Architecture-Detail-Extractor",
                description="Extrai detalhes de arquitetura de documentos e identifica padrões arquiteturais com base na documentação do Microsoft Learn via protocolo MCP.",
                required_plugins=["MicrosoftLearnMcpPlugin"]
            ),
            "azure_resources_specialist": FoundryAgentConfig(
                agent_id=os.getenv("AZURE_RESOURCES_SPECIALIST_AGENT_ID", "azure-resources-specialist-id"),
                name="Azure-Resources-Specialist",
                description="Agente Especialista em Recursos do Azure que utiliza exclusivamente a documentação do Microsoft Learn via protocolo MCP para identificar e mapear recursos de infraestrutura aos serviços apropriados do Azure. Totalmente dependente do plugin MCP para todo o conhecimento sobre Azure. Não fornece recomendações sem uma consulta bem-sucedida ao Microsoft Learn.",
                required_plugins=["MicrosoftLearnMcpPlugin"]
            )
        }
    
    async def _ensure_agent_client(self):
        """Ensures that the agent client is initialized using proper async context managers"""
        if not self._client_initialized:
            try:
                self.logger.info(f"Creating Azure AI agent client with endpoint: {self.project_endpoint}")
                
                # Store context managers for later cleanup
                self.credential_context = DefaultAzureCredential()
                self.client_context = None
                
                # Initialize async contexts
                await self.credential_context.__aenter__()
                
                # Create both the agent client and project client
                self.client_context = AzureAIAgent.create_client(
                    credential=self.credential_context,
                    endpoint=self.project_endpoint
                )
                self.agent_client = await self.client_context.__aenter__()
                

                
                self._client_initialized = True
                self.logger.info("Azure AI agent client and project client created successfully")
                
            except Exception as e:
                error_msg = f"Failed to create agent client: {str(e)}"
                self.logger.error(error_msg)
                # Clean up partially initialized contexts
                await self._cleanup_contexts()
                raise RuntimeError(error_msg) from e
    
    async def _cleanup_contexts(self):
        """Clean up async context managers"""
        try:
            if self.client_context:
                await self.client_context.__aexit__(None, None, None)
                self.client_context = None
            if self.credential_context:
                await self.credential_context.__aexit__(None, None, None)
                self.credential_context = None
        except Exception as e:
            self.logger.warning(f"Error during context cleanup: {e}")
        finally:
            self._client_initialized = False
            self.agent_client = None

    async def retrieve_foundry_agent(self, config: FoundryAgentConfig, pdf_content: str = None) -> AzureAIAgent:
        """
        Retrieves an existing Azure AI Foundry agent and creates a proper AzureAIAgent instance
        
        Args:
            config: Configuration for the agent to retrieve
            pdf_content: Optional PDF content to process
            
        Returns:
            AzureAIAgent: The configured agent ready for processing
        """
        try:
            # Check cache first
            if config.agent_id in self._agent_cache:
                self.logger.info(f"Retrieved cached agent: {config.agent_id}")
                return self._agent_cache[config.agent_id]
            
            # Ensure client is initialized
            await self._ensure_agent_client()
            
            self.logger.info(f"Retrieving Azure AI Foundry agent: {config.agent_id}")
            
            # Retrieve the existing agent from Azure AI Foundry to validate it exists
            raw_agent = await self.agent_client.agents.get_agent(config.agent_id)
            
            if not raw_agent:
                raise RuntimeError(f"Agent not found: {config.agent_id}")
                
            self.logger.info(f"Found agent in Azure AI Foundry: {config.agent_id}")
            
            # Create plugin instances for this agent based on config requirements
            plugins = []
            if config.required_plugins:
                self.logger.info(f"Creating plugins for agent {config.agent_id}: {config.required_plugins}")
                plugin_registry = {
                    #"PDFReaderPlugin": PDFReaderPlugin,
                    "MicrosoftLearnMcpPlugin": MicrosoftLearnMcpPlugin
                }
                
                for plugin_name in config.required_plugins:
                    if plugin_name in plugin_registry:
                        try:
                            plugin_instance = plugin_registry[plugin_name]()
                            plugins.append(plugin_instance)
                            self.logger.info(f"Created plugin instance: {plugin_name}")
                        except Exception as e:
                            self.logger.error(f"Failed to create plugin {plugin_name}: {e}")
                    else:
                        self.logger.warning(f"Unknown plugin requested: {plugin_name}")
            
            # Create AzureAIAgent instance using the retrieved agent information, client, and plugins
            azure_ai_agent = AzureAIAgent(
                client=self.agent_client,
                definition=raw_agent,
                plugins=plugins  # Add plugins support!
            )
            
            # Configure polling options for shorter timeouts
            from semantic_kernel.agents.open_ai.run_polling_options import RunPollingOptions
            from datetime import timedelta
            
            polling_options = RunPollingOptions(
                run_polling_timeout=timedelta(seconds=300),
                message_synchronization_delay=timedelta(seconds=2)
            )
            azure_ai_agent.polling_options = polling_options
            
            self.logger.info(f"Successfully created AzureAIAgent client: {config.agent_id}")
            self.logger.info(f"Agent has id: {hasattr(azure_ai_agent, 'id')}")
            if hasattr(azure_ai_agent, 'id'):
                self.logger.info(f"Agent id value: {azure_ai_agent.id}")
            
            # SUCCESS: Azure AI Foundry agents now properly configured with plugins!
            self.logger.info(f"=== FOUNDRY AGENT WITH PLUGINS SUCCESS ===")
            self.logger.info(f"Azure AI Foundry agent {config.agent_id} retrieved and configured successfully")
            self.logger.info(f"Required plugins: {config.required_plugins}")
            self.logger.info(f"Successfully created {len(plugins)} plugin instances")
            if plugins:
                plugin_names = [type(p).__name__ for p in plugins]
                self.logger.info(f"Active plugins: {plugin_names}")
                self.logger.info(f"MCP plugin should now be available to the agent!")
            else:
                self.logger.info(f"No plugins required for this agent")
            self.logger.info(f"=== PLUGIN CONFIGURATION COMPLETE ===")
            
            # Cache the agent client
            self._agent_cache[config.agent_id] = azure_ai_agent
            
            return azure_ai_agent
            
        except Exception as e:
            error_msg = f"Failed to retrieve foundry agent {config.agent_id}: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    async def retrieve_architecture_extractor(self) -> AzureAIAgent:
        """Retrieve the Architecture Detail Extractor agent"""
        # Use the pre-configured agent config that includes required plugins
        config = self.foundry_agents["architecture_extractor"]
        return await self.retrieve_foundry_agent(config)
    
    async def retrieve_resources_specialist(self) -> AzureAIAgent:
        """Retrieve the Azure Resources Specialist agent"""
        # Use the pre-configured agent config that includes required plugins
        config = self.foundry_agents["azure_resources_specialist"]
        return await self.retrieve_foundry_agent(config)
    
    async def get_sequential_agents(self) -> List[AzureAIAgent]:
        """Get agents in the required sequential order: Extractor first, Specialist later"""
        self.logger.info("=== GET_SEQUENTIAL_AGENTS CALLED ===")
        self.logger.info("About to retrieve architecture extractor...")
        
        arch_agent = await self.retrieve_architecture_extractor()
        self.logger.info("Architecture extractor retrieved, now retrieving resources specialist...")
        
        resources_agent = await self.retrieve_resources_specialist()
        self.logger.info("Both agents retrieved successfully")
        
        agents = [arch_agent, resources_agent]
        self.logger.info(f"Returning {len(agents)} agents")
        return agents
    
    def _create_specialized_kernel(self, config: FoundryAgentConfig) -> Kernel:
        """Create kernel with plugins for the agent"""
        # Create a simple kernel for the workflow
        kernel = Kernel()
        
        # Register plugins if specified
        if config.required_plugins:
            self._register_plugins(kernel, config.required_plugins)
        
        return kernel
    
    def _register_plugins(self, kernel: Kernel, required_plugins: List[str]):
        """Register plugins for the kernel"""
        plugin_registry = {
            #"PDFReaderPlugin": lambda: PDFReaderPlugin(),
            "MicrosoftLearnMcpPlugin": lambda: MicrosoftLearnMcpPlugin()
        }
        
        for plugin_name in required_plugins:
            if plugin_name in plugin_registry:
                try:
                    plugin_instance = plugin_registry[plugin_name]()
                    
                    kernel.add_plugin(plugin=plugin_instance)
                    self.logger.info(f"Registered plugin: {plugin_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to register plugin {plugin_name}: {e}")
    
    async def validate_agents_availability(self) -> bool:
        """Validate that required agents are available in the AI Foundry project"""
        try:
            self.logger.info("Starting agent availability validation...")
            
            # Check environment variables
            arch_agent_id = os.getenv("ARCHITECTURE_EXTRACTOR_AGENT_ID")
            resources_agent_id = os.getenv("AZURE_RESOURCES_SPECIALIST_AGENT_ID")
            
            self.logger.info(f"Architecture Extractor Agent ID: {arch_agent_id}")
            self.logger.info(f"Azure Resources Specialist Agent ID: {resources_agent_id}")
            
            if not arch_agent_id or not resources_agent_id:
                self.logger.error("Missing required agent IDs in environment variables")
                self.logger.error(f"ARCHITECTURE_EXTRACTOR_AGENT_ID: {arch_agent_id}")
                self.logger.error(f"AZURE_RESOURCES_SPECIALIST_AGENT_ID: {resources_agent_id}")
                return False
            
            # Try to retrieve agents to validate availability
            self.logger.info("Attempting to retrieve architecture extractor agent...")
            arch_agent = await self.retrieve_architecture_extractor()
            self.logger.info(f"Architecture extractor agent retrieved successfully: {arch_agent.name if hasattr(arch_agent, 'name') else 'Unknown'}")
            
            self.logger.info("Attempting to retrieve resources specialist agent...")
            resources_agent = await self.retrieve_resources_specialist()
            self.logger.info(f"Resources specialist agent retrieved successfully: {resources_agent.name if hasattr(resources_agent, 'name') else 'Unknown'}")
            
            self.logger.info("All required agents are available and validated")
            return True
            
        except Exception as e:
            self.logger.error(f"Agent availability validation failed: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    def clear_agent_cache(self):
        """Clear the agent cache to force fresh agent creation"""
        self.logger.info("=== CLEARING AGENT CACHE ===")
        self.logger.info(f"Cache contained {len(self._agent_cache)} agents: {list(self._agent_cache.keys())}")
        self._agent_cache.clear()
        self.logger.info("Agent cache cleared - next agent retrieval will trigger full initialization")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get current cache status for debugging"""
        return {
            "cache_size": len(self._agent_cache),
            "cached_agent_ids": list(self._agent_cache.keys()),
            "client_initialized": self._client_initialized
        }

    async def cleanup(self):
        """Clean up resources when factory is no longer needed"""
        self.logger.info("Cleaning up FoundryAgentFactory resources")
        await self._cleanup_contexts()
        self._agent_cache.clear()
        
    async def __aenter__(self):
        """Support for async context manager"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting async context"""
        await self.cleanup()