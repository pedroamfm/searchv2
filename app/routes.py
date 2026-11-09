"""Read-only API routes backed exclusively by repositories."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import FileResponse

from app.database import database_connection
from app.dependencies import CurrentUser, SettingsDependency
from app.errors import ApiError
from app.auth import require_csrf
from app.jobs import JobService
from app.repositories import (
    CaptureRepository,
    JobRepository,
    ProductRepository,
    RawSourceRepository,
    SourceRepository,
    TrendRepository,
)
from app.schemas import (
    CaptureResponse,
    CategoriesListResponse,
    CategoryResponse,
    CapturesListResponse,
    DashboardSummaryResponse,
    JobResponse,
    JobCreateRequest,
    JobEventResponse,
    JobEventsResponse,
    JobsListResponse,
    PageMeta,
    ProductDetailResponse,
    ProductResponse,
    ProductsListResponse,
    RawSourceResponse,
    ReportContentResponse,
    ReportResponse,
    ReportsListResponse,
    SourceResponse,
    SourcesListResponse,
    TrendResponse,
    TrendHistoryResponse,
    TrendsListResponse,
)

router = APIRouter(prefix="/api/v1", tags=["data"])
PageSize = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[int, Query(ge=0)]
SourceCode = Annotated[str | None, Query(min_length=1, max_length=64)]
Scope = Annotated[str | None, Query(pattern="^(general|category)$")]
CategoryId = Annotated[str | None, Query(min_length=3, max_length=32)]
Search = Annotated[str | None, Query(min_length=1, max_length=120)]
CapturedAt = Annotated[str | None, Query(min_length=10, max_length=35)]


def _rows(items: list[Any], mapper: Callable[[dict[str, Any]], Any]) -> list[Any]:
    return [mapper(dict(row)) for row in items]


@router.get("/sources", response_model=SourcesListResponse)
def list_sources(settings: SettingsDependency, _: CurrentUser) -> SourcesListResponse:
    with database_connection(settings.database_path) as connection:
        items = _rows(SourceRepository().list(connection), lambda row: SourceResponse.model_validate(row))
    return SourcesListResponse(items=items)


@router.get("/captures", response_model=CapturesListResponse)
def list_captures(
    settings: SettingsDependency, _: CurrentUser, cursor: Cursor = 0, limit: PageSize = 50
) -> CapturesListResponse:
    with database_connection(settings.database_path) as connection:
        page = CaptureRepository().list(connection, cursor=cursor, limit=limit)
    return CapturesListResponse(
        items=_rows(page.rows, lambda row: CaptureResponse.model_validate(row)),
        page=PageMeta(next_cursor=page.next_cursor),
    )


@router.get("/trends", response_model=TrendsListResponse)
def list_trends(
    settings: SettingsDependency,
    _: CurrentUser,
    cursor: Cursor = 0,
    limit: PageSize = 50,
    source_code: SourceCode = None,
    scope: Scope = None,
    category_id: CategoryId = None,
    keyword: Search = None,
    captured_from: CapturedAt = None,
    captured_to: CapturedAt = None,
) -> TrendsListResponse:
    with database_connection(settings.database_path) as connection:
        page = TrendRepository().list(
            connection, cursor=cursor, limit=limit, source_code=source_code, scope=scope,
            category_id=category_id, keyword=keyword, captured_from=captured_from, captured_to=captured_to,
        )
    return TrendsListResponse(
        items=_rows(page.rows, lambda row: TrendResponse.model_validate(row)),
        page=PageMeta(next_cursor=page.next_cursor),
    )


@router.get("/trends/history", response_model=TrendHistoryResponse)
def trend_history(
    settings: SettingsDependency,
    _: CurrentUser,
    source_code: Annotated[str, Query(min_length=1, max_length=64)],
    site_id: Annotated[str, Query(min_length=1, max_length=16)],
    scope: Annotated[str, Query(pattern="^(general|category)$")],
    keyword: Annotated[str, Query(min_length=1, max_length=120)],
    category_id: CategoryId = None,
) -> TrendHistoryResponse:
    if scope == "category" and category_id is None:
        raise ApiError(422, "validation_error", "category_id es obligatorio para tendencias por categoría.")
    with database_connection(settings.database_path) as connection:
        rows = TrendRepository().history(
            connection, source_code=source_code, site_id=site_id, scope=scope,
            category_id=category_id, keyword=keyword,
        )
    return TrendHistoryResponse(items=_rows(rows, lambda row: TrendResponse.model_validate(row)))


@router.get("/categories", response_model=CategoriesListResponse)
def list_categories(settings: SettingsDependency, _: CurrentUser) -> CategoriesListResponse:
    with database_connection(settings.database_path) as connection:
        rows = TrendRepository().categories(connection)
    return CategoriesListResponse(items=_rows(rows, lambda row: CategoryResponse.model_validate(row)))


@router.get("/products", response_model=ProductsListResponse)
def list_products(
    settings: SettingsDependency,
    _: CurrentUser,
    cursor: Cursor = 0,
    limit: PageSize = 50,
    source_code: SourceCode = None,
    category_id: CategoryId = None,
    query: Search = None,
    captured_from: CapturedAt = None,
    captured_to: CapturedAt = None,
) -> ProductsListResponse:
    with database_connection(settings.database_path) as connection:
        page = ProductRepository().list(
            connection, cursor=cursor, limit=limit, source_code=source_code,
            category_id=category_id, query=query, captured_from=captured_from, captured_to=captured_to,
        )
    return ProductsListResponse(
        items=_rows(page.rows, lambda row: ProductResponse.model_validate(row)),
        page=PageMeta(next_cursor=page.next_cursor),
    )


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
def get_product(settings: SettingsDependency, _: CurrentUser, product_id: str) -> ProductDetailResponse:
    with database_connection(settings.database_path) as connection:
        row = ProductRepository().detail(connection, product_id)
    if row is None:
        raise ApiError(404, "resource_not_found", "No existe el producto solicitado.")
    return ProductDetailResponse.model_validate(row)


@router.get("/raw-sources/{raw_source_id}", response_model=RawSourceResponse)
def get_raw_source(settings: SettingsDependency, _: CurrentUser, raw_source_id: int) -> RawSourceResponse:
    with database_connection(settings.database_path) as connection:
        row = RawSourceRepository().get(connection, raw_source_id)
    if row is None:
        raise ApiError(404, "resource_not_found", "No existe la evidencia RAW solicitada.")
    return RawSourceResponse.model_validate(dict(row))


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(settings: SettingsDependency, _: CurrentUser, job_id: str) -> JobResponse:
    with database_connection(settings.database_path) as connection:
        row = JobRepository().get(connection, job_id)
    if row is None:
        raise ApiError(404, "resource_not_found", "No existe el trabajo solicitado.")
    return JobResponse.model_validate(dict(row))

@router.get("/jobs", response_model=JobsListResponse)
def list_jobs(settings: SettingsDependency, _: CurrentUser) -> JobsListResponse:
    with database_connection(settings.database_path) as connection:
        return JobsListResponse(items=[JobResponse.model_validate(dict(row)) for row in JobRepository().list(connection)])

@router.get("/jobs/{job_id}/events", response_model=JobEventsResponse)
def job_events(settings: SettingsDependency, _: CurrentUser, job_id: str) -> JobEventsResponse:
    with database_connection(settings.database_path) as connection:
        if JobRepository().get(connection, job_id) is None: raise ApiError(404, "resource_not_found", "No existe el trabajo solicitado.")
        return JobEventsResponse(items=[JobEventResponse.model_validate(dict(row)) for row in JobRepository().events(connection, job_id)])

@router.post("/jobs", response_model=JobResponse, status_code=202)
def create_job(payload: JobCreateRequest, request: Request, settings: SettingsDependency, user: CurrentUser, idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)], csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None) -> JobResponse:
    if user["role"] != "admin": raise ApiError(403, "forbidden", "Sólo un administrador puede iniciar trabajos.")
    require_csrf(user, csrf_token)  # type: ignore[arg-type]
    with database_connection(settings.database_path, read_only=False) as connection:
        job = JobService().enqueue(connection, job_type=payload.job_type, source_code=payload.source_code, site_id=payload.site_id, scope=payload.scope, actor_user_id=int(user["user_id"]), idempotency_key=idempotency_key)
    return JobResponse.model_validate(dict(job))

@router.get("/reports/latest", response_model=ReportContentResponse)
def latest_report(settings: SettingsDependency, _: CurrentUser) -> ReportContentResponse:
    reports = sorted(settings.reports_root.glob("product_radar_MLC_*_32_categorias_online.md"))
    if not reports:
        raise ApiError(404, "resource_not_found", "Aún no hay un informe completo de 32 categorías.")
    report = reports[-1]
    return ReportContentResponse(filename=report.name, content=report.read_text(encoding="utf-8"))

@router.get("/reports", response_model=ReportsListResponse)
def list_reports(settings: SettingsDependency, _: CurrentUser) -> ReportsListResponse:
    files = sorted(settings.reports_root.glob("product_radar_MLC_*"), key=lambda path: path.stat().st_mtime, reverse=True)
    return ReportsListResponse(items=[ReportResponse(filename=path.name, size_bytes=path.stat().st_size, modified_at_utc=datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()) for path in files if path.is_file() and path.suffix in {".md", ".pdf"}])

@router.get("/reports/{filename}")
def open_report(settings: SettingsDependency, _: CurrentUser, filename: str) -> FileResponse:
    if Path(filename).name != filename or not filename.startswith("product_radar_MLC_") or Path(filename).suffix not in {".md", ".pdf"}:
        raise ApiError(404, "resource_not_found", "No existe el informe solicitado.")
    report = settings.reports_root / filename
    if not report.is_file():
        raise ApiError(404, "resource_not_found", "No existe el informe solicitado.")
    return FileResponse(report, media_type="application/pdf" if report.suffix == ".pdf" else "text/markdown; charset=utf-8", content_disposition_type="inline")


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(settings: SettingsDependency, _: CurrentUser) -> DashboardSummaryResponse:
    with database_connection(settings.database_path) as connection:
        latest = connection.execute("SELECT finished_at_utc, raw_file_count FROM capture_runs ORDER BY finished_at_utc DESC LIMIT 1").fetchone()
        counts = connection.execute("SELECT (SELECT COUNT(*) FROM capture_runs), (SELECT COUNT(*) FROM raw_sources), (SELECT COUNT(*) FROM trend_snapshots), (SELECT COUNT(*) FROM product_snapshots), (SELECT COUNT(DISTINCT category_id) FROM trend_snapshots WHERE category_id != ''), (SELECT MAX(captured_at_utc) FROM raw_sources)").fetchone()
        jobs = connection.execute("SELECT * FROM jobs ORDER BY created_at_utc DESC LIMIT 5").fetchall()
    return DashboardSummaryResponse(latest_capture_at_utc=latest["finished_at_utc"] if latest else None, capture_count=counts[0], raw_file_count=counts[1], trend_count=counts[2], product_count=counts[3], covered_categories=counts[4], freshness_at_utc=counts[5], recent_jobs=[JobResponse.model_validate(dict(job)) for job in jobs])
    RawSourceResponse,
