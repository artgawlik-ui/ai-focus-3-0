from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
class UserIn(LoginIn):
    name: str = Field(min_length=2, max_length=120)
    role: Literal['sales','manager'] = 'sales'
    @field_validator('password')
    @classmethod
    def strong(cls,v):
        if len(v)<12: raise ValueError('Hasło musi mieć minimum 12 znaków')
        return v
class SalonIn(BaseModel):
    name: str = Field(min_length=2,max_length=160)
    city: str = Field(min_length=2,max_length=100)
    address: str = Field(default='',max_length=250)
    contact: str = Field(default='',max_length=160)
    email: str = Field(default='',max_length=254)
    phone: str = Field(default='',max_length=40)
    instagram: str = Field(default='',max_length=100)
    territory: str = Field(default='',max_length=100)
    specialization: str = Field(default='',max_length=250)
    priority: Literal['A+','A','B','C'] = 'B'
    stage: Literal['new','contacted','discovery','offer','negotiation','won','lost'] = 'new'
    status: Literal['prospect','active','inactive','do_not_contact'] = 'prospect'
    potential: int = Field(default=0,ge=0,le=10000000)
    next_contact: str = ''
    notes: str = Field(default='',max_length=20000)
    source_url: str = Field(default='',max_length=1000)
    @field_validator('next_contact')
    @classmethod
    def valid_date(cls,v):
        if v: date.fromisoformat(v)
        return v
    @field_validator('source_url')
    @classmethod
    def valid_url(cls,v):
        if v and not v.startswith('https://'): raise ValueError('Źródło musi używać HTTPS')
        return v
class SalonUpdate(SalonIn):
    version: int = Field(ge=1)
class ActivityIn(BaseModel):
    kind: Literal['note','call','visit','email_received','follow_up'] = 'note'
    body: str = Field(min_length=1,max_length=10000)
class AppointmentIn(BaseModel):
    salon_id: str
    starts_at: datetime
    minutes: int = Field(default=45,ge=15,le=480)
    status: Literal['proposed','confirmed'] = 'proposed'
    notes: str = Field(default='',max_length=2000)
class AppointmentStatus(BaseModel):
    status: Literal['proposed','confirmed','completed','cancelled']
class JobIn(BaseModel):
    salon_id: str
    evidence: str = Field(default='',max_length=12000)
class AssignmentIn(BaseModel):
    owner_id: str
class PasswordIn(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(min_length=12,max_length=200)
    @field_validator('new_password')
    @classmethod
    def reject_trivial(cls,value):
        if len(set(value))<5 or value.casefold() in {'password123!','testpassword123!','qwerty123456','123456789012'}:
            raise ValueError('Wybierz unikalną frazę; łatwe do odgadnięcia hasła są zabronione')
        return value
class TrainingIn(BaseModel):
    title: str = Field(min_length=2,max_length=160)
    starts_at: datetime
    minutes: int = Field(default=60,ge=15,le=480)
    notes: str = Field(default='',max_length=4000)

class BackupIn(BaseModel):
    passphrase: str = Field(min_length=20,max_length=200)
