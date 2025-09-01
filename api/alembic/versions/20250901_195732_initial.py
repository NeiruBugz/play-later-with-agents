from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20250901_195732_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # games
    op.create_table(
        "games",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("cover_image_id", sa.String(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("igdb_id", sa.Integer(), nullable=True),
        sa.Column("hltb_id", sa.Integer(), nullable=True),
        sa.Column("steam_app_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_games_title", "games", ["title"])

    # collection_items
    op.create_table(
        "collection_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "game_id",
            sa.String(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("acquisition_type", sa.String(), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "game_id", "platform", name="uq_user_game_platform"
        ),
    )
    op.create_index("ix_collection_user", "collection_items", ["user_id"])
    op.create_index("ix_collection_platform", "collection_items", ["platform"])

    # playthroughs
    op.create_table(
        "playthroughs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "game_id",
            sa.String(),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "collection_id",
            sa.String(),
            sa.ForeignKey("collection_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("play_time_hours", sa.Float(), nullable=True),
        sa.Column("playthrough_type", sa.String(), nullable=True),
        sa.Column("difficulty", sa.String(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_pt_user", "playthroughs", ["user_id"])
    op.create_index("ix_pt_status", "playthroughs", ["status"])
    op.create_index("ix_pt_platform", "playthroughs", ["platform"])

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(), nullable=True),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_sessions_user", "sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_user", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_pt_platform", table_name="playthroughs")
    op.drop_index("ix_pt_status", table_name="playthroughs")
    op.drop_index("ix_pt_user", table_name="playthroughs")
    op.drop_table("playthroughs")

    op.drop_index("ix_collection_platform", table_name="collection_items")
    op.drop_index("ix_collection_user", table_name="collection_items")
    op.drop_table("collection_items")

    op.drop_index("ix_games_title", table_name="games")
    op.drop_table("games")
