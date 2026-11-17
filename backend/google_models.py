"""Optional Calendar metadata, isolated from the legacy 004 metadata."""
from sqlalchemy import String,Text,Integer,ForeignKey
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from backend.db import User,Appointment,now

class GoogleBase(DeclarativeBase):pass

class GoogleOAuthState(GoogleBase):
    __tablename__='google_oauth_states'
    state_hash:Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id:Mapped[str]=mapped_column(ForeignKey(User.id))
    session_hash:Mapped[str]=mapped_column(String(64))
    verifier_ciphertext:Mapped[str]=mapped_column(Text)
    expires_at:Mapped[str]=mapped_column(String(40))
    consumed:Mapped[int]=mapped_column(Integer,default=0)
    cancelled:Mapped[int]=mapped_column(Integer,default=0)
    code_hash:Mapped[str|None]=mapped_column(String(64),unique=True,nullable=True)

class GoogleAccount(GoogleBase):
    __tablename__='google_accounts'
    user_id:Mapped[str]=mapped_column(ForeignKey(User.id),primary_key=True)
    tokens_ciphertext:Mapped[str]=mapped_column(Text,default='')
    calendar_id:Mapped[str]=mapped_column(String(300),default='')
    generation:Mapped[int]=mapped_column(Integer,default=1)
    approved:Mapped[int]=mapped_column(Integer,default=0)
    approved_by:Mapped[str|None]=mapped_column(ForeignKey(User.id),nullable=True)
    approved_at:Mapped[str]=mapped_column(String(40),default='')
    revoked:Mapped[int]=mapped_column(Integer,default=0)
    status:Mapped[str]=mapped_column(String(40),default='awaiting_approval')
    updated_at:Mapped[str]=mapped_column(String(40),default=now)

class GoogleEventLink(GoogleBase):
    __tablename__='google_event_links'
    appointment_id:Mapped[str]=mapped_column(ForeignKey(Appointment.id),primary_key=True)
    user_id:Mapped[str]=mapped_column(ForeignKey(GoogleAccount.user_id))
    generation:Mapped[int]=mapped_column(Integer)
    calendar_id:Mapped[str]=mapped_column(String(300))
    event_id:Mapped[str]=mapped_column(String(120))
    etag:Mapped[str]=mapped_column(String(300))
    payload_hash:Mapped[str]=mapped_column(String(64))
    status:Mapped[str]=mapped_column(String(30))
    updated_at:Mapped[str]=mapped_column(String(40),default=now)

class GoogleSyncRequest(GoogleBase):
    __tablename__='google_sync_requests'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    appointment_id:Mapped[str]=mapped_column(ForeignKey(Appointment.id),index=True)
    user_id:Mapped[str]=mapped_column(ForeignKey(GoogleAccount.user_id),index=True)
    requested_by:Mapped[str]=mapped_column(ForeignKey(User.id))
    generation:Mapped[int]=mapped_column(Integer)
    payload_hash:Mapped[str]=mapped_column(String(64))
    local_revision:Mapped[str]=mapped_column(String(64))
    payload_ciphertext:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(30),default='pending',index=True)
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    next_attempt_at:Mapped[str]=mapped_column(String(40),default='')
    expires_at:Mapped[str]=mapped_column(String(40))
    last_error:Mapped[str]=mapped_column(String(40),default='')
    created_at:Mapped[str]=mapped_column(String(40),default=now)
    updated_at:Mapped[str]=mapped_column(String(40),default=now)
