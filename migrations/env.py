from alembic import context
from backend.db import Base, engine
from backend import meta_models  # register additive integration metadata for future autogeneration
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
