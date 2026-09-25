"""HTTP request and response models."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    workspace_name: str = Field(min_length=2, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    slug: str
    created_at: datetime


class AssistantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    role: str = Field(min_length=2, max_length=160)
    department: str = Field(min_length=2, max_length=120)
    role_template_id: str = Field(min_length=2, max_length=80)
    status: Literal["active", "draft"] = "draft"
    access_level: Literal["admins_only", "workspace"] = "admins_only"
    capabilities: list[str] = Field(default_factory=list, max_length=12)
    instructions: str | None = Field(default=None, max_length=8000)


class AssistantResponse(AssistantCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    created_at: datetime
    updated_at: datetime


class AssistantUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=120)
    role_template_id: str = Field(min_length=2, max_length=80)
    status: Literal["active", "draft"]
    access_level: Literal["admins_only", "workspace"]
    instructions: str | None = Field(default=None, max_length=8000)


class CatalogDepartment(BaseModel):
    id: str
    name: str


class CatalogRole(BaseModel):
    id: str
    department_id: str
    name: str
    description: str
    capabilities: list[str]
    risk_tier: Literal["standard", "elevated", "restricted"]
    oversight: str
    limitations: list[str]


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    assistant_id: str
    file_name: str
    content_type: str
    size_bytes: int
    status: str
    stage: str
    progress: int
    chunk_count: int
    processed_at: datetime | None
    feedback: str
    created_at: datetime


class MemberAdd(BaseModel):
    email: EmailStr
    role: Literal["member", "admin"] = "member"


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime


class WorkTaskCreate(BaseModel):
    assistant_id: str
    title: str = Field(min_length=3, max_length=180)
    instructions: str = Field(min_length=10, max_length=12000)
    expected_output: str | None = Field(default=None, max_length=4000)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    due_at: datetime | None = None


class WorkTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    assistant_id: str
    created_by: str
    supervisor_id: str
    title: str
    instructions: str
    expected_output: str | None
    priority: str
    due_at: datetime | None
    status: str
    stage: str
    progress: int
    risk_level: str
    result: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=12000)


class TaskMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    author_type: str
    author_user_id: str | None
    author_name: str
    kind: str
    content: str
    created_at: datetime


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=160)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=12000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime

