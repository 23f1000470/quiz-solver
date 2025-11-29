import google.generativeai as genai
import asyncio
import json
from typing import List, Optional, Dict, Any
from app.settings import settings
from app.types import LLMReasoningRequest, LLMReasoningResponse, AnswerType
from app.utils import logger, async_retry

class LLMEngine:
    def __init__(self):
        self.models = []
        self.current_model_index = 0
        self.setup_models()

    def setup_models(self):
        """Setup Gemini models with fallback chain"""
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Test available models first
            available_models = genai.list_models()
            available_model_names = [model.name for model in available_models]
            
            print(f"📋 Available models: {available_model_names}")
            
            # Try to load models in order of preference
            model_configs = [
                (settings.GEMINI_MODEL_PRIMARY, "primary"),
            ] + [(model, "fallback") for model in settings.GEMINI_MODEL_FALLBACKS]
            
            for model_name, role in model_configs:
                try:
                    # Remove 'models/' prefix if present and use full name
                    full_model_name = f"models/{model_name}" if not model_name.startswith('models/') else model_name
                    
                    if full_model_name in available_model_names:
                        model = genai.GenerativeModel(model_name)
                        self.models.append((model, model_name, role))
                        logger.info(f"Loaded {role} model: {model_name}")
                    else:
                        logger.warning(f"Model {model_name} not available")
                        
                except Exception as e:
                    logger.warning(f"Failed to load model {model_name}: {str(e)}")
                    
            if not self.models:
                # Fallback to any available model
                for model_name in available_model_names:
                    if 'gemini' in model_name and 'flash' in model_name:
                        try:
                            model = genai.GenerativeModel(model_name)
                            self.models.append((model, model_name, "emergency"))
                            logger.info(f"Loaded emergency model: {model_name}")
                            break
                        except:
                            continue
                            
            if not self.models:
                raise Exception("No Gemini models available")
                
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {str(e)}")
            raise

    @async_retry(max_attempts=3, delay=1)
    async def reason_about_question(self, request: LLMReasoningRequest, attempt: int = 0) -> LLMReasoningResponse:
        """Use LLM to reason about the question with attempt-based model selection"""
        
        prompt = self._build_prompt(request, attempt)  # Pass attempt here
        
        # Select models based on attempt number
        if attempt == 0:
            # First attempt: Use primary and first fallback
            models_to_try = self.models[:2]
        elif attempt == 1:
            # Second attempt: Use balanced models  
            models_to_try = self.models[1:3]
        else:
            # Third attempt: Use smartest models
            models_to_try = self.models[2:]
        
        logger.info(f"🎯 Attempt {attempt + 1}: Trying {len(models_to_try)} models")
        
        for model_index, (model, model_name, role) in enumerate(models_to_try):
            try:
                logger.info(f"Using {role} model: {model_name} (attempt {attempt + 1}.{model_index + 1})")
                
                # Run synchronous Gemini call in thread pool
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: model.generate_content(prompt)
                )
                
                result = self._parse_llm_response(response.text, request.expected_type)
                result.confidence = self._calculate_confidence(response, result.answer)
                
                logger.info(f"LLM reasoning successful with {model_name}, confidence: {result.confidence}")
                return result
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {str(e)}")
                if model_index == len(models_to_try) - 1:
                    logger.error(f"All models failed for attempt {attempt + 1}, using fallback reasoning")
                    return await self._fallback_reasoning(request)
                continue

    def _build_prompt(self, request: LLMReasoningRequest, attempt: int = 0) -> str:
        """Build the prompt for LLM reasoning with attempt context"""
        
        type_instructions = {
            AnswerType.NUMBER: "You MUST respond with ONLY a number. No explanation, no text, just the numerical answer.",
            AnswerType.STRING: "You MUST respond with ONLY a string answer. No additional text.",
            AnswerType.BOOLEAN: "You MUST respond with ONLY 'true' or 'false'. No other text.",
            AnswerType.JSON: "You MUST respond with valid JSON only. No other text.",
            AnswerType.BASE64_FILE: "You MUST respond with the file content or instructions for file generation."
        }
        
        # Add attempt context to prompt
        attempt_context = ""
        if attempt > 0:
            attempt_context = f"\nNOTE: This is attempt {attempt + 1}. Previous attempts were incorrect. Please reconsider carefully and double-check your reasoning."
        
        # Special handling for different question types
        additional_instruction = ""
        
        # Handle yes/no questions specifically
        question_lower = request.question.lower()
        if any(phrase in question_lower for phrase in ["answer 'yes' or 'no'", "answer with 'yes'", "yes or no", "yes/no"]):
            additional_instruction = "You MUST respond with ONLY 'yes' or 'no'. Do not use numbers, do not use true/false."
            # Override the type instruction for yes/no questions
            type_instructions[AnswerType.STRING] = "You MUST respond with ONLY 'yes' or 'no'. No other text."
        elif "table" in question_lower and "sum" in question_lower:
            additional_instruction = "Extract the numbers from the table and compute the sum. Return ONLY the total sum as a number."
        elif "table" in question_lower:
            additional_instruction = "Extract the relevant data from the table. Return ONLY the answer."
        elif "json" in question_lower and "sum" in question_lower:
            additional_instruction = "Extract the numbers from the JSON and compute the sum. Return ONLY the number."
        elif "json" in question_lower and "max" in question_lower:
            additional_instruction = "Extract the numbers from the JSON and find the maximum value. Return ONLY the number."
        elif "json" in question_lower and "average" in question_lower:
            additional_instruction = "Extract the numbers from the JSON and compute the average. Return ONLY the number."
        elif "pdf" in question_lower:
            additional_instruction = "Extract the number from the PDF text as described. Return ONLY the number."
        
        base_prompt = f"""
        QUESTION: {request.question}
        
        CONTEXT AND DATA: {request.context}
        
        INSTRUCTIONS:
        1. Analyze the question and available data carefully
        2. Perform any necessary calculations or reasoning
        3. {type_instructions[request.expected_type]}
        4. {additional_instruction}
        5. {attempt_context}
        6. Be precise and accurate
        
        IMPORTANT: Your response must be ONLY the answer in the required format. No additional text, no explanations, no markdown.
        
        Required output type: {request.expected_type.value}
        
        ANSWER:
        """
        
        return base_prompt

    def _parse_llm_response(self, response_text: str, expected_type: AnswerType) -> LLMReasoningResponse:
        """Parse LLM response and convert to appropriate type"""
        
        # Clean the response
        cleaned_text = response_text.strip()
        logger.info(f"🧠 LLM raw response: '{cleaned_text}' for type: {expected_type}")
        
        try:
            if expected_type == AnswerType.NUMBER:
                # Extract numbers from text
                import re
                numbers = re.findall(r'-?\d+\.?\d*', cleaned_text)
                if numbers:
                    # Try float first, then check if it should be int
                    num = float(numbers[0])
                    if num.is_integer():
                        answer = int(num)
                        logger.info(f"🧠 Converted LLM response '{numbers[0]}' to int: {answer}")
                    else:
                        answer = num
                        logger.info(f"🧠 Converted LLM response '{numbers[0]}' to float: {answer}")
                else:
                    answer = 0
                    logger.info(f"🧠 No numbers found, using default: {answer}")
                    
            elif expected_type == AnswerType.BOOLEAN:
                answer = cleaned_text.lower() in ['true', 'yes', '1', 'correct']
                logger.info(f"🧠 Boolean conversion: '{cleaned_text}' -> {answer}")
                
            elif expected_type == AnswerType.JSON:
                # Try to parse as JSON
                try:
                    # Find JSON in response
                    json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                    if json_match:
                        answer = json.loads(json_match.group())
                        logger.info(f"🧠 JSON parsing successful")
                    else:
                        answer = {"error": "No valid JSON found"}
                        logger.info(f"🧠 No JSON found in response")
                except:
                    answer = {"error": "Invalid JSON format"}
                    logger.info(f"🧠 JSON parsing failed")
                    
            elif expected_type == AnswerType.BASE64_FILE:
                # For file responses, we might need additional processing
                answer = cleaned_text
                logger.info(f"🧠 Base64/file response: '{cleaned_text}'")
                
            else:  # STRING
                # For string type, just return the cleaned text as-is
                answer = cleaned_text
                logger.info(f"🧠 String response kept as-is: '{cleaned_text}'")
                
            return LLMReasoningResponse(
                reasoning=response_text,
                answer=answer,
                confidence=0.8  # Temporary, will be updated
            )
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            # Fallback to string
            return LLMReasoningResponse(
                reasoning=response_text,
                answer=cleaned_text,
                confidence=0.5
            )

    def _calculate_confidence(self, response, answer: Any) -> float:
        """Calculate confidence score for the answer"""
        # Simple confidence calculation based on response properties
        confidence = 0.7  # Base confidence
        
        # Increase confidence if response has citations or seems certain
        if hasattr(response, 'prompt_feedback'):
            if response.prompt_feedback and response.prompt_feedback.block_reason is None:
                confidence += 0.2
                
        # Decrease confidence for empty or very short answers
        if not answer or (isinstance(answer, str) and len(answer.strip()) < 2):
            confidence -= 0.3
            
        return max(0.1, min(1.0, confidence))

    async def _fallback_reasoning(self, request: LLMReasoningRequest) -> LLMReasoningResponse:
        """Fallback reasoning when all models fail"""
        logger.warning("Using fallback reasoning")
        
        # Simple heuristic-based fallback
        question_lower = request.question.lower()
        
        if 'sum' in question_lower and 'value' in question_lower:
            # Try to extract and sum numbers from context
            import re
            numbers = re.findall(r'\d+', request.context)
            if numbers:
                total = sum(map(int, numbers))
                return LLMReasoningResponse(
                    reasoning="Fallback: Summed all numbers found in context",
                    answer=total,
                    confidence=0.3
                )
        
        # Default fallback
        return LLMReasoningResponse(
            reasoning="Fallback: All models failed, using default response",
            answer="Unknown" if request.expected_type == AnswerType.STRING else 0,
            confidence=0.1
        )

    async def validate_answer(self, question: str, answer: Any, expected_type: AnswerType) -> bool:
        """Use LLM to validate if answer seems reasonable"""
        try:
            prompt = f"""
            Question: {question}
            Proposed Answer: {answer}
            Expected Type: {expected_type.value}
            
            Does this answer seem reasonable and correct for the question? 
            Respond with ONLY 'true' or 'false'.
            """
            
            model = self.models[0][0]  # Use primary model
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.generate_content(prompt)
            )
            
            validation = response.text.strip().lower()
            return validation in ['true', 'yes']
            
        except:
            return True  # If validation fails, assume answer is OK