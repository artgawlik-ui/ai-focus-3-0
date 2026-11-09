"""Provider payload preparation only. No credentials, transport or external writes."""
import hashlib


def google_event(visit,salon,address_verified):
    payload={'id':'focus3'+hashlib.sha256(visit.id.encode()).hexdigest(),
             'summary':'Wizyta: '+salon.name,
             'start':{'dateTime':visit.starts_at,'timeZone':'UTC'},
             'end':{'dateTime':visit.ends_at,'timeZone':'UTC'},
             'status':'cancelled' if visit.status=='cancelled' else 'tentative' if visit.status=='proposed' else 'confirmed',
             'extendedProperties':{'private':{'focus3AppointmentId':visit.id}}}
    if address_verified:payload['location']=salon.address+', '+salon.city
    return payload
