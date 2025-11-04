"""
Microsoft Learn MCP Plugin for Semantic Kernel
Simple MCP plugin following PDFReaderPlugin pattern.
"""
import logging
import traceback
from typing import Dict, Any, Optional
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
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"=== MCP PLUGIN INIT START ===")
        self.logger.info(f"Initializing Microsoft Learn MCP plugin: {name}")
        self.logger.info(f"Description: {description}")
        self.logger.info(f"URL: {url}")
        
        try:
            super().__init__(
                name=name,
                description=description,
                url=url
            )
            
            # Store the plugin metadata
            self._name = name
            self._description = description
            self._url = url
            self._is_connected = False
            self._connection_error = None
            
            self.logger.info(f"=== MCP PLUGIN INIT SUCCESS ===")
            
        except Exception as e:
            self.logger.error(f"=== MCP PLUGIN INIT FAILED ===")
            self.logger.error(f"Error during MCP plugin initialization: {str(e)}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    async def connect(self):
        """Connect to the MCP server with detailed logging"""
        self.logger.info(f"=== MCP PLUGIN CONNECT START ===")
        self.logger.info(f"Attempting to connect to MCP server: {self._url}")
        
        try:
            await super().connect()
            self._is_connected = True
            self._connection_error = None
            self.logger.info(f"=== MCP PLUGIN CONNECT SUCCESS ===")
            return True
            
        except Exception as e:
            self._is_connected = False
            self._connection_error = str(e)
            self.logger.error(f"=== MCP PLUGIN CONNECT FAILED ===")
            self.logger.error(f"Failed to connect to MCP server: {str(e)}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    async def disconnect(self):
        """Disconnect from the MCP server with detailed logging"""
        self.logger.info(f"=== MCP PLUGIN DISCONNECT START ===")
        
        try:
            await super().disconnect()
            self._is_connected = False
            self.logger.info(f"=== MCP PLUGIN DISCONNECT SUCCESS ===")
            
        except Exception as e:
            self.logger.error(f"=== MCP PLUGIN DISCONNECT FAILED ===")
            self.logger.error(f"Error during disconnect: {str(e)}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    async def call_function(self, function_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a function on the MCP server with detailed logging"""
        self.logger.info(f"=== MCP FUNCTION CALL START ===")
        self.logger.info(f"Function: {function_name}")
        self.logger.info(f"Arguments: {arguments}")
        self.logger.info(f"Connected: {self._is_connected}")
        
        if not self._is_connected:
            self.logger.warning(f"MCP plugin not connected. Connection error: {self._connection_error}")
            
        try:
            result = await super().call_function(function_name, arguments)
            self.logger.info(f"=== MCP FUNCTION CALL SUCCESS ===")
            self.logger.info(f"Result type: {type(result)}")
            self.logger.info(f"Result preview: {str(result)[:200]}...")
            return result
            
        except Exception as e:
            self.logger.error(f"=== MCP FUNCTION CALL FAILED ===")
            self.logger.error(f"Error calling function {function_name}: {str(e)}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get current plugin status for debugging"""
        status = {
            "name": self._name,
            "url": self._url,
            "connected": self._is_connected,
            "connection_error": self._connection_error,
            "description": self._description
        }
        self.logger.info(f"=== MCP PLUGIN STATUS ===: {status}")
        return status
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the MCP connection and return status"""
        self.logger.info(f"=== MCP CONNECTION TEST START ===")
        
        test_result = {
            "plugin_name": self._name,
            "url": self._url,
            "connection_successful": False,
            "error": None,
            "functions_available": []
        }
        
        try:
            if not self._is_connected:
                self.logger.info("Plugin not connected, attempting to connect...")
                await self.connect()
            
            # Try to list available functions
            try:
                functions = await self.list_functions()
                test_result["functions_available"] = functions
                self.logger.info(f"Available MCP functions: {functions}")
                
            except Exception as func_error:
                self.logger.warning(f"Could not list functions: {func_error}")
                test_result["functions_available"] = f"Error: {str(func_error)}"
            
            test_result["connection_successful"] = True
            self.logger.info(f"=== MCP CONNECTION TEST SUCCESS ===")
            
        except Exception as e:
            test_result["error"] = str(e)
            self.logger.error(f"=== MCP CONNECTION TEST FAILED ===")
            self.logger.error(f"Connection test failed: {str(e)}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            
        self.logger.info(f"MCP Test Result: {test_result}")
        return test_result
    
    async def list_functions(self):
        """List available functions with logging"""
        self.logger.info(f"=== MCP LIST FUNCTIONS START ===")
        
        try:
            functions = await super().list_functions()
            self.logger.info(f"=== MCP LIST FUNCTIONS SUCCESS ===")
            self.logger.info(f"Available functions: {functions}")
            return functions
            
        except Exception as e:
            self.logger.error(f"=== MCP LIST FUNCTIONS FAILED ===")
            self.logger.error(f"Error listing functions: {str(e)}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def __del__(self):
        """Log when plugin is being destroyed"""
        try:
            self.logger.info(f"=== MCP PLUGIN DESTRUCTION ===")
            self.logger.info(f"Plugin {self._name} is being destroyed")
        except:
            # Ignore logging errors during destruction
            pass