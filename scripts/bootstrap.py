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
        if not db.scalar(select(func.count()).select_from(User)):
            db.add(User(id=str(uuid.uuid4()),email=email,name=os.getenv('BOOTSTRAP_NAME','Menedżer'),password_hash=ph.hash(password),role='manager'))
            db.commit(); print('Initial manager created.')
        else:
            print('Bootstrap skipped: users already exist.')
        verification_password=os.getenv('VERIFICATION_PASSWORD','')
        verification_email='verification@focus.invalid'
        if len(verification_password)>=24 and not db.scalar(select(User).where(User.email==verification_email)):
            db.add(User(id=str(uuid.uuid4()),email=verification_email,name='Weryfikacja techniczna',password_hash=ph.hash(verification_password),role='manager'))
            db.commit(); print('Temporary verification account created.')
if __name__=='__main__': main()
