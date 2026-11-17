"""Optional Calendar 005, never part of the default 004 migration path."""
from alembic import op
import sqlalchemy as sa
revision='005'
down_revision='004'

def upgrade():
    from backend.google_models import GoogleBase
    GoogleBase.metadata.create_all(op.get_bind(),checkfirst=True)

def downgrade():
    # Metadata rollback only: retain tokens, accepted requests and event mappings.
    # Re-enabling uses checkfirst; physical removal requires a separate approved plan.
    pass
