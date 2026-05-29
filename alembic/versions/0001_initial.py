"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_scope_id", "jobs", ["scope_id"], unique=True)

    # scoped_tasks (without FK to task_launches yet)
    op.create_table(
        "scoped_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("spec_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("depends_on", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_launch_id", sa.UUID(), nullable=True),
        sa.Column("latest_launch_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("spec_id", "job_id", "id"),
        sa.CheckConstraint(
            """
            CASE
                WHEN status = 'NEW'    THEN current_launch_id IS NULL AND latest_launch_id IS NULL
                WHEN status = 'PENDING'     THEN current_launch_id IS NOT NULL AND latest_launch_id IS NULL
                WHEN status = 'IN_PROGRESS' THEN current_launch_id IS NOT NULL AND latest_launch_id IS NULL
                WHEN status = 'SUCCESS'     THEN current_launch_id IS NULL AND latest_launch_id IS NOT NULL
                WHEN status = 'FAILED'      THEN current_launch_id IS NULL AND latest_launch_id IS NOT NULL
                WHEN status = 'SKIPPED'     THEN current_launch_id IS NULL AND latest_launch_id IS NOT NULL
                ELSE false
            END
            """,
            name="scoped_tasks_status_check",
        ),
    )
    op.create_index("ix_scoped_tasks_spec_id", "scoped_tasks", ["spec_id"])
    op.create_index("ix_scoped_tasks_job_id", "scoped_tasks", ["job_id"])
    op.create_index("ix_scoped_tasks_status", "scoped_tasks", ["status"])
    op.create_index("ix_scoped_tasks_current_launch_id", "scoped_tasks", ["current_launch_id"])
    op.create_index("ix_scoped_tasks_latest_launch_id", "scoped_tasks", ["latest_launch_id"])

    # task_launches
    op.create_table(
        "task_launches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("scheduled_by", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("is_aborted", sa.Boolean(), nullable=True),
        sa.Column("skipped_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["scoped_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            """
            CASE
                WHEN status = 'PENDING'     THEN started_at IS NULL AND finished_at IS NULL AND failed_at IS NULL AND is_aborted IS NULL AND skipped_at IS NULL
                WHEN status = 'IN_PROGRESS' THEN started_at IS NOT NULL AND finished_at IS NULL AND failed_at IS NULL AND is_aborted IS NULL AND skipped_at IS NULL
                WHEN status = 'FINISHED'    THEN started_at IS NOT NULL AND finished_at IS NOT NULL AND failed_at IS NULL AND is_aborted IS NULL AND skipped_at IS NULL
                WHEN status = 'FAILED'      THEN started_at IS NOT NULL AND finished_at IS NULL AND failed_at IS NOT NULL AND is_aborted IS NOT NULL AND skipped_at IS NULL
                WHEN status = 'SKIPPED'     THEN started_at IS NOT NULL AND finished_at IS NULL AND failed_at IS NULL AND is_aborted IS NULL AND skipped_at IS NOT NULL
                ELSE false
            END
            """,
            name="task_launches_status_check",
        ),
    )
    op.create_index("ix_task_launches_task_id", "task_launches", ["task_id"])
    op.create_index("ix_task_launches_status", "task_launches", ["status"])

    # journal
    op.create_table(
        "journal",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("launch_id", sa.UUID(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["launch_id"], ["task_launches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_journal_launch_id", "journal", ["launch_id"])
    op.create_index("ix_journal_level", "journal", ["level"])
    op.create_index("ix_journal_type", "journal", ["type"])

    # log_files
    op.create_table(
        "log_files",
        sa.Column("log_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("extension", sa.String(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["log_id"], ["journal.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("log_id"),
    )

    # Now add FKs from scoped_tasks to task_launches (use_alter pattern)
    op.create_foreign_key(
        "fk_scoped_tasks_current_launch",
        "scoped_tasks", "task_launches",
        ["current_launch_id"], ["id"],
        use_alter=True,
    )
    op.create_foreign_key(
        "fk_scoped_tasks_latest_launch",
        "scoped_tasks", "task_launches",
        ["latest_launch_id"], ["id"],
        use_alter=True,
    )


def downgrade() -> None:
    op.drop_constraint("fk_scoped_tasks_current_launch", "scoped_tasks", type_="foreignkey")
    op.drop_constraint("fk_scoped_tasks_latest_launch", "scoped_tasks", type_="foreignkey")
    op.drop_table("log_files")
    op.drop_table("journal")
    op.drop_table("task_launches")
    op.drop_table("scoped_tasks")
    op.drop_table("jobs")
