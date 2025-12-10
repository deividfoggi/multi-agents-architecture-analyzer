"""Plugin system for extensibility"""
from .pdf_reader_plugin import PDFReaderPlugin
from .xlsx_reader_plugin import XLSXReaderPlugin
from .azure_pricing_plugin import AzurePricingPlugin

__all__ = [
    'PDFReaderPlugin',
    'XLSXReaderPlugin',
    'AzurePricingPlugin'
]
