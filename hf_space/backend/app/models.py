from pydantic import BaseModel, Field


class ChargeRequest(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    customer_id: str = Field(..., min_length=1)
    description: str | None = None
    max_retries: int = Field(3, ge=0, le=10)


class ChargeResponse(BaseModel):
    id: str
    amount: float
    currency: str
    customer_id: str
    description: str | None
    status: str
    max_retries: int
    retry_count: int
    next_retry_at: str | None
    created_at: str
    updated_at: str


class AttemptSummary(BaseModel):
    attempt_number: int
    status: str
    error_code: str | None
    error_message: str | None
    attempted_at: str
    duration_ms: int


class ChargeStatusResponse(ChargeResponse):
    attempts: list[AttemptSummary]


class StatsResponse(BaseModel):
    total_charges: int
    success_count: int
    failed_count: int
    pending_count: int
    processing_count: int
    success_rate: float
    avg_attempts_to_success: float
