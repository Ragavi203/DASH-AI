from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DatasetCreateResponse(BaseModel):
    dataset_id: str
    share_id: str
    analysis: dict[str, Any]


class DatasetGetResponse(BaseModel):
    dataset_id: str
    share_id: str
    analysis: dict[str, Any]

class DatasetListItem(BaseModel):
    dataset_id: str
    share_id: str
    original_filename: str
    created_at: str
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



