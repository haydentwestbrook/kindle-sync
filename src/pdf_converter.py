"""PDF conversion utilities for Kindle Scribe optimization."""

import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from io import BytesIO
import markdown
import weasyprint
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from loguru import logger

from .config import Config


class MarkdownToPDFConverter:
    """Convert Markdown files to Kindle-optimized PDFs."""
    
    def __init__(self, config: Config):
        """Initialize the PDF converter."""
        self.config = config
        self.pdf_config = config.get_pdf_config()
        self.markdown_config = config.get_markdown_config()
        
        # Set up page size
        page_size_name = self.pdf_config.get('page_size', 'A4').upper()
        self.page_size = A4 if page_size_name == 'A4' else letter
        
        # Set up margins
        margins = self.pdf_config.get('margins', [72, 72, 72, 72])  # Default 1 inch margins
        self.margins = [margin / 72 for margin in margins]  # Convert points to inches
        
        # Set up styles
        self.styles = self._setup_styles()
        
        logger.info("PDF converter initialized")
    
    def _setup_styles(self) -> Dict[str, ParagraphStyle]:
        """Set up paragraph styles for PDF generation."""
        styles = getSampleStyleSheet()
        
        # Custom styles for Kindle optimization
        custom_styles = {
            'Title': ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ),
            'Heading1': ParagraphStyle(
                'CustomHeading1',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=12,
                spaceBefore=20,
                fontName='Helvetica-Bold'
            ),
            'Heading2': ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=10,
                spaceBefore=16,
                fontName='Helvetica-Bold'
            ),
            'Heading3': ParagraphStyle(
                'CustomHeading3',
                parent=styles['Heading3'],
                fontSize=12,
                spaceAfter=8,
                spaceBefore=12,
                fontName='Helvetica-Bold'
            ),
            'BodyText': ParagraphStyle(
                'CustomBodyText',
                parent=styles['Normal'],
                fontSize=self.pdf_config.get('font_size', 12),
                spaceAfter=6,
                alignment=TA_JUSTIFY,
                fontName='Times-Roman',
                leading=self.pdf_config.get('font_size', 12) * self.pdf_config.get('line_spacing', 1.2)
            ),
            'Code': ParagraphStyle(
                'CustomCode',
                parent=styles['Code'],
                fontSize=10,
                fontName='Courier',
                backColor='#f0f0f0',
                borderColor='#cccccc',
                borderWidth=1,
                leftIndent=20,
                rightIndent=20,
                spaceAfter=10,
                spaceBefore=10
            )
        }
        
        return custom_styles
    
    def convert_markdown_to_pdf(self, markdown_path: Path, output_path: Optional[Path] = None) -> Path:
        """Convert a Markdown file to PDF."""
        try:
            # Read markdown content
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Process markdown
            processed_content = self._process_markdown(markdown_content)
            
            # Generate PDF
            if output_path is None:
                output_path = markdown_path.with_suffix('.pdf')
            
            self._generate_pdf(processed_content, output_path)
            
            logger.info(f"Converted {markdown_path} to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error converting {markdown_path} to PDF: {e}")
            raise
    
    def _process_markdown(self, content: str) -> str:
        """Process markdown content for PDF generation."""
        # Configure markdown extensions
        extensions = self.markdown_config.get('extensions', ['tables', 'fenced_code', 'toc'])
        
        # Process with markdown
        md = markdown.Markdown(extensions=extensions)
        html_content = md.convert(content)
        
        # Add CSS for better PDF rendering
        css_styles = """
        <style>
        body {
            font-family: 'Times New Roman', serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #333;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        h1 { font-size: 1.8em; }
        h2 { font-size: 1.5em; }
        h3 { font-size: 1.3em; }
        p {
            margin-bottom: 1em;
            text-align: justify;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        pre {
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        blockquote {
            border-left: 4px solid #ddd;
            margin: 0;
            padding-left: 20px;
            color: #666;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        </style>
        """
        
        return f"<html><head>{css_styles}</head><body>{html_content}</body></html>"
    
    def _generate_pdf(self, html_content: str, output_path: Path):
        """Generate PDF from HTML content using WeasyPrint."""
        try:
            # Use WeasyPrint for better HTML to PDF conversion
            pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
            
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
                
        except Exception as e:
            logger.warning(f"WeasyPrint failed, falling back to ReportLab: {e}")
            self._generate_pdf_reportlab(html_content, output_path)
    
    def _generate_pdf_reportlab(self, html_content: str, output_path: Path):
        """Fallback PDF generation using ReportLab."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            rightMargin=self.margins[1],
            leftMargin=self.margins[3],
            topMargin=self.margins[0],
            bottomMargin=self.margins[2]
        )
        
        # Parse HTML and convert to ReportLab elements
        elements = self._parse_html_to_reportlab(html_content)
        
        # Build PDF
        doc.build(elements)
    
    def _parse_html_to_reportlab(self, html_content: str) -> List:
        """Parse HTML content and convert to ReportLab elements."""
        # This is a simplified parser - in production, you might want to use BeautifulSoup
        elements = []
        
        # Split content by HTML tags and process
        lines = html_content.split('\n')
        current_paragraph = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('<h1>'):
                if current_paragraph:
                    elements.append(Paragraph(current_paragraph, self.styles['BodyText']))
                    current_paragraph = ""
                title = line.replace('<h1>', '').replace('</h1>', '')
                elements.append(Paragraph(title, self.styles['Title']))
                elements.append(Spacer(1, 12))
                
            elif line.startswith('<h2>'):
                if current_paragraph:
                    elements.append(Paragraph(current_paragraph, self.styles['BodyText']))
                    current_paragraph = ""
                heading = line.replace('<h2>', '').replace('</h2>', '')
                elements.append(Paragraph(heading, self.styles['Heading1']))
                elements.append(Spacer(1, 10))
                
            elif line.startswith('<h3>'):
                if current_paragraph:
                    elements.append(Paragraph(current_paragraph, self.styles['BodyText']))
                    current_paragraph = ""
                heading = line.replace('<h3>', '').replace('</h3>', '')
                elements.append(Paragraph(heading, self.styles['Heading2']))
                elements.append(Spacer(1, 8))
                
            elif line.startswith('<p>'):
                paragraph = line.replace('<p>', '').replace('</p>', '')
                current_paragraph += paragraph + " "
                
            elif line.startswith('<br>') or line.startswith('<br/>'):
                if current_paragraph:
                    elements.append(Paragraph(current_paragraph, self.styles['BodyText']))
                    current_paragraph = ""
                elements.append(Spacer(1, 6))
                
            else:
                # Regular text line
                current_paragraph += line + " "
        
        # Add any remaining paragraph
        if current_paragraph:
            elements.append(Paragraph(current_paragraph, self.styles['BodyText']))
        
        return elements


class PDFToMarkdownConverter:
    """Convert PDF files to Markdown using OCR."""
    
    def __init__(self, config: Config):
        """Initialize the PDF to Markdown converter."""
        self.config = config
        self.ocr_config = config.get_ocr_config()
        
        logger.info("PDF to Markdown converter initialized")
    
    def convert_pdf_to_markdown(self, pdf_path: Path, output_path: Optional[Path] = None) -> Path:
        """Convert a PDF file to Markdown using OCR."""
        try:
            import pytesseract
            from PIL import Image
            import pdf2image
            
            # Convert PDF to images
            images = pdf2image.convert_from_path(pdf_path)
            
            # Extract text from images using OCR
            extracted_text = ""
            for i, image in enumerate(images):
                logger.info(f"Processing page {i + 1} of {len(images)}")
                
                # Perform OCR
                page_text = pytesseract.image_to_string(
                    image,
                    lang=self.ocr_config.get('language', 'eng'),
                    config='--psm 6'  # Assume uniform block of text
                )
                
                extracted_text += page_text + "\n\n"
            
            # Process extracted text
            markdown_content = self._process_extracted_text(extracted_text)
            
            # Save to file
            if output_path is None:
                output_path = pdf_path.with_suffix('.md')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Converted {pdf_path} to {output_path}")
            return output_path
            
        except ImportError:
            logger.error("Required OCR dependencies not installed. Install with: pip install pytesseract pdf2image")
            raise
        except Exception as e:
            logger.error(f"Error converting {pdf_path} to Markdown: {e}")
            raise
    
    def _process_extracted_text(self, text: str) -> str:
        """Process extracted text to improve Markdown formatting."""
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            if not line:
                processed_lines.append('')
                continue
            
            # Detect headings (simple heuristic)
            if len(line) < 50 and line.isupper() and not line.endswith('.'):
                processed_lines.append(f"# {line}")
            elif len(line) < 50 and not line.endswith('.'):
                processed_lines.append(f"## {line}")
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
