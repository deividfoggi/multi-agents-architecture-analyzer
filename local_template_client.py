import os
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler for console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class LocalTemplateClient:
    """
    Client for retrieving prompt templates from local filesystem.
    Maintains the same interface as AzureBlobTemplateClient for compatibility.
    Template file path can be provided as an argument or via LOCAL_TEMPLATE_FILE_PATH env var.
    """
    def __init__(self, template_file_path: str = None):
        # Get template file path from argument or environment
        if template_file_path is None:
            template_file_path = os.getenv("LOCAL_TEMPLATE_FILE_PATH", "essay.yaml")
        
        # Convert to absolute path if it's relative
        if not os.path.isabs(template_file_path):
            # Assume relative to project root (where this script is located)
            project_root = Path(__file__).parent
            template_file_path = project_root / template_file_path
        
        self.template_file_path = Path(template_file_path)
        
        # Validate that the template file exists
        if not self.template_file_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_file_path}")
        
        logger.info(f"LocalTemplateClient initialized with template: {self.template_file_path}")

    def get_template(self, file_name: str = None) -> str:
        """
        Read and return the contents of a local template file as a string.
        If file_name is provided, it overrides the default template file path.
        Maintains compatibility with AzureBlobTemplateClient interface.
        """
        try:
            # If file_name is provided, use it instead of the default path
            if file_name is not None:
                # Handle relative paths
                if not os.path.isabs(file_name):
                    project_root = Path(__file__).parent
                    file_path = project_root / file_name
                else:
                    file_path = Path(file_name)
            else:
                file_path = self.template_file_path
            
            # Check if file exists
            if not file_path.exists():
                logger.error(f"Template file not found: {file_path}")
                raise FileNotFoundError(f"Template file '{file_path}' not found.")
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            logger.info(f"Successfully read template file: {file_path}")
            return content
            
        except FileNotFoundError:
            logger.error(f"Template file not found: {file_path if 'file_path' in locals() else 'unknown'}")
            raise
        except PermissionError as e:
            logger.error(f"Permission denied reading template file: {e}")
            raise FileNotFoundError(f"Permission denied reading template file: {e}")
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error reading template file: {e}")
            raise ValueError(f"Invalid file encoding. Template file must be UTF-8 encoded: {e}")
        except Exception as e:
            logger.error(f"Unexpected error reading template file: {e}")
            raise RuntimeError(f"Unexpected error reading template file: {e}")