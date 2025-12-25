"""
Pydantic schemas for API requests and responses.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
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


# ========== Problem Schemas ==========

class ProblemSummary(BaseModel):
    id: int
    title: str
    category: str
    difficulty: str


class ProblemListResponse(BaseModel):
    problems: List[ProblemSummary]
    total: int


# ========== Execution Schemas ==========

class ExecuteRequest(BaseModel):
    problem_id: int
    code: str


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
    code: str


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
