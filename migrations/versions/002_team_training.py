"""Team training schedule."""
from alembic import op
import sqlalchemy as sa
revision='002'
down_revision='001'
def upgrade():
    # 001 installations may already include this table when initialized from current metadata.
    if not sa.inspect(op.get_bind()).has_table('trainings'):
        op.create_table('trainings',sa.Column('id',sa.String(36),primary_key=True),sa.Column('title',sa.String(160),nullable=False),sa.Column('starts_at',sa.String(40),nullable=False),sa.Column('minutes',sa.Integer(),nullable=False),sa.Column('notes',sa.Text(),nullable=False),sa.Column('created_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False))
def downgrade():
    raise RuntimeError('Destructive downgrade disabled')
