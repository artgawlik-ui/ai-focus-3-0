import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def now():
    return datetime.now(timezone.utc).isoformat()

url = os.getenv('DATABASE_URL', 'sqlite:///./focus3.db')
if os.getenv('APP_ENV') == 'production' and not url.startswith(('postgres://','postgresql://','postgresql+psycopg://')):
    raise RuntimeError('Production requires an isolated PostgreSQL DATABASE_URL')
if url.startswith('postgres://'):
    url = url.replace('postgres://', 'postgresql+psycopg://', 1)
elif url.startswith('postgresql://'):
    url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
engine = create_engine(url, pool_pre_ping=True, hide_parameters=True, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {})
if url.startswith('sqlite'):
    from sqlalchemy import event
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='sales')
    active: Mapped[int] = mapped_column(Integer, default=1)

class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    csrf: Mapped[str] = mapped_column(String(64))
    expires: Mapped[str] = mapped_column(String(40))

class LoginAttempt(Base):
    __tablename__ = 'login_attempts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[str] = mapped_column(String(40))

class Salon(Base):
    __tablename__ = 'salons'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(100), index=True)
    address: Mapped[str] = mapped_column(String(250), default='')
    contact: Mapped[str] = mapped_column(String(160), default='')
    email: Mapped[str] = mapped_column(String(254), default='')
    phone: Mapped[str] = mapped_column(String(40), default='')
    instagram: Mapped[str] = mapped_column(String(100), default='')
    territory: Mapped[str] = mapped_column(String(100), default='')
    specialization: Mapped[str] = mapped_column(String(250), default='')
    priority: Mapped[str] = mapped_column(String(2), default='B')
    stage: Mapped[str] = mapped_column(String(30), default='new')
    status: Mapped[str] = mapped_column(String(20), default='prospect')
    potential: Mapped[int] = mapped_column(Integer, default=0)
    next_contact: Mapped[str] = mapped_column(String(10), default='')
    notes: Mapped[str] = mapped_column(Text, default='')
    source_url: Mapped[str] = mapped_column(String(1000), default='')
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)

class Activity(Base):
    __tablename__ = 'activities'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    salon_id: Mapped[str] = mapped_column(ForeignKey('salons.id'), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(30))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now)

class Appointment(Base):
    __tablename__ = 'appointments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    salon_id: Mapped[str] = mapped_column(ForeignKey('salons.id'), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    starts_at: Mapped[str] = mapped_column(String(40))
    ends_at: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default='proposed')
    notes: Mapped[str] = mapped_column(Text, default='')

class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    salon_id: Mapped[str] = mapped_column(ForeignKey('salons.id'))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    status: Mapped[str] = mapped_column(String(20), default='queued')
    evidence: Mapped[str] = mapped_column(Text, default='')
    result: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)

class IntegrationLink(Base):
    __tablename__ = 'integration_links'
    __table_args__ = (UniqueConstraint('provider', 'external_id'), UniqueConstraint('provider', 'salon_id'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    salon_id: Mapped[str] = mapped_column(ForeignKey('salons.id'))
    provider: Mapped[str] = mapped_column(String(30))
    external_id: Mapped[str] = mapped_column(String(200))
    sync_cursor: Mapped[str] = mapped_column(String(200), default='')

class Training(Base):
    __tablename__ = 'trainings'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    starts_at: Mapped[str] = mapped_column(String(40))
    minutes: Mapped[int] = mapped_column(Integer, default=60)
    notes: Mapped[str] = mapped_column(Text, default='')
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
