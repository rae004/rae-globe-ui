from alembic import context

from globe_db.models import Base
from globe_db.session import get_engine

with get_engine().connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
