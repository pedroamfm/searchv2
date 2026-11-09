"""Persistent SQLite queue with leases and append-only events."""
from __future__ import annotations
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from app.errors import ApiError

def now() -> str: return datetime.now(UTC).isoformat()

class JobService:
    def event(self, c: sqlite3.Connection, job_id: str, code: str, level: str, step: str | None, message: str) -> None:
        sequence = c.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM job_events WHERE job_id=?", (job_id,)).fetchone()[0]
        c.execute("INSERT INTO job_events (job_id,sequence,event_code,level,step_code,message,occurred_at_utc) VALUES (?,?,?,?,?,?,?)", (job_id, sequence, code, level, step, message, now()))

    def enqueue(self, c: sqlite3.Connection, *, job_type: str, source_code: str, site_id: str, scope: str, actor_user_id: int, idempotency_key: str) -> sqlite3.Row:
        source = c.execute("SELECT source_id FROM sources WHERE code=?", (source_code,)).fetchone()
        if source is None: raise ApiError(422, "source_disabled", "La fuente solicitada no está disponible.")
        payload = json.dumps({"source_code": source_code, "site_id": site_id, "scope": scope}, sort_keys=True)
        old = c.execute("SELECT * FROM jobs WHERE requested_by_user_id=? AND idempotency_key=?", (actor_user_id, idempotency_key)).fetchone()
        if old:
            if old["job_type"] != job_type or old["request_payload_json"] != payload: raise ApiError(409, "idempotency_conflict", "La clave de idempotencia ya se usó con otra solicitud.")
            return old
        if job_type == "capture":
            active = c.execute("SELECT job_id FROM jobs WHERE source_id=? AND site_id=? AND job_type='capture' AND status IN ('queued','running')", (source[0], site_id)).fetchone()
            if active: raise ApiError(409, "active_capture_exists", "Ya existe una captura activa para la fuente y sitio.", {"job_id": active[0]})
        job_id = str(uuid4())
        c.execute("INSERT INTO jobs (job_id,job_type,source_id,site_id,status,idempotency_key,requested_by_user_id,request_payload_json,created_at_utc) VALUES (?,?,?,?, 'queued',?,?,?,?)", (job_id, job_type, source[0], site_id, idempotency_key, actor_user_id, payload, now()))
        self.event(c, job_id, "job.queued", "info", "job.validating", "Trabajo encolado.")
        return c.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()

    def recover(self, c: sqlite3.Connection) -> None:
        for job in c.execute("SELECT * FROM jobs WHERE status='running' AND lease_expires_at_utc < ?", (now(),)).fetchall():
            if job["attempt_count"] >= job["max_attempts"]:
                c.execute("UPDATE jobs SET status='failed',started_at_utc=NULL,finished_at_utc=?,error_code='job_attempts_exhausted',error_message='Se agotaron los intentos.' WHERE job_id=?", (now(), job["job_id"]))
                self.event(c, job["job_id"], "job.failed", "error", job["step_code"], "Se agotaron los intentos.")
            else:
                c.execute("UPDATE jobs SET status='queued',lease_owner=NULL,lease_expires_at_utc=NULL WHERE job_id=?", (job["job_id"],))
                self.event(c, job["job_id"], "job.retry_scheduled", "warning", job["step_code"], "Lease vencido; trabajo reencolado.")

    def claim(self, c: sqlite3.Connection, worker_id: str, lease_seconds: int = 60) -> sqlite3.Row | None:
        if c.in_transaction: c.commit()
        c.execute("BEGIN IMMEDIATE"); self.recover(c)
        job = c.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at_utc,job_id LIMIT 1").fetchone()
        if not job: c.commit(); return None
        expiry = (datetime.now(UTC) + timedelta(seconds=lease_seconds)).isoformat()
        c.execute("UPDATE jobs SET status='running',started_at_utc=COALESCE(started_at_utc,?),lease_owner=?,lease_expires_at_utc=?,attempt_count=attempt_count+1 WHERE job_id=?", (now(), worker_id, expiry, job["job_id"]))
        self.event(c, job["job_id"], "job.claimed", "info", "job.preparing", "Worker adquirió el lease."); c.commit()
        return c.execute("SELECT * FROM jobs WHERE job_id=?", (job["job_id"],)).fetchone()

    def complete(self, c: sqlite3.Connection, job_id: str, worker_id: str, error: bool = False) -> None:
        job = c.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if not job or job["status"] != "running" or job["lease_owner"] != worker_id: return
        if error:
            c.execute("UPDATE jobs SET status='failed',started_at_utc=NULL,finished_at_utc=?,error_code='internal_error',error_message='El trabajo no pudo completarse.',lease_owner=NULL,lease_expires_at_utc=NULL WHERE job_id=?", (now(), job_id)); self.event(c, job_id, "job.failed", "error", job["step_code"], "El trabajo no pudo completarse.")
        else:
            c.execute("UPDATE jobs SET status='succeeded',started_at_utc=NULL,finished_at_utc=?,step_code='job.finalizing',lease_owner=NULL,lease_expires_at_utc=NULL WHERE job_id=?", (now(), job_id)); self.event(c, job_id, "job.succeeded", "info", "job.finalizing", "Trabajo completado.")
