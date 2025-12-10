#!/usr/bin/env python3
"""
Debug script to diagnose why AzureResourcesSpecialist is not being created.
"""

import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def diagnose():
    """Diagnose the AzureResourcesSpecialist creation issue."""
    from analyzer.agents.agent_manager import AgentManager
    
    logger.info("=" * 80)
    logger.info("DIAGNOSING AZURERESOURCESSPECIALIST CREATION ISSUE")
    logger.info("=" * 80)
    
    async with AgentManager() as manager:
        # Step 1: Check current agent status
        logger.info("\n1️⃣  Checking current agent status...")
        all_present, existing, missing = await manager.validate_agents_setup()
        
        logger.info(f"   All present: {all_present}")
        logger.info(f"   Existing ({len(existing)}): {existing}")
        logger.info(f"   Missing ({len(missing)}): {missing}")
        
        # Step 2: List all agents with details
        logger.info("\n2️⃣  Listing all agents in Azure AI Foundry...")
        all_agents = await manager.list_agents(force_refresh=True)
        
        for name, agent in all_agents.items():
            logger.info(f"   ✓ {name} (ID: {agent.id})")
        
        # Step 3: Check if specialists exist
        logger.info("\n3️⃣  Checking required specialists for orchestrator...")
        required_specialists = [
            "AzureCalculatorSpecialist",
            "AzureComputeSpecialist", 
            "AzureInfrastructureSpecialist",
            "AzureDatabaseSpecialist",
            "AzureContainersSpecialist"
        ]
        
        available_specialists = {name: agent for name, agent in all_agents.items() 
                                if name in required_specialists}
        
        logger.info(f"   Required: {required_specialists}")
        logger.info(f"   Available: {list(available_specialists.keys())}")
        
        missing_specialists = [name for name in required_specialists 
                             if name not in available_specialists]
        
        if missing_specialists:
            logger.error(f"   ❌ Missing specialists: {missing_specialists}")
            logger.error("   → Cannot create AzureResourcesSpecialist until these are created!")
            return
        else:
            logger.info(f"   ✅ All {len(required_specialists)} required specialists are available")
        
        # Step 4: If orchestrator is missing, try to create it
        if "AzureResourcesSpecialist" in missing:
            logger.info("\n4️⃣  AzureResourcesSpecialist is missing. Attempting to create it...")
            
            try:
                logger.info(f"   Calling create_agent with {len(available_specialists)} specialists...")
                agent = await manager.create_agent("AzureResourcesSpecialist", available_specialists)
                logger.info(f"   ✅ Successfully created AzureResourcesSpecialist!")
                logger.info(f"   Agent ID: {agent.id}")
                logger.info(f"   Agent Name: {agent.name}")
                
                # Verify it was created
                logger.info("\n5️⃣  Verifying agent was created...")
                all_present, existing, missing = await manager.validate_agents_setup()
                
                if all_present:
                    logger.info("   ✅ SUCCESS! All agents are now configured!")
                else:
                    logger.warning(f"   ⚠️  Still missing: {missing}")
                    
            except Exception as e:
                logger.error(f"\n❌ Failed to create AzureResourcesSpecialist:")
                logger.error(f"   Error: {e}", exc_info=True)
                
                # Additional diagnostics
                logger.info("\n🔍 Additional diagnostics:")
                logger.info(f"   - Model deployment: {manager.model_deployment_name}")
                logger.info(f"   - Project endpoint: {manager.project_endpoint}")
                logger.info(f"   - Available specialist agents: {list(available_specialists.keys())}")
                
        else:
            logger.info("\n4️⃣  AzureResourcesSpecialist already exists!")
            logger.info("   Nothing to do.")
    
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSIS COMPLETE")
    logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(diagnose())
