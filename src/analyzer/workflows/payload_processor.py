"""
Payload Processor: Handles payload parsing and content extraction.
Follows Single Responsibility Principle (SRP).
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PayloadProcessor:
    """
    Responsible for parsing payloads and extracting content.
    Supports various payload formats including text, documents, and structured data.
    """
    
    def extract_content(self, payload: Dict[str, Any]) -> str:
        """
        Extract content from various payload formats.
        
        Args:
            payload: The input payload dictionary
            
        Returns:
            Extracted content as string
        """
        # Try direct content field
        if "content" in payload:
            content = payload["content"]
            if isinstance(content, str):
                return content
            elif isinstance(content, dict):
                return self._extract_from_dict(content)
        
        # Try document field
        if "document" in payload:
            return self._extract_from_document(payload["document"])
        
        # Try text field
        if "text" in payload:
            return str(payload["text"])
        
        # Fallback: stringify the entire payload
        logger.warning("No standard content field found, using entire payload")
        return str(payload)
    
    def _extract_from_dict(self, content_dict: Dict[str, Any]) -> str:
        """Extract content from a dictionary structure."""
        if "text" in content_dict:
            return str(content_dict["text"])
        elif "body" in content_dict:
            return str(content_dict["body"])
        elif "content" in content_dict:
            return str(content_dict["content"])
        else:
            return str(content_dict)
    
    def _extract_from_document(self, document: Any) -> str:
        """Extract content from a document structure."""
        if isinstance(document, dict):
            if "content" in document:
                return str(document["content"])
            elif "text" in document:
                return str(document["text"])
            return str(document)
        return str(document)
    
    def validate_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Validate that the payload has extractable content.
        
        Args:
            payload: The payload to validate
            
        Returns:
            True if payload is valid, False otherwise
        """
        if not payload:
            return False
        
        # Check for any standard content fields
        return any(key in payload for key in ["content", "document", "text"]) or bool(payload)
