"""Add lockout bookkeeping for local application users.

Revision ID: 20260917_002
Revises: 20260917_001
"""

from alembic import op

revision = "20260917_002"
down_revision = "20260917_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE app_users ADD COLUMN failed_login_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE app_users ADD COLUMN locked_until_utc TEXT")


def downgrade() -> None:
    # SQLite cannot drop columns portably; rollback restores from the pre-migration backup.
    raise NotImplementedError("Restaurar el backup previo a 20260917_002 para revertir.")
