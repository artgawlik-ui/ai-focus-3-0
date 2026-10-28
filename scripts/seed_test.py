"""Synthetic data for automated browser tests only. Never run in production."""
import os, uuid
if os.getenv('APP_ENV')!='test': raise SystemExit('Requires APP_ENV=test')
from backend.db import Session, User, Salon
from backend.security import ph
from backend.main import key
from sqlalchemy import select
with Session() as db:
    if db.scalar(select(User)): raise SystemExit('Refusing to seed nonempty database')
    user=User(id='e2e-manager',email='e2e@focus.test',name='Tester Focus',role='manager',password_hash=ph.hash('E2eSyntheticPassword123!'))
    db.add(user); db.flush()
    for name,city,priority,stage,potential in [('Salon Testowy Atelier','Głogów','A+','offer',3500),('Salon Testowy Studio','Lubin','A','discovery',2200),('Salon Testowy Forma','Polkowice','B','new',1800)]:
        db.add(Salon(id=str(uuid.uuid4()),owner_id=user.id,name=name,city=city,priority=priority,stage=stage,potential=potential,dedup_key=key(name,city),address='Rynek 1',next_contact='2026-01-01'))
    db.commit()
print('Synthetic E2E fixtures created.')
