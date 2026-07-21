"""Pydantic v2 schemas matching ORM models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Team ----------
class TeamBase(BaseModel):
    name: str


class TeamRead(TeamBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Provider ----------
class ProviderCreate(BaseModel):
    type: str  # aws|gcp|digitalocean|vultr|selfhosted|baremetal
    name: str
    credentials_ref: Optional[str] = None


class ProviderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_id: int
    type: str
    name: str
    credentials_ref: Optional[str]


# ---------- Instance ----------
class InstanceCreate(BaseModel):
    team_id: int
    provider_id: Optional[int] = None
    name: str
    host: str
    port: int = 22
    ssh_user: str = "root"
    ssh_key_ref: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_id: int
    provider_id: Optional[int]
    name: str
    host: str
    port: int
    ssh_user: str
    status: str
    tags: list[str]
    metadata: dict[str, Any] = Field(alias="metadata_")
    created_at: datetime
    last_checked_at: Optional[datetime]


class InstanceTestResult(BaseModel):
    instance_id: int
    ok: bool
    detail: str = ""


# ---------- Command ----------
class CommandCreate(BaseModel):
    instance_ids: list[int]
    command: str


class CommandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    instance_ids: list[int]
    command: str
    status: str
    outputs: dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime]


# ---------- Terminal ----------
class TerminalCmdIn(BaseModel):
    type: str  # "cmd" | "resize"
    data: str = ""
    cols: int = 80
    rows: int = 24


# ---------- Agent ----------
class AgentRunIn(BaseModel):
    goal: str


class AgentJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    goal: str
    plan: list[Any]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]


class AgentActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    tool: str
    params: dict[str, Any]
    result: dict[str, Any]
    requires_approval: bool
    approved_by: Optional[int]
    created_at: datetime


class AgentApprovalIn(BaseModel):
    approve: bool


# ---------- Deploy ----------
class DeployCreate(BaseModel):
    repo: str
    ref: str = "main"
    instance_ids: list[int]


class DeployRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    repo: str
    ref: str
    instance_ids: list[int]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]


# ---------- Monitoring ----------
class MetricPoint(BaseModel):
    ts: datetime
    value: float


class MetricsOut(BaseModel):
    cpu: list[MetricPoint] = Field(default_factory=list)
    ram: list[MetricPoint] = Field(default_factory=list)
    disk: list[MetricPoint] = Field(default_factory=list)


# ---------- Conversations ----------
class ConversationCreate(BaseModel):
    title: str = "New Chat"
    model: str = "default"


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    title: str
    model: str
    created_at: datetime
    updated_at: datetime


class ConversationMessageCreate(BaseModel):
    role: str
    content: str


class ConversationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    role: str
    content: str
    metadata: dict[str, Any] = Field(alias="metadata_")
    created_at: datetime


# ---------- Token Usage ----------
class TokenUsageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    created_at: datetime


class UsageSummary(BaseModel):
    total_input: int = 0
    total_output: int = 0
    total_cost: float = 0.0
    by_model: dict[str, dict[str, Any]] = {}


# ---------- Alerts ----------
class AlertCreate(BaseModel):
    type: str  # whatsapp|telegram|slack|email
    target: str
    events: list[str] = Field(default_factory=list)


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    type: str
    target: str
    events: list[str]
    is_active: bool
    created_at: datetime
