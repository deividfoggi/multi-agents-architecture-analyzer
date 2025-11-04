"""
Simple test script to read and display the structure of an existing XLSX file.
Shows sheets, columns, and data values.
"""

import os
import sys

from src.analyzer.plugins.xlsx_reader_plugin import XLSXReaderPlugin


def display_xlsx_structure(file_path: str):
    """
    Read an XLSX file and display its complete structure.
    
    Args:
        file_path: Path to the XLSX file to analyze
    """
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return
    
    print("\n" + "=" * 80)
    print(f"XLSX File Structure Analysis: {os.path.basename(file_path)}")
    print("=" * 80 + "\n")
    
    plugin = XLSXReaderPlugin()
    
    # Extract data from the file
    result = plugin.extract_xlsx_from_file(file_path=file_path)
    
    if not result.success:
        print(f"❌ Error reading file: {result.error_message}")
        return
    
    # Display file summary
    print("📊 FILE SUMMARY")
    print("-" * 80)
    print(f"Total Sheets: {result.metadata['total_sheets']}")
    print(f"Sheet Names: {', '.join(result.metadata['sheet_names'])}")
    print("\n")
    
    # Display each sheet's structure and content
    for sheet_name in result.metadata['sheet_names']:
        rows = result.sheets[sheet_name]
        sheet_meta = result.metadata['sheet_metadata'][sheet_name]
        
        print("=" * 80)
        print(f"📄 SHEET: {sheet_name}")
        print("=" * 80)
        print(f"Dimensions: {sheet_meta['row_count']} rows × {sheet_meta['column_count']} columns")
        print(f"Total rows in file: {sheet_meta['total_rows']}")
        
        if sheet_meta['truncated']:
            print(f"⚠️  Note: Data was truncated at {sheet_meta['row_count']} rows")
        
        print("\n")
        
        if len(rows) == 0:
            print("  (Empty sheet)")
            print("\n")
            continue
        
        # Display column headers (first row)
        print("📋 COLUMNS (Row 1 - Header):")
        print("-" * 80)
        headers = rows[0] if len(rows) > 0 else []
        for col_idx, header in enumerate(headers, 1):
            print(f"  Column {col_idx}: {header}")
        print("\n")
        
        # Display data rows
        if len(rows) > 1:
            print(f"📝 DATA ROWS (showing up to 10 rows):")
            print("-" * 80)
            
            # Show up to 10 data rows (excluding header)
            data_rows = rows[1:11]
            
            for row_idx, row in enumerate(data_rows, 2):  # Start from row 2 (after header)
                print(f"\nRow {row_idx}:")
                for col_idx, (header, value) in enumerate(zip(headers, row), 1):
                    # Format value based on type
                    if value == "" or value is None:
                        display_value = "(empty)"
                    elif isinstance(value, float):
                        display_value = f"{value:.2f}"
                    else:
                        display_value = str(value)
                    
                    print(f"  {header}: {display_value}")
            
            # Show row count summary
            total_data_rows = len(rows) - 1
            if total_data_rows > 10:
                print(f"\n... and {total_data_rows - 10} more rows")
        else:
            print("  (No data rows, only header)")
        
        print("\n")
    
    print("=" * 80)
    print("✓ Analysis complete!")
    print("=" * 80 + "\n")


def main():
    """Main function to read and display XLSX file structure."""
    # Check command line arguments
    if len(sys.argv) < 2:
        print("\n" + "=" * 80)
        print("XLSX File Structure Analyzer")
        print("=" * 80)
        print("\nUsage: python test_xlsx_plugin.py <path_to_xlsx_file>")
        print("\nExample:")
        print("  python test_xlsx_plugin.py data.xlsx")
        print("  python test_xlsx_plugin.py /path/to/your/file.xlsx")
        print("\n")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        display_xlsx_structure(file_path)
    except Exception as e:
        print(f"\n❌ Error during analysis: {str(e)}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
