"""
Excel Text Extraction Service using openpyxl and pandas
"""
import logging
import openpyxl
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime
import io

class ExcelExtractionMetadata:
    """Metadata about the Excel extraction process"""
    def __init__(self):
        self.sheet_count: int = 0
        self.file_size_bytes: int = 0
        self.file_name: str = ""
        self.processed_at: datetime = datetime.utcnow()
        self.extraction_method: str = "openpyxl/pandas"
        self.sheet_names: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheetCount": self.sheet_count,
            "fileSizeBytes": self.file_size_bytes,
            "fileName": self.file_name,
            "processedAt": self.processed_at.isoformat() + "Z",
            "extractionMethod": self.extraction_method,
            "sheetNames": self.sheet_names
        }

class ExcelExtractionResponse:
    """Response object for Excel extraction"""
    def __init__(self):
        self.success: bool = False
        self.extracted_text: str = ""
        self.metadata: Optional[ExcelExtractionMetadata] = None
        self.error_message: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "extractedText": self.extracted_text,
            "errorMessage": self.error_message
        }
        
        if self.metadata:
            result["extractionMetadata"] = self.metadata.to_dict()
            
        return result

class ExcelExtractionService:
    """Service for extracting text from Excel documents using openpyxl and pandas"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_text_from_excel(self, file_content: bytes, file_name: str = "document.xlsx") -> ExcelExtractionResponse:
        """
        Extract text from Excel content using openpyxl and pandas
        
        Args:
            file_content: The Excel file content as bytes
            file_name: Optional file name for metadata
            
        Returns:
            ExcelExtractionResponse with extracted text and metadata
        """
        response = ExcelExtractionResponse()
        response.metadata = ExcelExtractionMetadata()
        response.metadata.file_name = file_name
        response.metadata.file_size_bytes = len(file_content)
        
        try:
            self.logger.info(f"Starting Excel text extraction for file: {file_name} ({len(file_content)} bytes)")
            
            # Validate file content
            if not file_content or len(file_content) == 0:
                response.error_message = "File content is empty or invalid"
                return response
            
            # Read Excel file from memory using pandas
            file_stream = io.BytesIO(file_content)
            
            # Read all sheets
            excel_file = pd.ExcelFile(file_stream, engine='openpyxl')
            response.metadata.sheet_names = excel_file.sheet_names
            response.metadata.sheet_count = len(excel_file.sheet_names)
            
            self.logger.info(f"Excel file opened successfully. Sheet count: {response.metadata.sheet_count}")
            self.logger.info(f"Sheet names: {response.metadata.sheet_names}")
            
            # Extract text from all sheets
            extracted_text_parts: List[str] = []
            
            for sheet_name in excel_file.sheet_names:
                self.logger.info(f"Processing sheet: {sheet_name}")
                
                # Read the sheet into a DataFrame
                df = pd.read_excel(file_stream, sheet_name=sheet_name, engine='openpyxl')
                
                # Skip empty sheets
                if df.empty:
                    self.logger.info(f"Sheet '{sheet_name}' is empty, skipping")
                    continue
                
                # Convert DataFrame to text format
                sheet_text = self._dataframe_to_text(df, sheet_name)
                
                if sheet_text.strip():
                    extracted_text_parts.append(sheet_text)
                    self.logger.debug(f"Extracted text from sheet '{sheet_name}': {len(sheet_text)} characters")
            
            # Combine all extracted text
            response.extracted_text = "\n\n".join(extracted_text_parts)
            response.success = True
            
            self.logger.info(f"Text extraction completed successfully. Total characters: {len(response.extracted_text)}")
            
        except Exception as ex:
            self.logger.error(f"Error during Excel text extraction: {str(ex)}")
            response.success = False
            response.error_message = f"Excel text extraction failed: {str(ex)}"
            
        return response
    
    def _dataframe_to_text(self, df: pd.DataFrame, sheet_name: str) -> str:
        """
        Convert a pandas DataFrame to a readable text format
        
        Args:
            df: The pandas DataFrame
            sheet_name: Name of the sheet
            
        Returns:
            Formatted text representation of the DataFrame
        """
        text_parts = [f"=== SHEET: {sheet_name} ==="]
        
        # Add column headers
        headers = " | ".join([str(col) for col in df.columns])
        text_parts.append(f"\nColumns: {headers}\n")
        
        # Add separator
        text_parts.append("-" * min(len(headers), 100))
        
        # Add rows
        for idx, row in df.iterrows():
            row_values = []
            for col in df.columns:
                value = row[col]
                # Handle different types of values
                if pd.isna(value):
                    row_values.append("")
                else:
                    row_values.append(str(value))
            
            row_text = " | ".join(row_values)
            text_parts.append(row_text)
        
        # Add summary
        text_parts.append(f"\n[Sheet '{sheet_name}': {len(df)} rows x {len(df.columns)} columns]")
        
        return "\n".join(text_parts)
    
    def validate_excel_file(self, file_content: bytes) -> bool:
        """
        Validate if the file content is a valid Excel file
        
        Args:
            file_content: The file content as bytes
            
        Returns:
            True if valid Excel file, False otherwise
        """
        try:
            if not file_content or len(file_content) < 4:
                return False
            
            # Check for Excel file signatures
            # XLSX files start with PK (ZIP format)
            if file_content.startswith(b'PK'):
                # Try to open with openpyxl
                file_stream = io.BytesIO(file_content)
                excel_file = pd.ExcelFile(file_stream, engine='openpyxl')
                sheet_count = len(excel_file.sheet_names)
                return sheet_count > 0
            
            # XLS files start with specific header
            if file_content.startswith(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'):
                # Old Excel format - try to read with xlrd if needed
                file_stream = io.BytesIO(file_content)
                try:
                    excel_file = pd.ExcelFile(file_stream, engine='xlrd')
                    sheet_count = len(excel_file.sheet_names)
                    return sheet_count > 0
                except:
                    return False
            
            return False
            
        except Exception:
            return False
