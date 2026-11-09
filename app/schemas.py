"""Pydantic schemas exposed by the read-only B02 API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SourceResponse(BaseModel):
    source_id: int
    code: str
    name: str


class CaptureResponse(BaseModel):
    capture_run_id: int
    source_id: int
    started_at_utc: str | None
    finished_at_utc: str | None
    manifest_path: str
    raw_file_count: int | None


class TrendResponse(BaseModel):
    source_code: str
    site_id: str
    scope: str
    category_id: str | None
    keyword: str
    position: int
    previous_position: int | None = None
    change: str
    captured_at_utc: str
    raw_source_id: int


class ProductResponse(BaseModel):
    source_code: str
    product_id: str
    name: str | None
    brand: str | None
    domain_id: str | None = None
    ranking_category_id: str | None
    highlight_position: int | None
    captured_at_utc: str
    raw_source_id: int


class ProductDetailResponse(ProductResponse):
    offer_count: int
    lowest_price: float | None
    highest_price: float | None
    visit_points: int
    related_keyword_count: int
    snapshots: list["ProductSnapshotResponse"] = []
    offers: list["OfferResponse"] = []
    visits: list["VisitResponse"] = []
    keywords: list["KeywordResponse"] = []
    categories: list["ProductCategoryResponse"] = []


class ProductSnapshotResponse(BaseModel):
    name: str | None
    brand: str | None
    domain_id: str | None
    ranking_category_id: str | None
    highlight_position: int | None
    captured_at_utc: str
    raw_source_id: int


class OfferResponse(BaseModel):
    item_id: str
    seller_id: str | None
    category_id: str | None
    price: float | None
    original_price: float | None
    currency_id: str | None
    condition: str | None
    free_shipping: bool
    captured_at_utc: str
    raw_source_id: int


class VisitResponse(BaseModel):
    item_id: str
    date_utc: str
    visits: int
    window_days: int | None
    captured_at_utc: str
    raw_source_id: int


class KeywordResponse(BaseModel):
    keyword: str
    scope: str
    category_id: str | None
    trend_position: int | None
    relevance_position: int
    captured_at_utc: str
    raw_source_id: int


class ProductCategoryResponse(BaseModel):
    ranking_category_id: str | None
    offer_category_id: str | None
    offer_category_name: str | None
    path: list[object]
    offer_count: int
    captured_at_utc: str
    raw_source_id: int


class CategoryResponse(BaseModel):
    category_id: str
    name: str | None


class RawSourceResponse(BaseModel):
    raw_source_id: int
    source_code: str
    endpoint: str | None
    captured_at_utc: str
    http_status: int | None
    sha256: str
    relative_path: str


class TrendHistoryResponse(BaseModel):
    items: list[TrendResponse]


class PageMeta(BaseModel):
    next_cursor: int | None


class SourcesListResponse(BaseModel):
    items: list[SourceResponse]


class CapturesListResponse(BaseModel):
    items: list[CaptureResponse]
    page: PageMeta


class TrendsListResponse(BaseModel):
    items: list[TrendResponse]
    page: PageMeta


class ProductsListResponse(BaseModel):
    items: list[ProductResponse]
    page: PageMeta


class CategoriesListResponse(BaseModel):
    items: list[CategoryResponse]


class JobResponse(BaseModel):
    job_id: str
    job_type: str
    source_id: int | None
    site_id: str | None
    status: str
    step_code: str | None
    progress_current: int
    progress_total: int | None
    attempt_count: int
    created_at_utc: str
    started_at_utc: str | None
    finished_at_utc: str | None
    error_code: str | None
    error_message: str | None

class JobCreateRequest(BaseModel):
    job_type: str = Field(pattern="^(capture|ingest|report|render_pdf)$")
    source_code: str = Field(min_length=1, max_length=64)
    site_id: str = Field(default="MLC", min_length=1, max_length=16)
    scope: str = Field(default="full", pattern="^(full|daily_highlights|daily_catalog|sellers|keyword_supply|expanded_visits|shipping)$")

class JobEventResponse(BaseModel):
    sequence: int; event_code: str; level: str; step_code: str | None; message: str
    progress_current: int | None; progress_total: int | None; occurred_at_utc: str

class JobsListResponse(BaseModel):
    items: list[JobResponse]

class JobEventsResponse(BaseModel):
    items: list[JobEventResponse]

class ReportContentResponse(BaseModel):
    filename: str
    content: str

class ReportResponse(BaseModel):
    filename: str
    size_bytes: int
    modified_at_utc: str

class ReportsListResponse(BaseModel):
    items: list[ReportResponse]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=12, max_length=256)


class UserResponse(BaseModel):
    email: str
    display_name: str
    role: str
    csrf_token: str | None = None


class DashboardSummaryResponse(BaseModel):
    latest_capture_at_utc: str | None
    capture_count: int
    raw_file_count: int
    trend_count: int
    product_count: int
    covered_categories: int
    freshness_at_utc: str | None
    recent_jobs: list[JobResponse]
