"""Optional native planning, based on existing 004; does not require Google005."""
from alembic import op
revision='006'
down_revision='004'
def upgrade():
    from backend.native_models import NativeBase
    NativeBase.metadata.create_all(op.get_bind(),checkfirst=True)
def downgrade():
    # Marker rollback only. Keep tasks, policies, reminders and all CRM data.
    pass
