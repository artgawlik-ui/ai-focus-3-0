"""Additive repeatable inbox/leases. Safe downgrade preserves accepted messages."""
from alembic import op
import sqlalchemy as sa
revision='004'
down_revision='003'

def upgrade():
    metadata=sa.MetaData()
    inbox=sa.Table('meta_webhook_inbox',metadata,
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('dedup_key',sa.String(64),unique=True,nullable=False),
        sa.Column('account_id',sa.String(100),nullable=False),
        sa.Column('payload_ciphertext',sa.Text(),nullable=False),
        sa.Column('status',sa.String(20),nullable=False,index=True),
        sa.Column('attempts',sa.Integer(),nullable=False),
        sa.Column('next_attempt_at',sa.String(40),nullable=False),
        sa.Column('lease_until',sa.String(40),nullable=False),
        sa.Column('lease_token',sa.String(36),nullable=False),
        sa.Column('created_at',sa.String(40),nullable=False),
        sa.Column('updated_at',sa.String(40),nullable=False),
        sa.Column('processed_at',sa.String(40),nullable=False),
        sa.Column('last_error',sa.String(40),nullable=False),
        sa.Column('dead_letter',sa.Integer(),nullable=False))
    refresh=sa.Table('meta_refresh_states',metadata,
        sa.Column('account_id',sa.String(100),primary_key=True),
        sa.Column('lease_until',sa.String(40),nullable=False),
        sa.Column('lease_token',sa.String(36),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),
        sa.Column('attempts',sa.Integer(),nullable=False),
        sa.Column('next_attempt_at',sa.String(40),nullable=False),
        sa.Column('last_error',sa.String(40),nullable=False))
    for table in (inbox,refresh):table.create(op.get_bind(),checkfirst=True)

def downgrade():
    # Roll back code/config to 003 and retain these independent additive tables.
    # Physical DROP would lose already acknowledged events and deduplication IDs.
    pass
