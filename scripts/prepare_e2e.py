import psycopg
with psycopg.connect('postgresql://postgres@127.0.0.1:55432/postgres',autocommit=True) as db:
    for name in ['focus3_e2e','focus3_restore']:
        if not db.execute('SELECT 1 FROM pg_database WHERE datname=%s',(name,)).fetchone():
            db.execute('CREATE DATABASE '+name)
