"""Current reminder projection, bounded inserts and live filtering before pagination."""
from datetime import datetime,timezone
from sqlalchemy import text
from backend.native_queries import bounds
TASK_SOURCE="""
 SELECT 'task:'||t.id||':'||CAST(t.version AS text) AS key,s.owner_id AS user_id,t.id AS task_id,
 '' AS appointment_id,t.title AS title,t.due_at AS due_at
 FROM focus_tasks t JOIN salons s ON s.id=t.salon_id JOIN users u ON u.id=s.owner_id AND u.active=1
 WHERE t.status IN ('planned','in_progress') AND CAST(t.due_at AS timestamptz)<=CAST(:now AS timestamptz)
 AND s.status<>'do_not_contact' AND NOT EXISTS(SELECT 1 FROM meta_conversations m WHERE m.salon_id=s.id AND m.opted_out=1)
"""
VISIT_SOURCE="""
 SELECT 'visit:'||a.id||':'||substr(encode(sha256(convert_to(a.starts_at,'UTF8')),'hex'),1,16)||':'||CAST(o.minutes AS text) AS key,
 a.user_id,NULL AS task_id,a.id AS appointment_id,
 CASE WHEN o.minutes=0 THEN 'Termin wizyty: ' ELSE 'Zbliża się wizyta: ' END||s.name AS title,a.starts_at AS due_at
 FROM appointments a JOIN salons s ON s.id=a.salon_id AND s.owner_id=a.user_id
 JOIN users u ON u.id=a.user_id AND u.active=1 LEFT JOIN focus_work_settings w ON w.user_id=a.user_id
 CROSS JOIN LATERAL (
 SELECT min(CAST(value AS integer)) AS minutes FROM jsonb_array_elements_text(COALESCE(CAST(w.reminders AS jsonb),'[1440,120,30]'::jsonb))
 WHERE (CAST(value AS integer)>0 AND CAST(a.starts_at AS timestamptz)>=CAST(:now AS timestamptz)
 AND CAST(a.starts_at AS timestamptz)<=CAST(:now AS timestamptz)+CAST(value AS integer)*interval '1 minute')
 OR (CAST(value AS integer)=0 AND CAST(a.starts_at AS timestamptz)<=CAST(:now AS timestamptz)
 AND CAST(a.starts_at AS timestamptz)>CAST(:now AS timestamptz)-interval '24 hours')
 ) o
 WHERE a.status='confirmed' AND o.minutes IS NOT NULL AND s.status<>'do_not_contact'
 AND NOT EXISTS(SELECT 1 FROM meta_conversations m WHERE m.salon_id=s.id AND m.opted_out=1)
"""
SOURCES='WITH live AS MATERIALIZED (SELECT * FROM ('+TASK_SOURCE+' UNION ALL '+VISIT_SOURCE+') own WHERE own.user_id=:reader) '

def generate(db,instant=None,batch=500):
    # No sleep/network, no deletion. Repeated batches exclude already current deliveries.
    db.flush();p={'now':(instant or datetime.now(timezone.utc)).isoformat(),'batch':min(500,max(1,batch))}
    total=0
    for source in (TASK_SOURCE,VISIT_SOURCE):
        result=db.execute(text('WITH live AS ('+source+''')
        INSERT INTO focus_notifications(key,user_id,task_id,appointment_id,at,read)
        SELECT l.key,l.user_id,l.task_id,l.appointment_id,:now,0 FROM live l
        WHERE NOT EXISTS(SELECT 1 FROM focus_notifications n WHERE n.key=l.key AND n.user_id=l.user_id)
        ORDER BY l.due_at,l.key LIMIT :batch
        ON CONFLICT(key) DO UPDATE SET user_id=EXCLUDED.user_id,read=0,at=EXCLUDED.at
        WHERE focus_notifications.user_id<>EXCLUDED.user_id
        '''),p)
        total+=result.rowcount
    return total

def page(db,user,limit=20,offset=0):
    bounds(limit,offset);p={'now':datetime.now(timezone.utc).isoformat(),'user_id':user.id,'reader':user.id,'limit':limit,'offset':offset}
    joined=' FROM live l JOIN focus_notifications n ON n.key=l.key AND n.user_id=l.user_id WHERE n.user_id=:user_id'
    total=db.scalar(text(SOURCES+'SELECT count(*)'+joined),p)
    rows=db.execute(text(SOURCES+'SELECT n.key,l.title,n.at,n.read'+joined+' ORDER BY n.at DESC,n.key LIMIT :limit OFFSET :offset'),p).mappings()
    return {'items':[dict(r)|{'read':bool(r['read'])} for r in rows],'total':total,'limit':limit,'offset':offset,'has_more':offset+limit<total}
