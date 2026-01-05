#!/usr/bin/env python3
"""
PDF Parsing Comparison Test
============================

Compares different PDF parsing libraries (pypdf, pdfplumber, camelot)
to evaluate text and table extraction quality.

Usage:
    python test_pdf_parsing_comparison.py [path/to/test.pdf]
    
    If no path provided, uses default test PDF:
    Research/Researching Gain Therapeutics Drug Testing.pdf
"""

import sys
import time
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Default test PDF path
DEFAULT_PDF_PATH = Path(__file__).parent.parent.parent / "Research" / "Researching Gain Therapeutics Drug Testing.pdf"

# Output directory
OUTPUT_DIR = Path(__file__).parent


class PDFParserComparison:
    """Compare different PDF parsing libraries."""
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.results: Dict[str, Dict] = {}
        
    def run_comparison(self) -> None:
        """Run all parsing methods and generate comparison."""
        print(f"\n{'='*70}")
        print(f"PDF Parsing Comparison Test")
        print(f"{'='*70}")
        print(f"PDF File: {self.pdf_path}")
        print(f"File exists: {self.pdf_path.exists()}")
        print(f"{'='*70}\n")
        
        if not self.pdf_path.exists():
            print(f"ERROR: PDF file not found: {self.pdf_path}")
            sys.exit(1)
        
        # Test each library
        self._test_pypdf()
        self._test_pdfplumber()
        self._test_camelot()
        
        # Generate outputs
        self._save_outputs()
        self._generate_report()
        
    def _test_pypdf(self) -> None:
        """Test pypdf library."""
        print("Testing pypdf...")
        start_time = time.time()
        
        try:
            import pypdf
            
            text = ""
            with open(self.pdf_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                num_pages = len(reader.pages)
                
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            elapsed = time.time() - start_time
            
            # Calculate useful metrics
            words = len(text.split())
            # Count non-whitespace characters for better comparison
            non_whitespace_chars = len(''.join(text.split()))
            newline_count = text.count('\n')
            
            self.results['pypdf'] = {
                'success': True,
                'text': text,
                'char_count': len(text),
                'non_whitespace_chars': non_whitespace_chars,
                'word_count': words,
                'newline_count': newline_count,
                'num_pages': num_pages,
                'extraction_time': elapsed,
                'tables': [],  # pypdf doesn't extract tables
                'error': None
            }
            
            print(f"  [OK] Success: {num_pages} pages, {len(text):,} chars ({non_whitespace_chars:,} non-whitespace), {words:,} words, {elapsed:.2f}s")
            
        except ImportError:
            self.results['pypdf'] = {
                'success': False,
                'error': 'pypdf not installed',
                'text': '',
                'char_count': 0,
                'extraction_time': 0
            }
            print(f"  [X] pypdf not installed")
        except Exception as e:
            self.results['pypdf'] = {
                'success': False,
                'error': str(e),
                'text': '',
                'char_count': 0,
                'extraction_time': time.time() - start_time
            }
            print(f"  [X] Error: {e}")
    
    def _test_pdfplumber(self) -> None:
        """Test pdfplumber library."""
        print("Testing pdfplumber...")
        start_time = time.time()
        
        try:
            import pdfplumber
            
            text = ""
            tables = []
            
            with pdfplumber.open(self.pdf_path) as pdf:
                num_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table_num, table in enumerate(page_tables, 1):
                            tables.append({
                                'page': page_num,
                                'table_num': table_num,
                                'rows': len(table),
                                'data': table
                            })
            
            elapsed = time.time() - start_time
            
            # Calculate useful metrics
            words = len(text.split())
            non_whitespace_chars = len(''.join(text.split()))
            newline_count = text.count('\n')
            
            self.results['pdfplumber'] = {
                'success': True,
                'text': text,
                'char_count': len(text),
                'non_whitespace_chars': non_whitespace_chars,
                'word_count': words,
                'newline_count': newline_count,
                'num_pages': num_pages,
                'extraction_time': elapsed,
                'tables': tables,
                'num_tables': len(tables),
                'error': None
            }
            
            print(f"  [OK] Success: {num_pages} pages, {len(text):,} chars ({non_whitespace_chars:,} non-whitespace), {words:,} words, {len(tables)} tables, {elapsed:.2f}s")
            
        except ImportError:
            self.results['pdfplumber'] = {
                'success': False,
                'error': 'pdfplumber not installed',
                'text': '',
                'char_count': 0,
                'extraction_time': 0,
                'tables': [],
                'num_tables': 0
            }
            print(f"  [X] pdfplumber not installed")
        except Exception as e:
            self.results['pdfplumber'] = {
                'success': False,
                'error': str(e),
                'text': '',
                'char_count': 0,
                'extraction_time': time.time() - start_time,
                'tables': [],
                'num_tables': 0
            }
            print(f"  [X] Error: {e}")
    
    def _test_camelot(self) -> None:
        """Test camelot-py library (table extraction only)."""
        print("Testing camelot-py...")
        start_time = time.time()
        
        try:
            import camelot
            
            tables = []
            text = ""  # camelot doesn't extract text, only tables
            
            # Try to extract tables
            try:
                camelot_tables = camelot.read_pdf(str(self.pdf_path), pages='all', flavor='lattice')
                
                for table_num, table in enumerate(camelot_tables, 1):
                    # Convert to list of lists
                    table_data = table.df.values.tolist()
                    tables.append({
                        'page': table.page,
                        'table_num': table_num,
                        'rows': len(table_data),
                        'data': table_data,
                        'accuracy': table.accuracy if hasattr(table, 'accuracy') else None
                    })
                
                # Get text from first table's page context if available
                if camelot_tables:
                    # camelot doesn't provide full text, so we'll note this
                    text = "[Note: camelot-py extracts tables only, not full text]"
                
            except Exception as e:
                # camelot might fail on some PDFs, try alternative method
                try:
                    camelot_tables = camelot.read_pdf(str(self.pdf_path), pages='all', flavor='stream')
                    for table_num, table in enumerate(camelot_tables, 1):
                        table_data = table.df.values.tolist()
                        tables.append({
                            'page': table.page,
                            'table_num': table_num,
                            'rows': len(table_data),
                            'data': table_data,
                            'accuracy': table.accuracy if hasattr(table, 'accuracy') else None
                        })
                except Exception as e2:
                    raise e  # Raise original error
            
            elapsed = time.time() - start_time
            
            self.results['camelot'] = {
                'success': True,
                'text': text,
                'char_count': len(text) if text else 0,
                'num_pages': len(set(t['page'] for t in tables)) if tables else 0,
                'extraction_time': elapsed,
                'tables': tables,
                'num_tables': len(tables),
                'error': None
            }
            
            print(f"  [OK] Success: {len(tables)} tables extracted, {elapsed:.2f}s")
            
        except ImportError:
            self.results['camelot'] = {
                'success': False,
                'error': 'camelot-py not installed',
                'text': '',
                'char_count': 0,
                'extraction_time': 0,
                'tables': [],
                'num_tables': 0
            }
            print(f"  [X] camelot-py not installed")
        except Exception as e:
            self.results['camelot'] = {
                'success': False,
                'error': str(e),
                'text': '',
                'char_count': 0,
                'extraction_time': time.time() - start_time,
                'tables': [],
                'num_tables': 0
            }
            print(f"  [X] Error: {e}")
    
    def _save_outputs(self) -> None:
        """Save extracted text to output files."""
        print(f"\n{'='*70}")
        print("Saving output files...")
        print(f"{'='*70}\n")
        
        for lib_name, result in self.results.items():
            if not result.get('success'):
                continue
            
            output_file = OUTPUT_DIR / f"test_pdf_output_{lib_name}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"PDF Parsing Output: {lib_name}\n")
                f.write(f"{'='*70}\n")
                f.write(f"Source PDF: {self.pdf_path}\n")
                f.write(f"Extraction Time: {result.get('extraction_time', 0):.2f}s\n")
                f.write(f"Character Count: {result.get('char_count', 0):,}\n")
                f.write(f"Number of Pages: {result.get('num_pages', 0)}\n")
                
                if lib_name == 'pdfplumber' or lib_name == 'camelot':
                    f.write(f"Number of Tables: {result.get('num_tables', 0)}\n")
                
                f.write(f"{'='*70}\n\n")
                f.write(result.get('text', ''))
            
            print(f"  [OK] Saved: {output_file}")
            
            # Save tables to CSV if any found
            if lib_name in ['pdfplumber', 'camelot']:
                tables = result.get('tables', [])
                if tables:
                    for table_info in tables:
                        table_file = OUTPUT_DIR / f"test_pdf_table_{lib_name}_p{table_info['page']}_t{table_info['table_num']}.csv"
                        with open(table_file, 'w', encoding='utf-8', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerows(table_info['data'])
                        print(f"  [OK] Saved table: {table_file}")
    
    def _generate_report(self) -> None:
        """Generate comparison report."""
        report_file = OUTPUT_DIR / "test_pdf_comparison_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("PDF Parsing Comparison Report\n")
            f.write("=" * 70 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source PDF: {self.pdf_path}\n")
            f.write("=" * 70 + "\n\n")
            
            # Summary statistics
            f.write("SUMMARY STATISTICS\n")
            f.write("-" * 70 + "\n\n")
            
            for lib_name, result in self.results.items():
                f.write(f"{lib_name.upper()}:\n")
                if result.get('success'):
                    f.write(f"  Status: SUCCESS\n")
                    f.write(f"  Character Count: {result.get('char_count', 0):,}\n")
                    f.write(f"  Number of Pages: {result.get('num_pages', 0)}\n")
                    f.write(f"  Extraction Time: {result.get('extraction_time', 0):.2f}s\n")
                    
                    if lib_name in ['pdfplumber', 'camelot']:
                        f.write(f"  Number of Tables: {result.get('num_tables', 0)}\n")
                else:
                    f.write(f"  Status: FAILED\n")
                    f.write(f"  Error: {result.get('error', 'Unknown error')}\n")
                f.write("\n")
            
            # Comparison
            f.write("\n" + "=" * 70 + "\n")
            f.write("COMPARISON\n")
            f.write("=" * 70 + "\n\n")
            
            # Text extraction comparison
            successful_libs = [lib for lib, res in self.results.items() if res.get('success')]
            
            if len(successful_libs) > 1:
                f.write("Text Extraction Comparison:\n")
                f.write("-" * 70 + "\n")
                
                # Compare total characters
                f.write("Total Characters (including whitespace):\n")
                char_counts = {}
                for lib_name in successful_libs:
                    if lib_name != 'camelot':  # camelot doesn't extract text
                        char_counts[lib_name] = self.results[lib_name].get('char_count', 0)
                
                if char_counts:
                    max_chars = max(char_counts.values())
                    for lib_name, count in sorted(char_counts.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / max_chars * 100) if max_chars > 0 else 0
                        f.write(f"  {lib_name:15s}: {count:>10,} chars ({percentage:5.1f}%)\n")
                
                f.write("\n")
                
                # Compare non-whitespace characters (more meaningful)
                f.write("Non-Whitespace Characters (actual content):\n")
                nw_char_counts = {}
                for lib_name in successful_libs:
                    if lib_name != 'camelot':
                        nw_count = self.results[lib_name].get('non_whitespace_chars', 0)
                        if nw_count > 0:
                            nw_char_counts[lib_name] = nw_count
                
                if nw_char_counts:
                    max_nw_chars = max(nw_char_counts.values())
                    for lib_name, count in sorted(nw_char_counts.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / max_nw_chars * 100) if max_nw_chars > 0 else 0
                        newlines = self.results[lib_name].get('newline_count', 0)
                        f.write(f"  {lib_name:15s}: {count:>10,} chars ({percentage:5.1f}%), {newlines:,} newlines\n")
                
                f.write("\n")
                
                # Compare word counts
                f.write("Word Count:\n")
                word_counts = {}
                for lib_name in successful_libs:
                    if lib_name != 'camelot':
                        word_count = self.results[lib_name].get('word_count', 0)
                        if word_count > 0:
                            word_counts[lib_name] = word_count
                
                if word_counts:
                    max_words = max(word_counts.values())
                    for lib_name, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / max_words * 100) if max_words > 0 else 0
                        f.write(f"  {lib_name:15s}: {count:>10,} words ({percentage:5.1f}%)\n")
                
                f.write("\n")
            
            # Table extraction comparison
            table_libs = [lib for lib in ['pdfplumber', 'camelot'] if lib in successful_libs]
            if table_libs:
                f.write("Table Extraction Comparison:\n")
                f.write("-" * 70 + "\n")
                for lib_name in table_libs:
                    num_tables = self.results[lib_name].get('num_tables', 0)
                    f.write(f"  {lib_name:15s}: {num_tables} tables\n")
                f.write("\n")
            
            # Performance comparison
            f.write("Performance Comparison:\n")
            f.write("-" * 70 + "\n")
            for lib_name in successful_libs:
                time_taken = self.results[lib_name].get('extraction_time', 0)
                f.write(f"  {lib_name:15s}: {time_taken:>6.2f}s\n")
            f.write("\n")
            
            # Recommendations
            f.write("\n" + "=" * 70 + "\n")
            f.write("RECOMMENDATIONS\n")
            f.write("=" * 70 + "\n\n")
            
            if 'pdfplumber' in successful_libs:
                pdfplumber_result = self.results['pdfplumber']
                if pdfplumber_result.get('num_tables', 0) > 0:
                    f.write("[OK] pdfplumber extracted tables - good for documents with tables\n")
                if pdfplumber_result.get('char_count', 0) > 0:
                    f.write("[OK] pdfplumber extracted text - good text extraction quality\n")
            
            if 'pypdf' in successful_libs:
                pypdf_result = self.results['pypdf']
                if pypdf_result.get('char_count', 0) > 0:
                    f.write("[OK] pypdf extracted text - basic but reliable\n")
            
            if 'camelot' in successful_libs:
                camelot_result = self.results['camelot']
                if camelot_result.get('num_tables', 0) > 0:
                    f.write("[OK] camelot extracted tables - specialized for table extraction\n")
        
        print(f"  [OK] Saved report: {report_file}")
        
        # Print summary to console
        print(f"\n{'='*70}")
        print("COMPARISON SUMMARY")
        print(f"{'='*70}\n")
        
        for lib_name, result in self.results.items():
            if result.get('success'):
                print(f"{lib_name.upper():15s}: ", end="")
                nw_chars = result.get('non_whitespace_chars', result.get('char_count', 0))
                words = result.get('word_count', 0)
                tables = result.get('num_tables', 0)
                time_taken = result.get('extraction_time', 0)
                print(f"{nw_chars:>10,} non-whitespace chars, {words:>6,} words, {tables} tables, {time_taken:.2f}s")
            else:
                print(f"{lib_name.upper():15s}: FAILED - {result.get('error', 'Unknown')}")


def main():
    """Main entry point."""
    # Get PDF path from command line or use default
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        pdf_path = DEFAULT_PDF_PATH
    
    # Check if file exists
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        print(f"\nUsage: python {sys.argv[0]} [path/to/test.pdf]")
        print(f"Default path: {DEFAULT_PDF_PATH}")
        sys.exit(1)
    
    # Run comparison
    comparison = PDFParserComparison(pdf_path)
    comparison.run_comparison()
    
    print(f"\n{'='*70}")
    print("Test completed! Check output files in:")
    print(f"  {OUTPUT_DIR}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

