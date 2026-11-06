"""Bounded PostgreSQL projections. All user values are bound parameters."""
from datetime import datetime,timedelta,time,timezone
from zoneinfo import ZoneInfo
from sqlalchemy import text
from fastapi import HTTPException
ZONE=ZoneInfo('Europe/Warsaw')
CONTACT_BASE=r"""
WITH eligible AS MATERIALIZED (
 SELECT s.*,u.name AS representative_name FROM salons s JOIN users u ON u.id=s.owner_id AND u.active=1
 WHERE (:manager OR s.owner_id=:user_id) AND (:rep='' OR s.owner_id=:rep)
 AND (:salon='' OR s.id=:salon) AND s.status<>'do_not_contact'
 AND NOT EXISTS(SELECT 1 FROM meta_conversations m WHERE m.salon_id=s.id AND m.opted_out=1)
 AND (:search='' OR strpos(lower(s.name),lower(:search))>0 OR strpos(lower(u.name),lower(:search))>0)
 AND (:priority='' OR s.priority=:priority)
), latest AS (
 SELECT DISTINCT ON (a.salon_id) a.salon_id,a.id,
 CASE WHEN pg_input_is_valid(a.created_at,'timestamp with time zone') THEN CAST(a.created_at AS timestamptz) END AS at
 FROM activities a JOIN eligible e ON e.id=a.salon_id
 WHERE a.kind IN ('call','visit','email_received','instagram_received')
 AND CASE WHEN pg_input_is_valid(a.created_at,'timestamp with time zone') THEN CAST(a.created_at AS timestamptz) END<=CAST(:until AS timestamptz)
 ORDER BY a.salon_id,at DESC,a.id DESC
), followups AS (
 SELECT DISTINCT ON(t.salon_id) t.salon_id,t.id,t.cycle_key,t.assignee_id
 FROM focus_tasks t JOIN eligible e ON e.id=t.salon_id
 WHERE t.cycle_key LIKE 'followup:%' AND t.status IN ('planned','in_progress')
 ORDER BY t.salon_id,t.id
), evidence AS (
 SELECT s.id AS salon_id,s.name AS salon_name,s.owner_id,s.priority,s.created_at,
 s.representative_name,l.at AS last_contact_at,l.id AS cycle_id,
 COALESCE(p.interval_days,CAST(CAST(w.intervals AS jsonb)->>s.priority AS integer),
 CASE s.priority WHEN 'A+' THEN 7 WHEN 'A' THEN 14 WHEN 'B' THEN 30 ELSE 60 END) AS interval_days,
 COALESCE(CAST(l.at AT TIME ZONE 'Europe/Warsaw' AS date),CAST(CAST(s.created_at AS timestamptz) AT TIME ZONE 'Europe/Warsaw' AS date)) AS base_day,
 f.id AS task_id,f.cycle_key AS task_cycle,f.assignee_id AS task_owner
 FROM eligible s LEFT JOIN latest l ON l.salon_id=s.id
 LEFT JOIN followups f ON f.salon_id=s.id
 LEFT JOIN focus_contact_policies p ON p.salon_id=s.id
 LEFT JOIN focus_work_settings w ON w.user_id=s.owner_id
), aged AS (
 SELECT *,GREATEST(0,CAST(:day AS date)-base_day) AS age,
 CASE WHEN last_contact_at IS NULL THEN CAST(:day AS date) ELSE base_day+interval_days END AS due_on,
 COALESCE(cycle_id,'never') AS cycle FROM evidence
), projection AS (
 SELECT *,last_contact_at IS NULL OR CAST(:day AS date)>=due_on AS requires_contact,
 CASE WHEN last_contact_at IS NULL THEN age ELSE GREATEST(0,CAST(:day AS date)-due_on) END AS overdue_days
 FROM aged
)
"""
CONTACT_WHERE=""" WHERE (:due_only=false OR requires_contact)
AND (:from_date='' OR due_on>=CAST(NULLIF(:from_date,'') AS date))
AND (:to_date='' OR due_on<=CAST(NULLIF(:to_date,'') AS date))
"""
CONTACT_ORDER="CASE priority WHEN 'A+' THEN 0 WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END,overdue_days DESC,salon_name,salon_id"

def bounds(limit,offset):
    if not 1<=limit<=100 or not 0<=offset<=100000:raise HTTPException(422,'Limit1–100, offset0–100000')
def scope(user,rep):
    if rep and user.role!='manager' and rep!=user.id:raise HTTPException(403,'Niedozwolony handlowiec')
    return {'manager':user.role=='manager','user_id':user.id,'rep':rep}
def contact_params(user,day,rep='',salon='',search='',priority='',due_only=False,from_date='',to_date=''):
    until=min(datetime.now(timezone.utc),datetime.combine(day+timedelta(days=1),time.min,ZONE).astimezone(timezone.utc)-timedelta(microseconds=1))
    return {**scope(user,rep),'day':day.isoformat(),'until':until.isoformat(),'salon':salon,'search':search,'priority':priority,'due_only':due_only,'from_date':from_date,'to_date':to_date}
def contact_view(r):
    last=r['last_contact_at'];age=r['age']
    return {'salon_id':r['salon_id'],'salon_name':r['salon_name'],'owner_id':r['owner_id'],'priority':r['priority'],'representative_name':r['representative_name'],'last_contact_at':last.isoformat() if last else None,'days_since_contact':age if last else None,'days_since_registration':max(0,(r['_day']-datetime.fromisoformat(r['created_at']).astimezone(ZONE).date()).days),'threshold':max([d for d in (7,14,30,60) if age>=d],default=0),'interval_days':r['interval_days'],'due_on':r['due_on'].isoformat(),'requires_contact':r['requires_contact'],'overdue_days':r['overdue_days'],'cycle':r['cycle'],'task_id':r['task_id']}
def contacts_page(db,user,day,rep='',limit=20,offset=0,**filters):
    bounds(limit,offset);p=contact_params(user,day,rep,**filters)
    total=db.scalar(text(CONTACT_BASE+' SELECT count(*) FROM projection'+CONTACT_WHERE),p)
    rows=db.execute(text(CONTACT_BASE+' SELECT * FROM projection'+CONTACT_WHERE+' ORDER BY '+CONTACT_ORDER+' LIMIT :limit OFFSET :offset'),{**p,'limit':limit,'offset':offset}).mappings()
    return {'items':[contact_view({**r,'_day':day}) for r in rows],'total':total,'limit':limit,'offset':offset,'has_more':offset+limit<total}
def contact_work(db,user,day,limit=100):
    p=contact_params(user,day)
    condition=""" WHERE (task_id IS NOT NULL AND (task_cycle<>'followup:'||salon_id||':'||cycle OR task_owner<>owner_id))
    OR (requires_contact AND task_id IS NULL AND NOT EXISTS(SELECT 1 FROM focus_tasks t WHERE t.cycle_key='followup:'||salon_id||':'||cycle))"""
    rows=db.execute(text(CONTACT_BASE+' SELECT * FROM projection'+condition+' ORDER BY salon_id LIMIT :limit'),{**p,'limit':limit}).mappings()
    return [contact_view({**r,'_day':day}) for r in rows]

TASK_FROM="FROM focus_tasks t JOIN salons s ON s.id=t.salon_id JOIN users u ON u.id=s.owner_id"
TASK_WHERE=""" WHERE (:manager OR s.owner_id=:user_id) AND (:rep='' OR s.owner_id=:rep)
 AND (:search='' OR strpos(lower(s.name),lower(:search))>0 OR strpos(lower(t.title),lower(:search))>0 OR strpos(lower(u.name),lower(:search))>0)
 AND (:priority='' OR t.priority=:priority) AND (:status='' OR t.status=:status)
 AND (:from_date='' OR CAST(CAST(t.due_at AS timestamptz) AT TIME ZONE 'Europe/Warsaw' AS date)>=CAST(NULLIF(:from_date,'') AS date))
 AND (:to_date='' OR CAST(CAST(t.due_at AS timestamptz) AT TIME ZONE 'Europe/Warsaw' AS date)<=CAST(NULLIF(:to_date,'') AS date))"""
TASK_ORDER="CASE WHEN t.status IN ('planned','in_progress') THEN 0 ELSE 1 END,CASE t.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,t.due_at,t.id"
def task_params(user,rep='',search='',priority='',status='',from_date='',to_date=''):
    return {**scope(user,rep),'search':search,'priority':priority,'status':status,'from_date':from_date,'to_date':to_date}
def tasks_page(db,user,rep='',limit=20,offset=0,**filters):
    bounds(limit,offset);p=task_params(user,rep,**filters)
    total=db.scalar(text('SELECT count(*) '+TASK_FROM+TASK_WHERE),p)
    rows=db.execute(text('SELECT t.*,s.name AS salon_name,s.owner_id AS current_owner,u.name AS representative_name '+TASK_FROM+TASK_WHERE+' ORDER BY '+TASK_ORDER+' LIMIT :limit OFFSET :offset'),{**p,'limit':limit,'offset':offset}).mappings()
    instant=datetime.now(timezone.utc)
    items=[dict(r)|{'overdue':r['status'] in ('planned','in_progress') and datetime.fromisoformat(r['due_at'])<instant} for r in rows]
    return {'items':items,'total':total,'limit':limit,'offset':offset,'has_more':offset+limit<total}

def report_summary(db,user,day,rep=''):
    p=contact_params(user,day,rep)
    contact_counts=db.execute(text(CONTACT_BASE+" SELECT owner_id,count(*) FILTER(WHERE requires_contact) AS neglected,count(*) FILTER(WHERE requires_contact AND priority IN ('A+','A')) AS high_priority FROM projection GROUP BY owner_id"),p).mappings().all()
    instant=datetime.now(timezone.utc);start=datetime.combine(day,time.min,ZONE).astimezone(timezone.utc);end=datetime.combine(day+timedelta(days=1),time.min,ZONE).astimezone(timezone.utc)
    p={**p,'now':instant.isoformat(),'start':start.isoformat(),'end':end.isoformat(),'next2':(instant+timedelta(hours=2)).isoformat(),'next24':(instant+timedelta(hours=24)).isoformat()}
    tc=db.execute(text("""SELECT s.owner_id,count(*) FILTER(WHERE t.status IN ('planned','in_progress') AND t.due_at<:now) AS overdue_tasks,
    count(*) FILTER(WHERE t.status='completed') AS completed_tasks,
    count(*) FILTER(WHERE t.status='completed' AND CAST(NULLIF(t.completed_at,'') AS timestamptz)<=CAST(t.due_at AS timestamptz)) AS completed_on_time,
    count(*) FILTER(WHERE t.due_at>=:start AND t.due_at<:end) AS tasks_today,
    count(*) FILTER(WHERE t.status IN ('planned','in_progress') AND t.due_at>=:now AND t.due_at<=:next24) AS due_next_24h,
    count(*) FILTER(WHERE t.status='planned' AND t.due_at>=:now AND t.due_at<=:next2) AS at_risk_tasks
    """+TASK_FROM+" WHERE (:manager OR s.owner_id=:user_id) AND (:rep='' OR s.owner_id=:rep) GROUP BY s.owner_id"),p).mappings().all()
    vc=db.execute(text("""SELECT s.owner_id,count(*) AS visits_today,
    count(*) FILTER(WHERE a.status='completed') AS visits_completed_recorded,
    count(*) FILTER(WHERE a.status IN ('proposed','confirmed') AND a.ends_at<:now) AS visits_uncompleted,
    count(*) FILTER(WHERE a.status='confirmed' AND a.starts_at>=:now AND a.starts_at<=:next2) AS visits_next_2h
    FROM appointments a JOIN salons s ON s.id=a.salon_id WHERE a.user_id=s.owner_id
    AND (:manager OR s.owner_id=:user_id) AND (:rep='' OR s.owner_id=:rep)
    AND a.starts_at>=:start AND a.starts_at<:end GROUP BY s.owner_id"""),p).mappings().all()
    cc=db.execute(text("""SELECT a.user_id,count(*) AS contacts_recorded FROM activities a JOIN salons s ON s.id=a.salon_id
    WHERE (:manager OR s.owner_id=:user_id) AND (:rep='' OR s.owner_id=:rep)
    AND a.kind IN ('call','visit','email_received','instagram_received') AND a.created_at>=:start AND a.created_at<:end AND a.created_at<=:now
    AND s.status<>'do_not_contact' AND NOT EXISTS(SELECT 1 FROM meta_conversations m WHERE m.salon_id=s.id AND m.opted_out=1)
    GROUP BY a.user_id"""),p).mappings().all()
    groups={}
    for rows in (contact_counts,tc,vc,cc):
        for r in rows:
            key=r.get('owner_id',r.get('user_id'));groups.setdefault(key,{}).update({k:v for k,v in r.items() if k not in ('owner_id','user_id')})
    keys=('neglected','high_priority','overdue_tasks','completed_tasks','completed_on_time','tasks_today','due_next_24h','at_risk_tasks','visits_today','visits_completed_recorded','visits_uncompleted','visits_next_2h','contacts_recorded')
    totals={k:sum(g.get(k,0) for g in groups.values()) for k in keys}
    team=[]
    if user.role=='manager':
        for u in db.execute(text("SELECT id,name FROM users WHERE active=1 AND (:rep='' OR id=:rep) ORDER BY name,id"),p).mappings():team.append({'representative_id':u['id'],'name':u['name'],**{k:groups.get(u['id'],{}).get(k,0) for k in keys}})
    return totals,team
