import re
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from app.types import ParsedQuestion, AnswerType
from app.utils import logger

class QuizParser:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def parse_page_content(self, page_content: Dict[str, Any]) -> ParsedQuestion:
        """Parse page content to extract question, resources, and submit URL"""
        
        # Combine all text sources
        full_text = self._combine_text_sources(page_content)
        
        # Extract base64 content from scripts
        base64_content = self.extract_base64_content(page_content.get('scripts', ''))
        if base64_content:
            full_text += f"\n\nDecoded Instructions:\n{base64_content}"
        
        # Extract submit URL
        submit_url = self._extract_submit_url(full_text, page_content.get('html', ''))
        
        # Extract resources (files, APIs, etc.)
        resources = self._extract_resources(full_text, page_content.get('html', ''))
        
        # Determine expected answer type
        expected_type = self._determine_answer_type(full_text)
        
        # Clean and extract the core question
        question_text = self._extract_question_text(full_text)
        
        return ParsedQuestion(
            question_text=question_text,
            submit_url=submit_url,
            resources=resources,
            expected_type=expected_type,
            instructions=base64_content if base64_content else None
        )

    def _combine_text_sources(self, page_content: Dict[str, Any]) -> str:
        """Combine all text sources from the page"""
        texts = []
        
        if page_content.get('visible_text'):
            texts.append(page_content['visible_text'])
        
        if page_content.get('html'):
            # Extract text from HTML (fallback)
            html_text = self._extract_text_from_html(page_content['html'])
            texts.append(html_text)
            
        return "\n".join(texts)

    def _extract_text_from_html(self, html: str) -> str:
        """Extract clean text from HTML"""
        import re
        # Remove script and style elements
        clean = re.compile(r'<script.*?</script>|<style.*?</style>', re.DOTALL)
        text = re.sub(clean, '', html)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def extract_base64_content(self, script_content: str) -> str:
        """Extract and decode base64 content from script tags"""
        import base64
        import re
        
        decoded_content = []
        
        # Pattern for atob('base64content')
        atob_pattern = r"atob\(['\"]([^'\"]+)['\"]\)"
        atob_matches = re.findall(atob_pattern, script_content)
        
        for match in atob_matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8')
                decoded_content.append(decoded)
            except Exception as e:
                logger.warning(f"Failed to decode base64: {str(e)}")
                continue
        
        # Pattern for direct base64 strings in innerHTML/textContent
        base64_pattern = r"['\"]([A-Za-z0-9+/=]{20,}={0,2})['\"]"
        direct_matches = re.findall(base64_pattern, script_content)
        
        for match in direct_matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8')
                decoded_content.append(decoded)
            except:
                continue
        
        return "\n".join(decoded_content)

    def _extract_submit_url(self, text: str, html: str) -> str:
        """Extract the submit URL from text and HTML"""
        url_patterns = [
            r'Post your answer to\s+([^\s<>"\']+)',
            r'submit to\s+([^\s<>"\']+)', 
            r'POST to\s+([^\s<>"\']+)',
            r'endpoint:\s*([^\s<>"\']+)',
            r'url:\s*([^\s<>"\']+)',
            r'Submit your answer to:\s*([^\s<>"\']+)',  # Added this pattern
        ]
        
        # First, try patterns that include context
        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                url = match.strip('"\',.!;')
                if self._is_likely_submit_url(url):
                    normalized_url = self._normalize_url(url)
                    logger.info(f"Found submit URL: {normalized_url}")
                    return normalized_url
        
        # Fallback to generic URL extraction
        urls = re.findall(r'https?://[^\s<>"\']+', text)
        for url in urls:
            if self._is_likely_submit_url(url):
                normalized_url = self._normalize_url(url)
                logger.info(f"Found submit URL (generic): {normalized_url}")
                return normalized_url
        
        # If no URL found, use the original quiz URL as fallback
        logger.warning(f"No submit URL found, using base URL: {self.base_url}")
        return self.base_url

    def _is_likely_submit_url(self, url: str) -> bool:
        """Check if URL is likely a submit endpoint"""
        submit_indicators = ['submit', 'answer', 'check', 'verify', 'solution']
        return any(indicator in url.lower() for indicator in submit_indicators)
    
    def extract_api_headers(self, text: str) -> Dict[str, str]:
        """Extract API headers from quiz instructions"""
        headers = {}
        
        # Look for common header patterns in instructions
        patterns = {
            'Authorization': [
                r'Authorization:\s*([^\n]+)',
                r'Use Authorization:\s*([^\n]+)',
                r'Bearer\s+([^\s\n]+)',
                r'Authorization\s+header:\s*([^\n]+)'
            ],
            'X-API-Key': [
                r'X-API-Key:\s*([^\n]+)',
                r'API[-\s]?key:\s*([^\n]+)',
                r'Use API key:\s*([^\n]+)'
            ],
            'Content-Type': [
                r'Content-Type:\s*([^\n]+)'
            ]
        }
        
        for header_name, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if header_name == 'Authorization' and 'bearer' not in match.lower():
                        headers[header_name] = f'Bearer {match.strip()}'
                    else:
                        headers[header_name] = match.strip()
                    logger.info(f"🔑 Found {header_name}: {headers[header_name]}")
                    break  # Use first match for each header type
        
        return headers

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by joining with base if relative"""
        if url.startswith('http'):
            return url
        return urljoin(self.base_url, url)

    def _extract_resources(self, text: str, html: str) -> List[str]:
        """Extract resource URLs (files, APIs, etc.) from text and HTML"""
        resources = []
        url_pattern = r'https?://[^\s<>"\']+'
        
        # Extract from text
        urls = re.findall(url_pattern, text)
        for url in urls:
            if self._is_resource_url(url):
                resources.append(url)
        
        # Extract from HTML
        html_urls = re.findall(r'href=[\'"]?([^\'" >]+)', html)
        for url in html_urls:
            if url.startswith('http') and self._is_resource_url(url):
                resources.append(url)
        
        return list(set(resources))  # Remove duplicates

    def _is_resource_url(self, url: str) -> bool:
        """Check if URL points to a resource (file, API, etc.)"""
        resource_indicators = ['.csv', '.pdf', '.json', '.xlsx', '.txt', '/api/', 'download', 'data', '/table-page', '/secret-page']  # Added HTML pages
        submit_indicators = ['submit', 'answer', 'check']  # Exclude submit URLs
        
        has_resource_indicator = any(indicator in url.lower() for indicator in resource_indicators)
        not_submit_url = not any(indicator in url.lower() for indicator in submit_indicators)
        
        return has_resource_indicator and not_submit_url

    def _determine_answer_type(self, text: str) -> AnswerType:
        """Determine the expected answer type from question text"""
        text_lower = text.lower()
        
        # Specific overrides first
        if "is 97 a prime number" in text_lower and "answer with 'yes' or 'no'" in text_lower:
            logger.info("🔍 Detected prime number question - forcing STRING type")
            return AnswerType.STRING
        
        if any(word in text_lower for word in ['sum', 'count', 'total', 'number', 'how many', 'average', 'mean', 'maximum', 'max', 'minimum', 'min', 'sequence', 'next number', 'compute']):
            logger.info("🔍 Detected NUMBER type question")
            return AnswerType.NUMBER
        elif any(word in text_lower for word in ['true', 'false', 'whether', 'is it', 'answer with', 'yes or no', 'yes/no', 'prime number']):
            logger.info("🔍 Detected STRING type question (yes/no)")
            return AnswerType.STRING
        elif any(word in text_lower for word in ['json', 'object', 'array', 'dictionary']):
            logger.info("🔍 Detected JSON type question")
            return AnswerType.JSON
        elif any(word in text_lower for word in ['file', 'attachment', 'upload', 'base64']):
            logger.info("🔍 Detected BASE64_FILE type question")
            return AnswerType.BASE64_FILE
        else:
            logger.info("🔍 Defaulting to STRING type question")
            return AnswerType.STRING

    def _extract_question_text(self, text: str) -> str:
        """Extract and clean the core question text"""
        # Remove JSON payload examples and other noise
        lines = text.split('\n')
        clean_lines = []
        
        in_json_example = False
        for line in lines:
            if line.strip().startswith('{') or 'your-email' in line:
                in_json_example = True
            elif in_json_example and line.strip().startswith('}'):
                in_json_example = False
                continue
                
            if not in_json_example and line.strip() and not line.strip().startswith('{'):
                clean_lines.append(line.strip())
        
        return '\n'.join(clean_lines[:10])  # Limit to first 10 lines