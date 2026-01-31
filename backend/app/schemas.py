from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DatasetCreateResponse(BaseModel):
    dataset_id: str
    share_id: str
    status: str = "ready"
    error: str | None = None
    analysis: dict[str, Any]


class DatasetGetResponse(BaseModel):
    dataset_id: str
    share_id: str
    status: str = "ready"
    error: str | None = None
    analysis: dict[str, Any]

class DatasetListItem(BaseModel):
    dataset_id: str
    share_id: str
    original_filename: str
    created_at: str
    status: str | None = None
    rows: int | None = None
    cols: int | None = None


class DatasetListResponse(BaseModel):
    items: list[DatasetListItem]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatAnswer(BaseModel):
    type: Literal["text", "table", "chart"] = "text"
    text: str
    table: dict[str, Any] | None = None
    chart: dict[str, Any] | None = None
    citations: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    dataset_id: str
    answer: ChatAnswer


class ChatMessageItem(BaseModel):
    id: int
    role: Literal["user", "ai"]
    type: Literal["text", "table", "chart", "meta"] = "text"
    text: str = ""
    table: dict[str, Any] | None = None
    chart: dict[str, Any] | None = None
    created_at: str


class ChatHistoryResponse(BaseModel):
    dataset_id: str
    messages: list[ChatMessageItem]


class AuthRequestCodeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class AuthRequestCodeResponse(BaseModel):
    ok: bool = True
    dev_code: str | None = None


class AuthVerifyCodeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=4, max_length=12)


class AuthVerifyCodeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class PivotRequest(BaseModel):
    group_by: list[str] = Field(default_factory=list)
    metric: str | None = None
    agg: Literal["sum", "mean", "count", "min", "max"] = "sum"
    date_col: str | None = None
    time_grain: Literal["day", "week", "month"] | None = None
    top_n: int = Field(default=12, ge=1, le=50)
    filters: dict[str, Any] | None = None
    chart_type: Literal["bar", "line", "table"] = "bar"


class PivotResponse(BaseModel):
    type: Literal["text", "table", "chart"] = "chart"
    text: str
    table: dict[str, Any] | None = None
    chart: dict[str, Any] | None = None
    citations: dict[str, Any] | None = None



