"""Add Product Radar operational tables without altering analytical snapshots.

Revision ID: 20260917_001
Revises:
Create Date: 2026-09-17
"""

from __future__ import annotations

from alembic import op

revision = "20260917_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE app_users (
            user_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'viewer')),
            password_hash TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE user_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
            csrf_token_hash TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            expires_at_utc TEXT NOT NULL,
            last_seen_at_utc TEXT NOT NULL,
            revoked_at_utc TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL CHECK(job_type IN ('capture', 'ingest', 'report', 'render_pdf')),
            source_id INTEGER REFERENCES sources(source_id),
            site_id TEXT,
            status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'succeeded', 'failed')),
            step_code TEXT,
            progress_current INTEGER NOT NULL DEFAULT 0 CHECK(progress_current >= 0),
            progress_total INTEGER CHECK(progress_total IS NULL OR progress_total >= 0),
            attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
            max_attempts INTEGER NOT NULL DEFAULT 1 CHECK(max_attempts >= 1),
            lease_owner TEXT,
            lease_expires_at_utc TEXT,
            idempotency_key TEXT,
            requested_by_user_id INTEGER REFERENCES app_users(user_id),
            request_payload_json TEXT NOT NULL DEFAULT '{}',
            result_json TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at_utc TEXT NOT NULL,
            started_at_utc TEXT,
            finished_at_utc TEXT,
            CHECK((status = 'running') = (started_at_utc IS NOT NULL)),
            CHECK((status IN ('succeeded', 'failed')) = (finished_at_utc IS NOT NULL))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE job_events (
            job_event_id INTEGER PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL CHECK(sequence > 0),
            event_code TEXT NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('debug', 'info', 'warning', 'error')),
            step_code TEXT,
            message TEXT NOT NULL,
            progress_current INTEGER CHECK(progress_current IS NULL OR progress_current >= 0),
            progress_total INTEGER CHECK(progress_total IS NULL OR progress_total >= 0),
            metadata_json TEXT NOT NULL DEFAULT '{}',
            occurred_at_utc TEXT NOT NULL,
            UNIQUE(job_id, sequence)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE audit_events (
            audit_event_id INTEGER PRIMARY KEY,
            request_id TEXT,
            actor_user_id INTEGER REFERENCES app_users(user_id),
            action_code TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            outcome TEXT NOT NULL CHECK(outcome IN ('succeeded', 'failed', 'denied')),
            metadata_json TEXT NOT NULL DEFAULT '{}',
            occurred_at_utc TEXT NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX idx_user_sessions_user_expiry ON user_sessions(user_id, expires_at_utc)")
    op.execute("CREATE INDEX idx_jobs_status_created ON jobs(status, created_at_utc)")
    op.execute("CREATE INDEX idx_jobs_source_site_status ON jobs(source_id, site_id, status)")
    op.execute("CREATE INDEX idx_job_events_job_sequence ON job_events(job_id, sequence)")
    op.execute("CREATE INDEX idx_audit_events_request ON audit_events(request_id, occurred_at_utc)")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_active_capture_per_source_site
        ON jobs(source_id, site_id)
        WHERE job_type = 'capture' AND status IN ('queued', 'running')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_active_capture_per_source_site")
    op.execute("DROP INDEX idx_audit_events_request")
    op.execute("DROP INDEX idx_job_events_job_sequence")
    op.execute("DROP INDEX idx_jobs_source_site_status")
    op.execute("DROP INDEX idx_jobs_status_created")
    op.execute("DROP INDEX idx_user_sessions_user_expiry")
    op.execute("DROP TABLE audit_events")
    op.execute("DROP TABLE job_events")
    op.execute("DROP TABLE jobs")
    op.execute("DROP TABLE user_sessions")
    op.execute("DROP TABLE app_users")
