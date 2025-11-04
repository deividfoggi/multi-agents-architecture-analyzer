"""
Microsoft Learn MCP Plugin for Semantic Kernel
Simple MCP plugin following PDFReaderPlugin pattern.
"""
import logging
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin


class MicrosoftLearnMcpPlugin(MCPStreamableHttpPlugin):
    """
    Simple Microsoft Learn MCP plugin - just inherits from MCPStreamableHttpPlugin
    Following the same pattern as PDFReaderPlugin
    """
    
    def __init__(self, mcp_server_url: str = "https://learn.microsoft.com/en-us/training/support/mcp"):
        super().__init__(mcp_server_url=mcp_server_url)
        self.logger = logging.getLogger(__name__)