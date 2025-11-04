"""
Agent Initialization Manager: Handles agent initialization and validation.
Follows Single Responsibility Principle (SRP).
"""
from typing import Optional
import logging
from foundry_agent_factory import FoundryAgentFactory

logger = logging.getLogger(__name__)


class AgentInitializationManager:
    """
    Responsible for initializing and validating Azure AI Foundry agents.
    Manages the foundry factory lifecycle.
    """
    
    def __init__(self):
        self._foundry_factory: Optional[FoundryAgentFactory] = None
        self._is_initialized: bool = False
    
    async def initialize(self) -> bool:
        """
        Initialize the foundry agent factory.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._is_initialized:
            logger.info("Agent factory already initialized")
            return True
        
        try:
            logger.info("Initializing foundry agent factory...")
            self._foundry_factory = FoundryAgentFactory()
            await self._foundry_factory.initialize()
            self._is_initialized = True
            logger.info("Foundry agent factory initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize foundry agent factory: {e}", exc_info=True)
            self._is_initialized = False
            return False
    
    async def validate_agents(self) -> bool:
        """
        Validate that all required agents are available.
        
        Returns:
            True if agents are available, False otherwise
        """
        if not self._is_initialized or not self._foundry_factory:
            logger.error("Cannot validate agents: factory not initialized")
            return False
        
        try:
            agents = await self._foundry_factory.get_agents()
            if not agents:
                logger.error("No agents available from foundry factory")
                return False
            
            logger.info(f"Validated {len(agents)} agents from foundry factory")
            return True
        except Exception as e:
            logger.error(f"Failed to validate agents: {e}", exc_info=True)
            return False
    
    def get_factory(self) -> Optional[FoundryAgentFactory]:
        """
        Get the initialized foundry factory.
        
        Returns:
            The foundry factory instance, or None if not initialized
        """
        return self._foundry_factory
    
    def is_initialized(self) -> bool:
        """
        Check if the factory is initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._is_initialized
    
    async def reset(self) -> None:
        """
        Reset the initialization state.
        """
        self._foundry_factory = None
        self._is_initialized = False
        logger.info("Agent initialization manager reset")
