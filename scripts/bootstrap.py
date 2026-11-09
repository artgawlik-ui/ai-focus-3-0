"""Create only the initial manager in an empty database. Never recreate test accounts."""
import os,uuid
from sqlalchemy import select,func,text
from backend.db import Session,User
from backend.security import ph
from backend.schemas import PasswordIn
from pydantic import ValidationError


def main():
    try:
        _initialize()
    except Exception:
        # Driver failures can contain query details; CLI output must remain generic.
        raise SystemExit('Bootstrap failed; check database/configuration securely.') from None


def _initialize():
    with Session() as db:
        if db.bind.dialect.name=='postgresql':
            db.execute(text('SET TRANSACTION ISOLATION LEVEL READ COMMITTED'))
        # Existing installations need no retained provisioning credentials on restart.
        # This also leaves disabled users, password hashes and sessions untouched.
        if db.scalar(select(func.count()).select_from(User)):
            print('Bootstrap skipped: users already exist.')
            return
        if db.bind.dialect.name=='postgresql':
            db.execute(text("SET LOCAL lock_timeout='5s'"))
            db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('focus-bootstrap-owner',0))"))
            if db.scalar(select(func.count()).select_from(User)):
                print('Bootstrap skipped: users already exist.')
                return
        email=os.environ.get('BOOTSTRAP_EMAIL','').strip().lower()
        password=os.environ.get('BOOTSTRAP_PASSWORD','')
        message='Set BOOTSTRAP_EMAIL and BOOTSTRAP_PASSWORD (non-trivial 12-200 characters) securely.'
        if not email or len(email)>254:
            raise SystemExit(message)
        try:
            password=PasswordIn(current_password='',new_password=password).new_password
        except ValidationError:
            # Pydantic includes input values in its default error; never propagate them.
            raise SystemExit(message) from None
        db.add(User(id=str(uuid.uuid4()),email=email,name=os.getenv('BOOTSTRAP_NAME','Menedżer'),password_hash=ph.hash(password),role='manager'))
        db.commit()
        print('Initial manager created.')


if __name__=='__main__':main()
