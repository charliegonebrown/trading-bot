"""Initial tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id",              sa.Integer(), primary_key=True, index=True),
        sa.Column("balance",         sa.Float(),   nullable=True, server_default="100000.0"),
        sa.Column("initial_balance", sa.Float(),   nullable=True, server_default="100000.0"),
        sa.Column("total_pnl",       sa.Float(),   nullable=True, server_default="0.0"),
        sa.Column("total_trades",    sa.Integer(), nullable=True, server_default="0"),
        sa.Column("winning_trades",  sa.Integer(), nullable=True, server_default="0"),
    )

    trade_status = sa.Enum(
        "open", "closed_tp", "closed_sl", "closed",
        name="tradestatus"
    )

    op.create_table(
        "trades",
        sa.Column("id",          sa.Integer(),               primary_key=True, index=True),
        sa.Column("symbol",      sa.String(),                nullable=True),
        sa.Column("market_type", sa.String(),                nullable=True),
        sa.Column("side",        sa.String(),                nullable=True),
        sa.Column("entry_price", sa.Float(),                 nullable=True),
        sa.Column("exit_price",  sa.Float(),                 nullable=True),
        sa.Column("quantity",    sa.Float(),                 nullable=True),
        sa.Column("notional",    sa.Float(),                 nullable=True),
        sa.Column("take_profit", sa.Float(),                 nullable=True),
        sa.Column("stop_loss",   sa.Float(),                 nullable=True),
        sa.Column("pnl",         sa.Float(),                 nullable=True),
        sa.Column("status",      trade_status,               nullable=True, server_default="open"),
        sa.Column("strategy",    sa.String(),                nullable=True),
        sa.Column("reason",      sa.String(),                nullable=True),
        sa.Column("opened_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at",   sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "bot_settings",
        sa.Column("id",                 sa.Integer(), primary_key=True, index=True),
        sa.Column("is_running",         sa.Boolean(), nullable=True,  server_default="false"),
        sa.Column("strategy",           sa.String(),  nullable=True,  server_default="hybrid"),
        sa.Column("max_risk_per_trade", sa.Float(),   nullable=True,  server_default="2.0"),
        sa.Column("min_ai_confidence",  sa.Float(),   nullable=True,  server_default="0.7"),
    )


def downgrade() -> None:
    op.drop_table("bot_settings")
    op.drop_table("trades")
    op.drop_table("portfolios")
    # Drop the enum type (PostgreSQL-specific — safe to ignore on SQLite)
    try:
        sa.Enum(name="tradestatus").drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass
