"""Initial schema: pad and launch.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pad",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location_name", sa.String(255)),
        sa.Column("country_code", sa.String(8)),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
    )
    op.create_table(
        "launch",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("net", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32)),
        sa.Column("provider", sa.String(255)),
        sa.Column("rocket", sa.String(255)),
        sa.Column("mission_name", sa.String(255)),
        sa.Column("mission_type", sa.String(64)),
        sa.Column("mission_description", sa.Text),
        sa.Column("orbit_name", sa.String(64)),
        sa.Column("orbit_abbrev", sa.String(32)),
        sa.Column("orbit_body", sa.String(64)),
        sa.Column("pad_id", sa.Integer, sa.ForeignKey("pad.id"), nullable=False),
    )
    op.create_index("ix_launch_net", "launch", ["net"])


def downgrade() -> None:
    op.drop_index("ix_launch_net", table_name="launch")
    op.drop_table("launch")
    op.drop_table("pad")
