import aiohttp
import asyncio
import pandas as pd
import pdfplumber
import base64
import io
from typing import Dict, Any, Optional
from PIL import Image
import pytesseract
import json
import re
import matplotlib

from app.types import ProcessingResult
from app.utils import logger, async_retry

class ResourceFetcher:
    def __init__(self):
        self.session = None

    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_resource(self, url: str, headers: Optional[Dict] = None) -> ProcessingResult:
        """Fetch and process a resource based on its type"""
        session = await self.get_session()
        
        try:
            request_headers = headers or {}
            async with session.get(url, headers=request_headers) as response:
                response.raise_for_status()
                content_type = response.headers.get('content-type', '').lower()
                content = await response.read()
                
                # Process based on content type and file extension
                if 'csv' in content_type or url.endswith('.csv'):
                    return await self._process_csv(content)
                elif 'pdf' in content_type or url.endswith('.pdf'):
                    return await self._process_pdf(content)
                elif 'json' in content_type or url.endswith('.json'):
                    return await self._process_json(content)
                elif 'spreadsheet' in content_type or 'excel' in content_type or any(url.endswith(ext) for ext in ['.xlsx', '.xls']):
                    return await self._process_excel(content)  # Add this line
                elif 'image' in content_type or any(url.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                    return await self._process_image(content)
                elif 'html' in content_type or url.endswith('.html') or '/table-page' in url or '/secret-page' in url:
                    return await self._process_html(content, url)
                elif 'xml' in content_type or url.endswith('.xml'):
                    return await self._process_xml(content)
                elif 'text' in content_type or url.endswith('.txt'):
                    return await self._process_text(content)
                else:
                    # Try to auto-detect type
                    return await self._auto_detect_process(content, url)
                    
        except Exception as e:
            logger.error(f"Error fetching resource {url}: {str(e)}")
            raise

    async def _auto_detect_process(self, content: bytes, url: str) -> ProcessingResult:
        """Auto-detect content type and process"""
        # Try common file extensions
        if url.endswith('.xlsx') or url.endswith('.xls'):
            return await self._process_excel(content)  # Add this line
        elif url.endswith('.csv'):
            return await self._process_csv(content)
        elif url.endswith('.pdf'):
            return await self._process_pdf(content)
        elif url.endswith('.json'):
            return await self._process_json(content)
        elif any(url.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']):
            return await self._process_image(content)
        elif url.endswith('.txt'):
            return await self._process_text(content)
        else:
            # Default to text processing
            return await self._process_text(content)

    async def _process_html(self, content: bytes, url: str) -> ProcessingResult:
        """Process HTML page and extract structured data"""
        logger.info(f"🔄 Processing HTML page: {url}")
        try:
            from bs4 import BeautifulSoup
            
            html_text = content.decode('utf-8')
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Extract tables
            tables = soup.find_all('table')
            table_data = []
            
            for i, table in enumerate(tables):
                table_info = f"Table {i+1}:"
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    table_info += f"\n{row_data}"
                table_data.append(table_info)
            
            # Extract all text
            text_content = soup.get_text(separator='\n', strip=True)
            
            # Combine table data with text
            full_content = f"Page URL: {url}\n\nExtracted Tables:\n" + "\n\n".join(table_data) + f"\n\nFull Text:\n{text_content}"
            
            logger.info(f"✅ HTML processing complete. Found {len(tables)} tables.")
            
            return ProcessingResult(
                content=full_content,
                metadata={'type': 'html', 'tables': len(tables)}
            )
            
        except Exception as e:
            logger.error(f"Error processing HTML: {str(e)}")
            return ProcessingResult(
                content=content.decode('utf-8', errors='ignore'),
                metadata={'type': 'text', 'error': str(e)}
            )

    async def _process_csv(self, content: bytes) -> ProcessingResult:
        """Process CSV file and return analysis"""
        try:
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'windows-1252']:
                try:
                    csv_text = content.decode(encoding)
                    df = pd.read_csv(io.StringIO(csv_text))
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # If all encodings fail, use bytes
                df = pd.read_csv(io.BytesIO(content))
            
            # Generate summary
            summary = {
                'shape': df.shape,
                'columns': df.columns.tolist(),
                'dtypes': df.dtypes.astype(str).to_dict(),
                'head': df.head().to_dict('records'),
                'description': df.describe().to_dict() if df.select_dtypes(include=['number']).shape[1] > 0 else {}
            }
            
            return ProcessingResult(
                content=json.dumps(summary, default=str),
                metadata={'type': 'csv', 'rows': len(df), 'columns': len(df.columns)}
            )
            
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            # Fallback: return as text
            return ProcessingResult(
                content=content.decode('utf-8', errors='ignore'),
                metadata={'type': 'text', 'error': str(e)}
            )
        
    async def _process_excel(self, content: bytes) -> ProcessingResult:
        """Process Excel file and extract data"""
        try:
            import pandas as pd
            from io import BytesIO
            
            # Read Excel file
            excel_file = BytesIO(content)
            xl = pd.ExcelFile(excel_file)
            
            sheet_data = []
            for sheet_name in xl.sheet_names:
                df = xl.parse(sheet_name)
                sheet_info = {
                    'sheet_name': sheet_name,
                    'shape': df.shape,
                    'columns': df.columns.tolist(),
                    'head': df.head().to_dict('records')
                }
                sheet_data.append(sheet_info)
            
            summary = {
                'sheets': sheet_data,
                'total_sheets': len(sheet_data)
            }
            
            return ProcessingResult(
                content=json.dumps(summary, default=str),
                metadata={'type': 'excel', 'sheets': len(sheet_data)}
            )
            
        except Exception as e:
            logger.error(f"Error processing Excel: {str(e)}")
            return ProcessingResult(
                content=f"Error processing Excel file: {str(e)}",
                metadata={'type': 'excel', 'error': str(e)}
            )

    async def _process_pdf(self, content: bytes) -> ProcessingResult:
        """Process PDF file and extract text"""
        try:
            text_content = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        text_content.append(f"--- Page {page_num + 1} ---\n{text}")
            
            full_text = "\n".join(text_content) if text_content else "No text extracted from PDF"
            
            return ProcessingResult(
                content=full_text,
                metadata={'type': 'pdf', 'pages': len(text_content)}
            )
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return ProcessingResult(
                content=f"Error processing PDF: {str(e)}",
                metadata={'type': 'pdf', 'error': str(e)}
            )

    async def _process_json(self, content: bytes) -> ProcessingResult:
        """Process JSON file"""
        try:
            json_data = json.loads(content.decode('utf-8'))
            
            # For simple arrays like {"values": [1, 2, 3]}, provide direct access
            enhanced_context = ""
            if isinstance(json_data, dict) and 'values' in json_data and isinstance(json_data['values'], list):
                values = json_data['values']
                enhanced_context = f"\nThe JSON contains an array 'values' with these numbers: {values}"
                if len(values) > 0:
                    enhanced_context += f"\n- Sum: {sum(values)}"
                    enhanced_context += f"\n- Max: {max(values)}" 
                    enhanced_context += f"\n- Min: {min(values)}"
                    enhanced_context += f"\n- Average: {sum(values)/len(values):.2f}"
            
            # Create a summary for large JSON
            if isinstance(json_data, list):
                summary = f"JSON array with {len(json_data)} items. First few items: {json.dumps(json_data[:3], indent=2)}"
            elif isinstance(json_data, dict):
                summary = f"JSON object with keys: {list(json_data.keys())}. Sample: {json.dumps(dict(list(json_data.items())[:3]), indent=2)}"
            else:
                summary = json.dumps(json_data, indent=2)
            
            # Combine with enhanced context
            full_content = summary + enhanced_context
            
            return ProcessingResult(
                content=full_content,
                metadata={'type': 'json', 'size': len(content)}
            )
            
        except Exception as e:
            logger.error(f"Error processing JSON: {str(e)}")
            return ProcessingResult(
                content=content.decode('utf-8', errors='ignore'),
                metadata={'type': 'text', 'error': str(e)}
            )

    async def _process_image(self, content: bytes) -> ProcessingResult:
        """Process image with OCR"""
        try:
            # Try OCR first
            image = Image.open(io.BytesIO(content))
            ocr_text = pytesseract.image_to_string(image)
            
            if ocr_text.strip():
                return ProcessingResult(
                    content=ocr_text,
                    metadata={'type': 'image', 'processing': 'ocr', 'size': len(content)}
                )
            else:
                return ProcessingResult(
                    content="No text detected in image",
                    metadata={'type': 'image', 'processing': 'none', 'size': len(content)}
                )
                
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            # Fallback: return as base64
            base64_content = base64.b64encode(content).decode('utf-8')
            return ProcessingResult(
                content=base64_content,
                metadata={'type': 'image', 'processing': 'base64', 'error': str(e)}
            )
        
    async def _process_xml(self, content: bytes) -> ProcessingResult:
        """Process XML file"""
        try:
            import xml.etree.ElementTree as ET
            
            xml_text = content.decode('utf-8')
            root = ET.fromstring(xml_text)
            
            # Extract basic XML structure info
            xml_info = {
                'root_tag': root.tag,
                'attributes': root.attrib,
                'children_count': len(root),
                'sample_content': ET.tostring(root, encoding='unicode')[:500] + '...' if len(ET.tostring(root, encoding='unicode')) > 500 else ET.tostring(root, encoding='unicode')
            }
            
            return ProcessingResult(
                content=json.dumps(xml_info),
                metadata={'type': 'xml'}
            )
            
        except Exception as e:
            logger.error(f"Error processing XML: {str(e)}")
            return ProcessingResult(
                content=content.decode('utf-8', errors='ignore'),
                metadata={'type': 'text', 'error': str(e)}
            )

    async def _process_text(self, content: bytes) -> ProcessingResult:
        """Process text file with basic cleansing"""
        try:
            text = content.decode('utf-8')
            
            # Basic text cleansing
            cleaned_text = self._cleanse_text(text)
            
            return ProcessingResult(
                content=cleaned_text,
                metadata={'type': 'text', 'size': len(cleaned_text), 'original_size': len(text)}
            )
        except UnicodeDecodeError:
            text = content.decode('latin-1', errors='ignore')
            cleaned_text = self._cleanse_text(text)
            return ProcessingResult(
                content=cleaned_text,
                metadata={'type': 'text', 'encoding': 'latin-1', 'size': len(cleaned_text)}
            )

    def _cleanse_text(self, text: str) -> str:
        """Basic text cleansing"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common data issues
        text = re.sub(r'\bNaN\b', '', text)  # Remove NaN values
        text = re.sub(r'\bnull\b', '', text)  # Remove null values
        text = re.sub(r',\s*,', ',', text)    # Fix empty CSV cells
        
        return text.strip()

    async def generate_chart(self, data: Dict, chart_type: str = "bar") -> ProcessingResult:
        """Generate a chart image as base64"""
        try:
            import matplotlib.pyplot as plt
            import base64
            from io import BytesIO
            
            plt.figure(figsize=(10, 6))
            
            if chart_type == "bar" and 'categories' in data and 'values' in data:
                plt.bar(data['categories'], data['values'])
                plt.title(data.get('title', 'Bar Chart'))
                plt.xlabel(data.get('xlabel', 'Categories'))
                plt.ylabel(data.get('ylabel', 'Values'))
            elif chart_type == "line" and 'x' in data and 'y' in data:
                plt.plot(data['x'], data['y'])
                plt.title(data.get('title', 'Line Chart'))
                plt.xlabel(data.get('xlabel', 'X'))
                plt.ylabel(data.get('ylabel', 'Y'))
            elif chart_type == "pie" and 'labels' in data and 'sizes' in data:
                plt.pie(data['sizes'], labels=data['labels'], autopct='%1.1f%%')
                plt.title(data.get('title', 'Pie Chart'))
            else:
                return ProcessingResult(
                    content="Error: Invalid chart data",
                    metadata={'type': 'error', 'error': 'Invalid chart data'}
                )
            
            # Save to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            plt.close()
            
            base64_image = base64.b64encode(buffer.getvalue()).decode()
            
            return ProcessingResult(
                content=f"data:image/png;base64,{base64_image}",
                metadata={'type': 'chart', 'chart_type': chart_type}
            )
            
        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            return ProcessingResult(
                content=f"Error generating chart: {str(e)}",
                metadata={'type': 'error', 'error': str(e)}
            )
        
    async def advanced_analysis(self, data: Dict, analysis_type: str) -> ProcessingResult:
        """Perform advanced data analysis"""
        try:
            import pandas as pd
            import numpy as np
            
            if analysis_type == "statistics" and 'values' in data:
                values = data['values']
                df = pd.Series(values)
                
                stats = {
                    'count': len(values),
                    'mean': float(df.mean()),
                    'median': float(df.median()),
                    'std': float(df.std()),
                    'min': float(df.min()),
                    'max': float(df.max()),
                    'q1': float(df.quantile(0.25)),
                    'q3': float(df.quantile(0.75))
                }
                
                return ProcessingResult(
                    content=json.dumps(stats),
                    metadata={'type': 'statistics', 'analysis': analysis_type}
                )
                
            elif analysis_type == "correlation" and 'x' in data and 'y' in data:
                correlation = np.corrcoef(data['x'], data['y'])[0, 1]
                
                return ProcessingResult(
                    content=json.dumps({'correlation': float(correlation)}),
                    metadata={'type': 'correlation', 'analysis': analysis_type}
                )
                
        except Exception as e:
            logger.error(f"Error in advanced analysis: {str(e)}")
            return ProcessingResult(
                content=f"Error in analysis: {str(e)}",
                metadata={'type': 'error', 'error': str(e)}
            )

    async def fetch_api_data(self, url: str, headers: Optional[Dict] = None) -> ProcessingResult:
        """Fetch data from API endpoint"""
        session = await self.get_session()
        
        try:
            request_headers = headers or {}
            async with session.get(url, headers=request_headers) as response:
                response.raise_for_status()
                content_type = response.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    json_data = await response.json()
                    return ProcessingResult(
                        content=json.dumps(json_data, indent=2),
                        metadata={'type': 'api', 'content_type': 'json'}
                    )
                else:
                    text = await response.text()
                    return ProcessingResult(
                        content=text,
                        metadata={'type': 'api', 'content_type': content_type}
                    )
                    
        except Exception as e:
            logger.error(f"Error fetching API data {url}: {str(e)}")
            raise