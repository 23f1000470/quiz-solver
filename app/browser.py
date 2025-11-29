import asyncio
import base64
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from app.settings import settings
from app.utils import logger

import platform

    
class BrowserManager:
    def __init__(self):
        self.browser = None
        self.context = None
        self.playwright = None
        self._setup_done = False

    async def setup(self):
        """Initialize browser context with proper event loop handling"""
        if self._setup_done:
            return
        
        if platform.system() == "Windows":
            raise NotImplementedError("Playwright not supported on Windows, using fallback")

        try:
            self.playwright = await async_playwright().start()
            
            # Use a different approach for Windows compatibility
            self.browser = await self.playwright.chromium.launch(
                headless=settings.BROWSER_HEADLESS,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--allow-running-insecure-content',
                    '--disable-dev-shm-usage'
                ]
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True,
                java_script_enabled=True
            )
            
            self._setup_done = True
            logger.info("Browser setup completed successfully")
            
        except Exception as e:
            logger.error(f"Browser setup failed: {str(e)}")
            await self.close()
            raise

            
    async def close(self):
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error during browser cleanup: {str(e)}")
        finally:
            self.browser = None
            self.context = None
            self.playwright = None
            self._setup_done = False

    async def get_page_content(self, url: str) -> str:
        """Get fully rendered page content with JavaScript execution"""
        if not self._setup_done:
            await self.setup()

        page = None
        try:
            page = await self.context.new_page()
            
            # Set longer timeout for navigation
            page.set_default_timeout(settings.BROWSER_TIMEOUT)
            page.set_default_navigation_timeout(settings.BROWSER_TIMEOUT)
            
            # Navigate to URL
            logger.info(f"Navigating to: {url}")
            response = await page.goto(url, wait_until='networkidle')
            
            if not response or response.status >= 400:
                logger.warning(f"Page load issue: {response.status if response else 'No response'}")
            
            # Wait for potential dynamic content
            await page.wait_for_timeout(2000)
            
            # Extract visible text content
            content = await page.content()
            
            # Also get visible text for fallback parsing
            visible_text = await page.evaluate("""
                () => {
                    // Get all visible text
                    const bodyText = document.body.innerText;
                    
                    // Look for base64 encoded content in script tags
                    const scripts = Array.from(document.querySelectorAll('script'));
                    let scriptContent = '';
                    
                    scripts.forEach(script => {
                        const content = script.textContent || script.innerHTML;
                        if (content.includes('atob(') || content.includes('base64')) {
                            scriptContent += content + '\\n';
                        }
                    });
                    
                    return {
                        body_text: bodyText,
                        script_content: scriptContent,
                        full_html: document.documentElement.outerHTML
                    };
                }
            """)
            
            result = {
                'html': content,
                'visible_text': visible_text['body_text'],
                'scripts': visible_text['script_content'],
                'full_html': visible_text['full_html']
            }
            
            logger.info(f"Successfully extracted content from {url}")
            return result
            
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout loading page: {url}")
            # Try to get whatever content we have
            if page:
                try:
                    content = await page.content()
                    return {'html': content, 'visible_text': '', 'scripts': '', 'full_html': content}
                except:
                    pass
            raise
        except Exception as e:
            logger.error(f"Error loading page {url}: {str(e)}")
            raise
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass

    def extract_base64_content(self, script_content: str) -> str:
        """Extract and decode base64 content from script tags"""
        import re
        
        decoded_content = []
        
        # Look for atob('base64content') patterns
        atob_pattern = r"atob\(['\"]([^'\"]+)['\"]\)"
        base64_pattern = r"['\"]([A-Za-z0-9+/=]{20,}={0,2})['\"]"
        
        # First try atob patterns
        atob_matches = re.findall(atob_pattern, script_content)
        for match in atob_matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8')
                decoded_content.append(decoded)
                logger.info(f"Decoded base64 content: {decoded[:100]}...")
            except Exception as e:
                logger.warning(f"Failed to decode base64 from atob: {str(e)}")
                continue
                
        # Then try direct base64 strings
        direct_matches = re.findall(base64_pattern, script_content)
        for match in direct_matches:
            if len(match) > 20:  # Likely base64 content
                try:
                    decoded = base64.b64decode(match).decode('utf-8')
                    decoded_content.append(decoded)
                except:
                    continue
        
        return "\n".join(decoded_content)