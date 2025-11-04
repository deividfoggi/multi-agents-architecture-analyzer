import logging
import os
import uvicorn

# Configure root logger to handle all modules
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Add console handler to root logger
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# Get logger for this module
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting API server on {host}:{port}")
    logger.info(f"Reload mode: {reload}")
    logger.info("Using standard asyncio loop to avoid uvloop conflicts")
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        loop="asyncio"  # Force standard asyncio instead of uvloop
    )
