import aiohttp
import json
from typing import Optional, Dict, Any
from app.types import AnswerSubmission, QuizResponse
from app.utils import logger, async_retry

class AnswerSubmitter:
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

    @async_retry(max_attempts=3, delay=1)
    async def submit_answer(self, submission: AnswerSubmission, submit_url: str) -> QuizResponse:
        """Submit answer to the quiz endpoint with strict size validation"""
        session = await self.get_session()
        
        try:
            # Prepare payload
            payload = {
                "email": submission.email,
                "secret": submission.secret,
                "url": submission.url,
                "answer": submission.answer
            }
            
            # Strict 1MB validation
            if not self._validate_payload_size(payload):
                logger.error("❌ Payload exceeds 1MB limit")
                return QuizResponse(
                    correct=False,
                    url=None,
                    reason="Payload size exceeds 1MB limit"
                )
            
            logger.info(f"Submitting answer to {submit_url}")
            logger.info(f"Payload size: {self._get_payload_size(payload)} bytes")
            
            # Make POST request
            async with session.post(submit_url, json=payload) as response:
                response_text = await response.text()
                
                logger.info(f"Response status: {response.status}")
                
                if response.status == 200:
                    try:
                        data = json.loads(response_text)
                        return QuizResponse(**data)
                    except json.JSONDecodeError:
                        return QuizResponse(
                            correct=True if 'correct' in response_text.lower() else False,
                            url=None,
                            reason=response_text
                        )
                else:
                    logger.error(f"Submission failed with status {response.status}: {response_text}")
                    return QuizResponse(
                        correct=False,
                        url=None,
                        reason=f"HTTP {response.status}: {response_text}"
                    )
                    
        except Exception as e:
            logger.error(f"Error submitting answer: {str(e)}")
            return QuizResponse(
                correct=False,
                url=None, 
                reason=str(e)
            )

    def _validate_payload_size(self, payload: dict) -> bool:
        """Validate that payload is under 1MB"""
        payload_size = self._get_payload_size(payload)
        return payload_size < 1_000_000  # 1MB limit

    def _get_payload_size(self, payload: dict) -> int:
        """Calculate the size of payload in bytes"""
        import sys
        return sys.getsizeof(json.dumps(payload))

    def _compress_payload(self, payload: dict) -> dict:
        """Compress payload if it's too large"""
        if isinstance(payload.get('answer'), str) and len(payload['answer']) > 500_000:
            # Truncate very large string answers
            payload['answer'] = payload['answer'][:500_000] + "...[truncated]"
            logger.warning("📦 Large answer truncated to fit 1MB limit")
        
        return payload