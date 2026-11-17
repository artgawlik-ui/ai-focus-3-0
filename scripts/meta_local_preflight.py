"""Walidacja dostarczonej konfiguracji testowej, bez HTTP, DB i ujawniania wartości."""
from cryptography.fernet import Fernet

FLAGS=('META_ENABLED','META_OAUTH_ENABLED','META_WEBHOOK_VERIFY_ENABLED','META_INGEST_ENABLED','META_CRM_HISTORY_ENABLED','META_DIAGNOSTICS_ENABLED','META_DM_TRANSPORT_ENABLED')
REQUIRED=('META_APP_ID','META_APP_SECRET','META_CONFIG_ID','META_VERIFY_TOKEN','META_ENCRYPTION_KEY','META_TEST_ACCOUNT_ID','META_REDIRECT_URI','META_MODE')
REDIRECT='https://ai-focus-3-0.onrender.com/api/meta/oauth/callback'


def inspect_configuration(values):
    """Nie czyta os.environ: wywołujący jawnie dostarcza syntetyczny profil."""
    statuses={name:'ustawione' if values.get(name) else 'puste' for name in REQUIRED+FLAGS}
    for name in ('META_APP_ID','META_CONFIG_ID','META_TEST_ACCOUNT_ID'):
        if values.get(name) and (not str(values[name]).isascii() or not str(values[name]).isdigit()):
            statuses[name]='zły format'
    if values.get('META_MODE') and values['META_MODE']!='development':statuses['META_MODE']='zły format'
    if values.get('META_REDIRECT_URI') and values['META_REDIRECT_URI']!=REDIRECT:statuses['META_REDIRECT_URI']='zły format'
    if values.get('META_ENCRYPTION_KEY'):
        try:Fernet(values['META_ENCRYPTION_KEY'].encode())
        except Exception:statuses['META_ENCRYPTION_KEY']='zły format'
    for name in FLAGS:
        if values.get(name) and values[name].lower() not in ('true','false'):statuses[name]='zły format'
    modules_off=all(str(values.get(name,'false')).lower()!='true' for name in FLAGS)
    return {'variables':statuses,'isolated_profile_all_modules_off':modules_off,
            'configuration_valid':all(statuses[n]=='ustawione' for n in REQUIRED),
            'real_oauth_verified':False,'network_requests':0,'production_settings_read':False}
