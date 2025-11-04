"""
Microsoft Learn MCP Plugin for Semantic Kernel
Simple MCP plugin following PDFReaderPlugin pattern.
"""
import logging
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin


class MicrosoftLearnMcpPlugin(MCPStreamableHttpPlugin):
    """
    Microsoft Learn MCP plugin for accessing Microsoft Learn documentation and training materials.
    Provides access to Microsoft Learn content via MCP protocol.
    """
    
    def __init__(self, 
                 name: str = "MicrosoftLearn",
                 description: str = "Acessa a documentação do Microsoft Learn, arquitetura e boas práticas via protocolo MCP  ",
                 url: str = "https://learn.microsoft.com/en-us/training/support/mcp"):
        """
        Initialize the Microsoft Learn MCP plugin.
        
        Args:
            name: The name of the plugin (default: "MicrosoftLearn")
            description: The description of what the plugin does
            url: The MCP server URL for Microsoft Learn (default: Microsoft Learn MCP endpoint)
        """
        super().__init__(
            name=name,
            description=description,
            url=url
        )
        self.logger = logging.getLogger(__name__)
        
        # Store the plugin metadata
        self._name = name
        self._description = description
        self._url = url
        
        self.logger.info(f"Initialized Microsoft Learn MCP plugin: {name}")
        self.logger.info(f"Description: {description}")
        self.logger.info(f"URL: {url}")
    
    @property
    def name(self) -> str:
        """Get the plugin name."""
        return self._name
    
    @property
    def description(self) -> str:
        """Get the plugin description."""
        return self._description
    
    @property
    def url(self) -> str:
        """Get the MCP server URL."""
        return self._url