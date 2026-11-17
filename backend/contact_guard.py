"""Transaction-scoped per-salon serialization, no schema or global lock."""
from sqlalchemy import text


def lock_contact(db, salon_id):
    if salon_id and db.bind.dialect.name == 'postgresql':
        # A hash collision only serializes unrelated salons; it cannot bypass a block.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                   {'key':'focus3-contact:' + salon_id})
