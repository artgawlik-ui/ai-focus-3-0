"""Optional bounded query indexes; no row deletion or schema data rewrite."""
from alembic import op
revision='007'
down_revision='006'
def upgrade():
    from backend.native_models import register_performance_indexes
    for index in register_performance_indexes():index.create(op.get_bind(),checkfirst=True)
def downgrade():
    from backend.native_models import register_performance_indexes
    for index in reversed(register_performance_indexes()):index.drop(op.get_bind(),checkfirst=True)
