"""Local scheduling helpers. No Google/Maps network operations."""
import os,json,hashlib
from datetime import datetime,timezone
from urllib.parse import urlencode
from sqlalchemy import select
from backend.db import Activity


def enabled():return os.getenv('VISIT_PLANNER_ENABLED','false').lower()=='true' or os.getenv('FOCUS_CALENDAR_ENABLED','false').strip().lower()=='true'


def address_text(salon):return f'Ręcznie sprawdzono adres: {salon.address.strip()}, {salon.city.strip()}.'


def verified(db,salon):
    return bool(salon.address.strip() and salon.city.strip() and db.scalar(select(Activity.id).where(Activity.salon_id==salon.id,Activity.kind=='address_verified',Activity.body==address_text(salon),Activity.created_at>=salon.updated_at).limit(1)))


def links(visit,salon,is_verified):
    location=salon.address+', '+salon.city+', Polska' if is_verified else ''
    navigation='https://www.google.com/maps/dir/?'+urlencode({'api':'1','destination':location,'travelmode':'driving'}) if location and visit.status in ('proposed','confirmed') else None
    def stamp(value):return datetime.fromisoformat(value).astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    params={'action':'TEMPLATE','text':'Wizyta: '+salon.name,'dates':stamp(visit.starts_at)+'/'+stamp(visit.ends_at)}
    if location:params['location']=location
    calendar='https://calendar.google.com/calendar/render?'+urlencode(params) if visit.status in ('proposed','confirmed') else None
    return {'address_verified':is_verified,'navigation_url':navigation,'google_calendar_url':calendar,'calendar_sync':'not_connected'}


def revision(visit):
    return hashlib.sha256(json.dumps([visit.starts_at,visit.ends_at,visit.status,visit.notes],ensure_ascii=False).encode()).hexdigest()
