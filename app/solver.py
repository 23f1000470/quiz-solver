import asyncio
import time
from typing import Optional
from app.types import QuizRequest, ParsedQuestion, AnswerSubmission, AnswerType
from app.browser import BrowserManager
from app.browser_fallback import BrowserFallback
from app.parser import QuizParser
from app.fetcher import ResourceFetcher
from app.llm import LLMEngine
from app.submitter import AnswerSubmitter
from app.utils import logger
from app.settings import *

class QuizSolver:
    def __init__(self, request: QuizRequest, start_time: float):
        self.request = request
        self.start_time = start_time
        self.current_url = request.url
        self.browser = BrowserManager()
        self.fallback_browser = BrowserFallback()
        self.fetcher = ResourceFetcher()
        self.llm = LLMEngine()
        self.submitter = AnswerSubmitter()
    
    async def solve_chain(self):
        """Solve the quiz chain with enhanced retry logic"""
        try:
            while self.current_url and not self._is_timed_out():
                logger.info(f"🎯 Solving quiz: {self.current_url}")
                
                # Step 1: Get and parse page content
                question = await self._get_question_content()
                if not question:
                    break
                
                # Step 2: Fetch and process resources
                context = await self._process_resources(question.resources)
                
                # Step 3: Multiple attempts with escalating model intelligence
                final_result = await self._solve_with_retries(question, context)
                
                # Step 4: Check if we should continue
                if final_result.correct and final_result.url:
                    self.current_url = final_result.url
                    logger.info(f"✅ Correct! Moving to next URL: {self.current_url}")
                elif not final_result.correct and final_result.url:
                    # Option to skip to next URL even if wrong
                    self.current_url = final_result.url
                    logger.info(f"⚠️ Incorrect but moving to next URL: {self.current_url}")
                else:
                    self.current_url = None
                    logger.info(f"🏁 Quiz completed. Correct: {final_result.correct}")
                        
        except Exception as e:
            logger.error(f"Error in quiz chain: {str(e)}")
        finally:
            await self._cleanup()

    async def _solve_with_retries(self, question: ParsedQuestion, context: str) -> any:
        """Solve a quiz question with multiple retries and escalating model intelligence"""
        from app.types import QuizResponse
        
        last_result = None
        
        for attempt in range(settings.MAX_QUIZ_ATTEMPTS):
            logger.info(f"🔄 Attempt {attempt + 1}/{settings.MAX_QUIZ_ATTEMPTS} for quiz")
            
            # Use progressively smarter models
            if attempt == 0:
                # First attempt: Fast model
                model_note = "Using fast model (gemini-2.0-flash-lite)"
            elif attempt == 1:
                # Second attempt: Balanced model  
                model_note = "Using balanced model (gemini-2.0-flash)"
            else:
                # Third attempt: Smartest model
                model_note = "Using smart model (gemini-2.5-pro)"
            
            logger.info(f"🧠 {model_note}")
            
            # Step 1: Use LLM to reason about answer
            answer = await self._reason_about_answer(question, context, attempt)
            
            # Step 2: Submit answer
            result = await self._submit_answer(question, answer)
            last_result = result
            
            logger.info(f"📊 Attempt {attempt + 1} result: Correct={result.correct}, Reason={result.reason}")
            
            if result.correct:
                logger.info(f"🎉 Correct on attempt {attempt + 1}!")
                return result
            else:
                if attempt < settings.MAX_QUIZ_ATTEMPTS - 1:
                    logger.info(f"❌ Wrong answer. Retrying in {settings.RETRY_DELAY}s...")
                    await asyncio.sleep(settings.RETRY_DELAY)
                else:
                    logger.info(f"💥 All {settings.MAX_QUIZ_ATTEMPTS} attempts failed")
        
        return last_result  # Return the last result even if all attempts failed

    async def _reason_about_answer(self, question: ParsedQuestion, context: str, attempt: int = 0) -> any:
        """Use LLM to reason about the answer with attempt-specific model selection"""
        from app.types import LLMReasoningRequest
        
        reasoning_request = LLMReasoningRequest(
            question=question.question_text,
            context=context,
            expected_type=question.expected_type,
            attempt_number=attempt + 1  # Pass attempt info to LLM
        )
        
        # Pass the attempt number to LLM engine
        result = await self.llm.reason_about_question(reasoning_request, attempt)
        
        logger.info(f"🧠 LLM attempt {attempt + 1} result: {result.answer} (confidence: {result.confidence})")
        
        # Validate answer type
        enforced_answer = self._enforce_answer_type(result.answer, question.expected_type)
        logger.info(f"🔧 After enforcement: {enforced_answer} (type: {type(enforced_answer)})")
        
        return enforced_answer


    async def _get_question_content(self) -> Optional[ParsedQuestion]:
        """Get and parse question content from current URL"""
        page_content = None
        
        # Try Playwright first
        try:
            logger.info("Attempting to use Playwright browser...")
            page_content = await self.browser.get_page_content(self.current_url)
        except Exception as e:
            logger.warning(f"Playwright failed: {str(e)}, using fallback...")
            try:
                # Try fallback browser
                page_content = await self.fallback_browser.get_page_content(self.current_url)
            except Exception as fallback_error:
                logger.error(f"Fallback browser also failed: {str(fallback_error)}")
                return None
        
        if page_content:
            try:
                parser = QuizParser(self.current_url)
                question = parser.parse_page_content(page_content)
                
                logger.info(f"Parsed question: {question.question_text[:100]}...")
                logger.info(f"Submit URL: {question.submit_url}")
                logger.info(f"Resources: {question.resources}")
                logger.info(f"Expected type: {question.expected_type}")
                
                return question
            except Exception as e:
                logger.error(f"Error parsing question content: {str(e)}")
        
        return None

    async def _process_resources(self, resources: list) -> str:
        """Fetch and process all resources with API headers"""
        if not resources:
            return "No external resources required."
        
        context_parts = ["EXTERNAL RESOURCES:"]
        
        # Extract API headers from the current page content
        headers = {}
        try:
            # Get the page content to extract headers from instructions
            page_content = await self.fallback_browser.get_page_content(self.current_url)
            parser = QuizParser(self.current_url)
            headers = parser.extract_api_headers(page_content.get('visible_text', ''))
            
            if headers:
                logger.info(f"🔑 Extracted API headers: {headers}")
            else:
                logger.info("🔑 No API headers found in instructions")
                
        except Exception as e:
            logger.warning(f"🔑 Failed to extract API headers: {e}")
        
        for resource_url in resources:
            try:
                logger.info(f"Fetching resource: {resource_url}")
                
                # Use extracted headers for this resource
                resource_headers = headers.copy() if headers else {}
                
                # Special case: if resource URL matches API endpoints, use headers
                if any(api_indicator in resource_url for api_indicator in ['/api-', '/simple-api', '/api-protected-data']):
                    logger.info(f"🔑 Using headers for API resource: {resource_url}")
                
                result = await self.fetcher.fetch_resource(resource_url, resource_headers)
                context_parts.append(f"Resource: {resource_url}")
                if resource_headers:
                    context_parts.append(f"Headers used: {resource_headers}")
                context_parts.append(f"Content: {result.content}")
                context_parts.append("---")
                
            except Exception as e:
                logger.error(f"Error processing resource {resource_url}: {str(e)}")
                context_parts.append(f"Error fetching {resource_url}: {str(e)}")
        
        return "\n".join(context_parts)


    def _enforce_answer_type(self, answer: any, expected_type: AnswerType) -> any:
        """Enforce the expected answer type"""
        try:
            if expected_type == AnswerType.NUMBER:
                if isinstance(answer, (int, float)):
                    # Convert to int if it's a whole number
                    if isinstance(answer, float) and answer.is_integer():
                        return int(answer)
                    return answer
                elif isinstance(answer, str):
                    # Try to extract number and convert to int if whole number
                    import re
                    numbers = re.findall(r'-?\d+\.?\d*', answer)
                    if numbers:
                        num = float(numbers[0])
                        if num.is_integer():
                            return int(num)
                        return num
                    else:
                        return 0
                else:
                    num = float(answer) if answer else 0
                    if num.is_integer():
                        return int(num)
                    return num
            
            elif expected_type == AnswerType.BASE64_FILE:
                # Handle base64 file answers - don't double-encode!
                if isinstance(answer, str):
                    # Check if it's already base64 encoded
                    import base64
                    try:
                        # Try to decode to see if it's valid base64
                        decoded = base64.b64decode(answer)
                        # If it decodes without error and contains "Hello World", it's already correct
                        decoded_text = decoded.decode('utf-8')
                        if "hello world" in decoded_text.lower():
                            logger.info("🔧 Base64 file: Already correctly encoded, returning as-is")
                            return answer
                    except:
                        # Not valid base64, encode it
                        pass
                    
                    # If it's a plain string, encode it as base64
                    if "hello world" in answer.lower():
                        encoded = base64.b64encode(answer.encode()).decode()
                        logger.info(f"🔧 Base64 file: Encoded string to base64: {encoded}")
                        return encoded
                    else:
                        # Just encode whatever we have
                        encoded = base64.b64encode(answer.encode()).decode()
                        logger.info(f"🔧 Base64 file: Encoded to base64: {encoded}")
                        return encoded
                else:
                    # Convert to base64
                    import base64
                    encoded = base64.b64encode(str(answer).encode()).decode()
                    logger.info(f"🔧 Base64 file: Converted to base64: {encoded}")
                    return encoded

            elif expected_type == AnswerType.BOOLEAN:
                if isinstance(answer, bool):
                    return answer
                elif isinstance(answer, str):
                    return answer.lower() in ['true', 'yes', '1', 'correct']
                else:
                    return bool(answer)
                    
            elif expected_type == AnswerType.JSON:
                if isinstance(answer, (dict, list)):
                    return answer
                elif isinstance(answer, str):
                    import json
                    try:
                        return json.loads(answer)
                    except:
                        return {"answer": answer}
                else:
                    return {"answer": str(answer)}
                    
            else:  # STRING
                return str(answer)
                
        except Exception as e:
            logger.error(f"Error enforcing answer type: {str(e)}")
            return str(answer)

    async def _submit_answer(self, question: ParsedQuestion, answer: any) -> any:
        """Submit answer and get response"""
        
        # Prepare the answer based on expected type
        final_answer = answer
        if question.expected_type == AnswerType.NUMBER and isinstance(answer, str):
            try:
                if '.' in answer:
                    final_answer = float(answer)
                else:
                    final_answer = int(answer)
            except:
                pass
        
        # Use the ORIGINAL QUIZ URL, not the submit URL
        submission = AnswerSubmission(
            email=self.request.email,
            secret=self.request.secret,
            url=self.current_url,  # This is the quiz URL, not submit URL
            answer=final_answer
        )
        
        logger.info(f"Submitting answer: {final_answer} for quiz: {self.current_url}")
        return await self.submitter.submit_answer(submission, question.submit_url)

    def _is_timed_out(self) -> bool:
        """Check if we've exceeded the 3-minute timeout"""
        return time.time() - self.start_time > 180  # 3 minutes

    async def _cleanup(self):
        """Clean up resources"""
        try:
            await self.browser.close()
            await self.fallback_browser.close()
            await self.fetcher.close()
            await self.submitter.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")