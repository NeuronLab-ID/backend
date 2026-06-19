"""add manim_render_jobs table

Revision ID: 2b6f8e91c4a7
Revises: 98bff2535119
Create Date: 2026-06-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "2b6f8e91c4a7"
down_revision: str | Sequence[str] | None = "98bff2535119"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ = op.create_table(
        "manim_render_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=True),
        sa.Column("video_type", sa.String(length=20), nullable=True),
        sa.Column("requested_backend", sa.String(length=20), nullable=False),
        sa.Column("resolved_backend", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("container_id", sa.String(length=128), nullable=True),
        sa.Column("animation_id", sa.Integer(), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("logs_tail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_manim_render_jobs_id"), "manim_render_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_manim_render_jobs_job_id"), "manim_render_jobs", ["job_id"], unique=True)
    op.create_index(op.f("ix_manim_render_jobs_user_id"), "manim_render_jobs", ["user_id"], unique=False)
    op.create_index(op.f("ix_manim_render_jobs_problem_id"), "manim_render_jobs", ["problem_id"], unique=False)
    op.create_index(op.f("ix_manim_render_jobs_status"), "manim_render_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_manim_render_jobs_request_hash"), "manim_render_jobs", ["request_hash"], unique=False)
    op.create_index(
        op.f("ix_manim_render_jobs_idempotency_key"), "manim_render_jobs", ["idempotency_key"], unique=False
    )
    op.create_index("ix_manim_render_jobs_status_created", "manim_render_jobs", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_manim_render_jobs_status_created", table_name="manim_render_jobs")
    op.drop_index(op.f("ix_manim_render_jobs_idempotency_key"), table_name="manim_render_jobs")
    op.drop_index(op.f("ix_manim_render_jobs_request_hash"), table_name="manim_render_jobs")
    op.drop_index(op.f("ix_manim_render_jobs_status"), table_name="manim_render_jobs")
    op.drop_index(op.f("ix_manim_render_jobs_problem_id"), table_name="manim_render_jobs")
    op.drop_index(op.f("ix_manim_render_jobs_user_id"), table_name="manim_render_jobs")
    op.drop_index(op.f("ix_manim_render_jobs_job_id"), table_name="manim_render_jobs")
    op.drop_index(op.f("ix_manim_render_jobs_id"), table_name="manim_render_jobs")
    op.drop_table("manim_render_jobs")
