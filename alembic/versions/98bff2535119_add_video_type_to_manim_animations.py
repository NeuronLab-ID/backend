"""add video_type to manim_animations

Revision ID: 98bff2535119
Revises: 767f6273cdf3
Create Date: 2026-02-21 15:36:00.771836

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "98bff2535119"
down_revision: Union[str, Sequence[str], None] = "767f6273cdf3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("manim_animations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("video_type", sa.String(20), nullable=False, server_default="calculation"))
        batch_op.create_unique_constraint("uq_manim_problem_step_type", ["problem_id", "step_number", "video_type"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("manim_animations", schema=None) as batch_op:
        batch_op.drop_constraint("uq_manim_problem_step_type", type_="unique")
        batch_op.drop_column("video_type")
