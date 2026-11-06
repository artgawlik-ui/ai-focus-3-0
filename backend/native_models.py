"""Optional native planning metadata; no changes to legacy 004 models."""
from sqlalchemy import String,Text,Integer,ForeignKey
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from backend.db import User,Salon,now
class NativeBase(DeclarativeBase):pass
class ContactPolicy(NativeBase):
    __tablename__='focus_contact_policies'
    salon_id:Mapped[str]=mapped_column(ForeignKey(Salon.id),primary_key=True)
    interval_days:Mapped[int]=mapped_column(Integer)
class WorkSettings(NativeBase):
    __tablename__='focus_work_settings'
    user_id:Mapped[str]=mapped_column(ForeignKey(User.id),primary_key=True)
    intervals:Mapped[str]=mapped_column(Text,default='{"A+":7,"A":14,"B":30,"C":60}')
    reminders:Mapped[str]=mapped_column(Text,default='[1440,120,30]')
class Task(NativeBase):
    __tablename__='focus_tasks'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    salon_id:Mapped[str]=mapped_column(ForeignKey(Salon.id),index=True)
    assignee_id:Mapped[str]=mapped_column(ForeignKey(User.id),index=True)
    title:Mapped[str]=mapped_column(String(180))
    due_at:Mapped[str]=mapped_column(String(40),index=True)
    priority:Mapped[str]=mapped_column(String(10),default='normal')
    status:Mapped[str]=mapped_column(String(15),default='planned')
    repeat_days:Mapped[int]=mapped_column(Integer,default=0)
    cycle_key:Mapped[str|None]=mapped_column(String(160),unique=True,nullable=True)
    result:Mapped[str]=mapped_column(Text,default='')
    version:Mapped[int]=mapped_column(Integer,default=1)
    created_at:Mapped[str]=mapped_column(String(40),default=now)
    completed_at:Mapped[str]=mapped_column(String(40),default='')
class Notification(NativeBase):
    __tablename__='focus_notifications'
    key:Mapped[str]=mapped_column(String(200),primary_key=True)
    user_id:Mapped[str]=mapped_column(ForeignKey(User.id),index=True)
    task_id:Mapped[str|None]=mapped_column(ForeignKey(Task.id),nullable=True)
    appointment_id:Mapped[str]=mapped_column(String(36),default='')
    at:Mapped[str]=mapped_column(String(40))
    read:Mapped[int]=mapped_column(Integer,default=0)
