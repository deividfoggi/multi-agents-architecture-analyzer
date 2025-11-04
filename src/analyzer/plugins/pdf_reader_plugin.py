"""
PDF Reader Plugin for Semantic Kernel
Provides PDF text extraction functionality as a native Python function plugin.
"""
import logging
import fitz  # PyMuPDF
import base64
import io
from typing import Optional, Dict, Any
from datetime import datetime
from semantic_kernel.functions import kernel_function
from dataclasses import dataclass


@dataclass
class PDFExtractionResult:
    """Result of PDF text extraction with metadata"""
    text_content: str
    page_count: int
    file_size_bytes: int
    extraction_method: str = "PyMuPDF"
    processed_at: str = None
    
    def __post_init__(self):
        if self.processed_at is None:
            self.processed_at = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text_content": self.text_content,
            "page_count": self.page_count,
            "file_size_bytes": self.file_size_bytes,
            "extraction_method": self.extraction_method,
            "processed_at": self.processed_at
        }


class PDFReaderPlugin:
    """
    Semantic Kernel plugin for reading PDF content from files.
    Supports both file paths and base64-encoded PDF data.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @kernel_function(
        description="Extract text content from a PDF file",
        name="extract_pdf_text"
    )
    def extract_pdf_text(self, pdf_data: str, data_type: str = "base64") -> str:
        """
        Extract text content from PDF data.
        
        Args:
            pdf_data: Either base64-encoded PDF data or file path
            data_type: Type of data - "base64" or "file_path"
        
        Returns:
            JSON string containing extraction result and metadata
        """
        try:
            self.logger.info(f"Starting PDF text extraction with data_type: {data_type}")
            
            if data_type == "base64":
                result = self._extract_from_base64(pdf_data)
            elif data_type == "file_path":
                result = self._extract_from_file_path(pdf_data)
            else:
                raise ValueError(f"Unsupported data_type: {data_type}. Use 'base64' or 'file_path'")
            
            self.logger.info(f"PDF extraction completed successfully. Pages: {result.page_count}, Characters: {len(result.text_content)}")
            
            # Return as JSON string for Semantic Kernel compatibility
            import json
            return json.dumps(result.to_dict())
            
        except Exception as e:
            error_msg = f"PDF extraction failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Return error result as JSON
            import json
            error_result = {
                "text_content": "",
                "page_count": 0,
                "file_size_bytes": 0,
                "extraction_method": "PyMuPDF",
                "processed_at": datetime.utcnow().isoformat() + "Z",
                "error": error_msg
            }
            return json.dumps(error_result)
    
    @kernel_function(
        description="Extract text content from base64-encoded PDF data",
        name="extract_pdf_from_base64"
    )
    def extract_pdf_from_base64(self, base64_data: str) -> str:
        """
        Extract text content from base64-encoded PDF data.
        
        Args:
            base64_data: Base64-encoded PDF file content
        
        Returns:
            JSON string containing extraction result and metadata
        """
        return self.extract_pdf_text(base64_data, "base64")
    
    @kernel_function(
        description="Extract text content from PDF file path",
        name="extract_pdf_from_file"
    )
    def extract_pdf_from_file(self, file_path: str) -> str:
        """
        Extract text content from PDF file path.
        
        Args:
            file_path: Path to the PDF file
        
        Returns:
            JSON string containing extraction result and metadata
        """
        return self.extract_pdf_text(file_path, "file_path")
    
    def _extract_from_base64(self, base64_data: str) -> PDFExtractionResult:
        """Extract text from base64-encoded PDF data"""
        try:
            # Decode base64 data
            pdf_bytes = base64.b64decode(base64_data)
            file_size = len(pdf_bytes)
            
            # Create PDF document from bytes
            pdf_stream = io.BytesIO(pdf_bytes)
            doc = fitz.open(stream=pdf_stream, filetype="pdf")
            
            return self._extract_text_from_document(doc, file_size)
            
        except Exception as e:
            raise Exception(f"Failed to process base64 PDF data: {str(e)}")
    
    def _extract_from_file_path(self, file_path: str) -> PDFExtractionResult:
        """Extract text from PDF file path"""
        try:
            import os
            
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Open PDF document
            doc = fitz.open(file_path)
            
            return self._extract_text_from_document(doc, file_size)
            
        except Exception as e:
            raise Exception(f"Failed to process PDF file '{file_path}': {str(e)}")
    
    def _extract_text_from_document(self, doc: fitz.Document, file_size: int) -> PDFExtractionResult:
        """Extract text from PyMuPDF document"""
        try:
            text_content = ""
            page_count = len(doc)
            
            # Extract text from each page
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                if text.strip():  # Only add non-empty pages
                    text_content += f"\n--- Page {page_num + 1} ---\n"
                    text_content += text
                    text_content += "\n"
            
            # Close the document
            doc.close()
            
            # Clean up the extracted text
            text_content = text_content.strip()
            
            if not text_content:
                self.logger.warning("No text content extracted from PDF")
            
            return PDFExtractionResult(
                text_content=text_content,
                page_count=page_count,
                file_size_bytes=file_size
            )
            
        except Exception as e:
            doc.close()  # Ensure document is closed
            raise Exception(f"Text extraction failed: {str(e)}")
    
    @kernel_function(
        description="Get PDF metadata without extracting full text",
        name="get_pdf_metadata"
    )
    def get_pdf_metadata(self, pdf_data: str, data_type: str = "base64") -> str:
        """
        Get PDF metadata (page count, file size) without extracting full text.
        
        Args:
            pdf_data: Either base64-encoded PDF data or file path
            data_type: Type of data - "base64" or "file_path"
        
        Returns:
            JSON string containing PDF metadata
        """
        try:
            if data_type == "base64":
                pdf_bytes = base64.b64decode(pdf_data)
                file_size = len(pdf_bytes)
                pdf_stream = io.BytesIO(pdf_bytes)
                doc = fitz.open(stream=pdf_stream, filetype="pdf")
            elif data_type == "file_path":
                import os
                if not os.path.exists(pdf_data):
                    raise FileNotFoundError(f"PDF file not found: {pdf_data}")
                file_size = os.path.getsize(pdf_data)
                doc = fitz.open(pdf_data)
            else:
                raise ValueError(f"Unsupported data_type: {data_type}")
            
            metadata = {
                "page_count": len(doc),
                "file_size_bytes": file_size,
                "extraction_method": "PyMuPDF",
                "processed_at": datetime.utcnow().isoformat() + "Z"
            }
            
            doc.close()
            
            import json
            return json.dumps(metadata)
            
        except Exception as e:
            error_result = {
                "page_count": 0,
                "file_size_bytes": 0,
                "extraction_method": "PyMuPDF",
                "processed_at": datetime.utcnow().isoformat() + "Z",
                "error": f"Metadata extraction failed: {str(e)}"
            }
            
            import json
            return json.dumps(error_result)


# For backward compatibility and easy import
PDFReader = PDFReaderPlugin