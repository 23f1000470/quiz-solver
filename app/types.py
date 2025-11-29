from pydantic import BaseModel, Field
from typing import Optional, Union, Any, Dict, List
from enum import Enum

class AnswerType(str, Enum):
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    JSON = "json"
    BASE64_FILE = "base64_file"

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

class QuizResponse(BaseModel):
    correct: bool
    url: Optional[str] = None
    reason: Optional[str] = None

class AnswerSubmission(BaseModel):
    email: str
    secret: str
    url: str
    answer: Union[int, float, str, bool, Dict[str, Any], List[Any]]

class ParsedQuestion(BaseModel):
    question_text: str
    submit_url: str
    resources: List[str] = Field(default_factory=list)
    expected_type: AnswerType = AnswerType.STRING
    instructions: Optional[str] = None

class ProcessingResult(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class LLMReasoningRequest(BaseModel):
    question: str
    context: str
    expected_type: AnswerType
    attempt_number: int = 1

class LLMReasoningResponse(BaseModel):
    reasoning: str
    answer: Union[int, float, str, bool, Dict[str, Any], List[Any]]
    confidence: float