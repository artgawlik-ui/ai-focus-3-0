"""Initial isolated Focus 3 schema."""
from alembic import op
from backend.db import Base
revision = '001'
down_revision = None

def upgrade():
    Base.metadata.create_all(op.get_bind(), tables=[t for t in Base.metadata.sorted_tables if t.name != 'trainings'])

def downgrade():
    raise RuntimeError('Destructive downgrade disabled; restore a verified backup instead')
