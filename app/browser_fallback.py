import aiohttp
import base64
import re
from bs4 import BeautifulSoup
from app.utils import logger

class BrowserFallback:
    """Fallback browser using requests + BeautifulSoup when Playwright fails"""
    
    def __init__(self):
        self.session = None

    async def get_session(self):
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def get_page_content(self, url: str) -> dict:
        """Get page content without JavaScript execution"""
        session = await self.get_session()
        
        try:
            logger.info(f"Using fallback browser for: {url}")
            
            async with session.get(url) as response:
                response.raise_for_status()
                html_content = await response.text()
                
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style tags for clean text
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get visible text
            visible_text = soup.get_text(separator='\n', strip=True)
            
            # Extract script content separately
            scripts = soup.find_all('script')
            script_content = ""
            for script in scripts:
                if script.string:
                    script_content += script.string + "\n"
            
            return {
                'html': html_content,
                'visible_text': visible_text,
                'scripts': script_content,
                'full_html': html_content
            }
            
        except Exception as e:
            logger.error(f"Fallback browser failed for {url}: {str(e)}")
            raise