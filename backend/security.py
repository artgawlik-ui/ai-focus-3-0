import hashlib, secrets, os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, Request, HTTPException
from sqlalchemy import select
from argon2 import PasswordHasher
from backend.db import Session, LoginSession, User
ph = PasswordHasher()
secure = os.getenv('APP_ENV', 'development') == 'production'

def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def expires(hours=12): return (datetime.now(timezone.utc)+timedelta(hours=hours)).isoformat()
def database():
    with Session() as db: yield db

def current(request: Request, db=Depends(database)):
    session = db.get(LoginSession, digest(request.cookies.get('focus_session', '')))
    if not session or session.expires < datetime.now(timezone.utc).isoformat():
        raise HTTPException(401, 'Zaloguj się ponownie')
    user = db.get(User, session.user_id)
    if not user or not user.active: raise HTTPException(401, 'Konto nieaktywne')
    if request.method not in ('GET','HEAD','OPTIONS'):
        if not secrets.compare_digest(request.headers.get('X-CSRF-Token',''), session.csrf):
            raise HTTPException(403, 'Nieprawidłowy token CSRF')
    return user

def manager(user=Depends(current)):
    if user.role != 'manager': raise HTTPException(403, 'Wymagane konto menedżera')
    return user

def public_user(user): return {k:getattr(user,k) for k in ('id','name','email','role','active')}
