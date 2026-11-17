"""Offline bramka profilu syntetycznego. Nie łączy się z siecią ani bazą."""
import argparse,json
from scripts.meta_local_preflight import FLAGS


def evaluate(profile):
    flags=profile.get('flags',{})
    invalid=[]
    for name in FLAGS:
        value=flags.get(name,'false')
        if not isinstance(value,str) or value.lower()!='false':invalid.append(name)
    checks={'synthetic_profile':profile.get('source')=='synthetic',
            'version':profile.get('version')=='3.0.4',
            'schema':profile.get('schema_revision')=='004',
            'meta_off':not invalid,
            'restore_test':profile.get('synthetic_restore_verified') is True,
            'rollback_test':profile.get('synthetic_rollback_verified') is True,
            'technical_disabled':profile.get('synthetic_technical_disabled') is True,
            'owner_login':profile.get('synthetic_owner_login_verified') is True}
    return {'status':'PASS_LOCAL' if all(checks.values()) else 'BLOCKED',
            'checks':checks,'invalid_flags':invalid,'production_verified':False,
            'deployment_authorized':False,'cleanup_authorized':False,'meta_activation_authorized':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--profile',required=True);args=parser.parse_args()
    try:
        with open(args.profile) as source:result=evaluate(json.load(source))
    except Exception:result={'status':'BLOCKED','reason':'invalid_profile_no_details_exposed'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='PASS_LOCAL' else 1

if __name__=='__main__':raise SystemExit(main())
