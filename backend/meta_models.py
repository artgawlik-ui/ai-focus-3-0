"""Instagram development metadata; credentials and message content are encrypted."""
from sqlalchemy import String,Text,Integer,ForeignKey,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from backend.db import Base,now

class MetaOAuthState(Base):
    __tablename__='meta_oauth_states'
    state_hash:Mapped[str]=mapped_column(String(64),primary_key=True)
    code_hash:Mapped[str|None]=mapped_column(String(64),nullable=True,unique=True)
    nonce_hash:Mapped[str]=mapped_column(String(64))
    session_hash:Mapped[str]=mapped_column(String(64))
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    expires_at:Mapped[str]=mapped_column(String(40))
    consumed:Mapped[int]=mapped_column(Integer,default=0)

class MetaConversation(Base):
    __tablename__='meta_conversations'
    __table_args__=(UniqueConstraint('account_id','peer_id'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    account_id:Mapped[str]=mapped_column(String(100))
    peer_id:Mapped[str]=mapped_column(String(100))
    salon_id:Mapped[str|None]=mapped_column(ForeignKey('salons.id'),nullable=True)
    last_inbound_at:Mapped[str]=mapped_column(String(40),default='')
    opted_out:Mapped[int]=mapped_column(Integer,default=0)
    created_at:Mapped[str]=mapped_column(String(40),default=now)

class MetaMessage(Base):
    __tablename__='meta_messages'
    __table_args__=(UniqueConstraint('conversation_id','external_id'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    conversation_id:Mapped[str]=mapped_column(ForeignKey('meta_conversations.id'))
    external_id:Mapped[str|None]=mapped_column(String(250),nullable=True)
    status:Mapped[str]=mapped_column(String(40))
    direction:Mapped[str]=mapped_column(String(20))
    body_ciphertext:Mapped[str]=mapped_column(Text,default='')
    occurred_at:Mapped[str]=mapped_column(String(40))
    created_at:Mapped[str]=mapped_column(String(40),default=now)
    approved_by:Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)

class MetaCredential(Base):
    __tablename__='meta_credentials'
    account_id:Mapped[str]=mapped_column(String(100),primary_key=True)
    business_id:Mapped[str]=mapped_column(String(100))
    subject_id:Mapped[str]=mapped_column(String(100))
    username:Mapped[str]=mapped_column(String(100))
    config_id:Mapped[str]=mapped_column(String(100))
    token_ciphertext:Mapped[str]=mapped_column(Text)
    expires_at:Mapped[str]=mapped_column(String(40),default='')
    checked_at:Mapped[str]=mapped_column(String(40),default=now)
    revoked:Mapped[int]=mapped_column(Integer,default=0)

class MetaPrivacyRequest(Base):
    __tablename__='meta_privacy_requests'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    request_hash:Mapped[str]=mapped_column(String(64),unique=True)
    subject_hash:Mapped[str]=mapped_column(String(64))
    kind:Mapped[str]=mapped_column(String(30))
    status:Mapped[str]=mapped_column(String(30))
    created_at:Mapped[str]=mapped_column(String(40),default=now)

class MetaWebhookInbox(Base):
    __tablename__='meta_webhook_inbox'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    dedup_key:Mapped[str]=mapped_column(String(64),unique=True)
    account_id:Mapped[str]=mapped_column(String(100))
    payload_ciphertext:Mapped[str]=mapped_column(Text,default='')
    status:Mapped[str]=mapped_column(String(20),default='pending',index=True)
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    next_attempt_at:Mapped[str]=mapped_column(String(40),default='')
    lease_until:Mapped[str]=mapped_column(String(40),default='')
    lease_token:Mapped[str]=mapped_column(String(36),default='')
    created_at:Mapped[str]=mapped_column(String(40),default=now)
    updated_at:Mapped[str]=mapped_column(String(40),default=now)
    processed_at:Mapped[str]=mapped_column(String(40),default='')
    last_error:Mapped[str]=mapped_column(String(40),default='')
    dead_letter:Mapped[int]=mapped_column(Integer,default=0)

class MetaRefreshState(Base):
    __tablename__='meta_refresh_states'
    account_id:Mapped[str]=mapped_column(String(100),primary_key=True)
    lease_until:Mapped[str]=mapped_column(String(40),default='')
    lease_token:Mapped[str]=mapped_column(String(36),default='')
    status:Mapped[str]=mapped_column(String(20),default='idle')
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    next_attempt_at:Mapped[str]=mapped_column(String(40),default='')
    last_error:Mapped[str]=mapped_column(String(40),default='')
