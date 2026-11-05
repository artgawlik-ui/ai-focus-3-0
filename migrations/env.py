from alembic import context
from backend.db import Base, engine
from backend import meta_models  # register additive integration metadata for future autogeneration
metadata=Base.metadata
if context.config.get_main_option('google_calendar_migrations')=='true':
    from backend.google_models import GoogleBase
    metadata=[Base.metadata,GoogleBase.metadata]
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
