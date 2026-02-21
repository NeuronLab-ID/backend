"""
Pydantic schemas for API requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Literal
from datetime import datetime


# ========== Auth Schemas ==========


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)


# ========== Problem Schemas ==========


class ProblemSummary(BaseModel):
    id: int
    title: str
    category: str
    difficulty: str
    has_quest: bool = False


class ProblemListResponse(BaseModel):
    problems: List[ProblemSummary]
    total: int


# ========== Execution Schemas ==========


class ExecuteRequest(BaseModel):
    problem_id: int
    code: str = Field(..., max_length=50000)
    framework: Optional[Literal["pytorch", "tinygrad", "cuda"]] = "pytorch"


class TestResult(BaseModel):
    test_number: int
    passed: bool
    input: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    error: Optional[str] = None


class ExecuteResponse(BaseModel):
    success: bool
    results: List[TestResult] = []
    error: Optional[str] = None
    hint: Optional[str] = None
    execution_time: float = 0


# ========== Submission Schemas ==========


class SubmissionResponse(BaseModel):
    id: int
    problem_id: int
    passed: bool
    created_at: datetime


class SaveSubmissionRequest(BaseModel):
    problem_id: int
    code: str
    passed: bool = False


class ProgressResponse(BaseModel):
    solved: int
    streak: int
    submissions: List[SubmissionResponse]


# ========== Hint Schemas ==========


class HintRequest(BaseModel):
    problem_id: int
    code: str
    error: str


# ========== Quest Schemas ==========


class QuestExecuteRequest(BaseModel):
    problem_id: int
    step: int
    code: str = Field(..., max_length=50000)


class QuestHintRequest(BaseModel):
    problem_id: int
    step: int
    code: str
    error: str


class QuestCreateRequest(BaseModel):
    problem_id: int
    data: dict[str, Any]


class QuestProgressSaveRequest(BaseModel):
    problem_id: int
    step: int
    code: str


class QuestProgressResponse(BaseModel):
    step: int
    code: str
    completed: bool
    created_at: datetime


class QuestReasoningRequest(BaseModel):
    problem_id: int
    step: int
    test_input: str
    expected_output: str
    function_signature: str


class FixMermaidRequest(BaseModel):
    code: str
    error: str


class PersistMermaidFixRequest(BaseModel):
    problem_id: int
    original_code: str
    fixed_code: str


# ========== Manim Schemas ==========


class ManimGenerateRequest(BaseModel):
    problem_id: int
    step_number: Optional[int] = None  # None = generate all steps
    video_type: Optional[str] = None  # None = both types; "visualization" or "calculation"


class ManimAnimationResponse(BaseModel):
    id: int
    problem_id: int
    step_number: int
    video_type: str = "calculation"
    status: str
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    render_time_ms: Optional[int] = None
    created_at: datetime


class ManimStatusResponse(BaseModel):
    problem_id: int
    animations: List[ManimAnimationResponse]
    total_steps: int
    completed_count: int
    rendering_count: int
    error_count: int
