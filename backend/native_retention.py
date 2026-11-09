"""Retention proposal only. No deletion path, even if an env flag is mistakenly set."""
from datetime import datetime,timedelta,timezone
from fastapi import Depends
from sqlalchemy import text
from backend.native_planning import router,require
from backend.security import manager,database

@router.get('/retention-preview')
def preview(user=Depends(manager),db=Depends(database)):
    require();now=datetime.now(timezone.utc)
    result=db.execute(text("""SELECT
    (SELECT count(*) FROM focus_notifications WHERE read=1 AND at<:notice) AS read_notifications,
    (SELECT count(*) FROM focus_tasks WHERE status='completed' AND completed_at<>'' AND completed_at<:archive) AS tasks_for_archive_review
    """),{'notice':(now-timedelta(days=30)).isoformat(),'archive':(now-timedelta(days=365)).isoformat()}).mappings().one()
    return {'enabled':False,'dry_run':True,'deletion_implemented':False,'candidates':dict(result),'proposal':{'read_notifications_days':30,'unread_notifications':'keep_until_review','completed_tasks_archive_review_days':365,'cancelled_tasks':'keep_until_verified_close_date','client_and_contact_history':'never_automatic','process_status':'single_current_file_no_history'},'approval_required':True}
