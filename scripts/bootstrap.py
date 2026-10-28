"""Create initial manager using protected environment variables; never print credentials."""
import os, uuid
from sqlalchemy import select, func
from backend.db import Session, User
from backend.security import ph

def main():
    email=os.environ.get('BOOTSTRAP_EMAIL','').strip().lower()
    password=os.environ.get('BOOTSTRAP_PASSWORD','')
    if not email or len(password)<12: raise SystemExit('Set BOOTSTRAP_EMAIL and BOOTSTRAP_PASSWORD (12+ chars) securely.')
    with Session() as db:
        if db.scalar(select(func.count()).select_from(User)):
            print('Bootstrap skipped: users already exist.'); return
        db.add(User(id=str(uuid.uuid4()),email=email,name=os.getenv('BOOTSTRAP_NAME','Menedżer'),password_hash=ph.hash(password),role='manager'))
        db.commit(); print('Initial manager created.')
if __name__=='__main__': main()
