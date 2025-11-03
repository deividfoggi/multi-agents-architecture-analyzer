import logging
import os
import uvicorn

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting Essay Evaluation API server on {host}:{port}")
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
