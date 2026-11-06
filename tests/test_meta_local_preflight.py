import json
from cryptography.fernet import Fernet
from scripts.meta_local_preflight import inspect_configuration,REQUIRED,FLAGS,REDIRECT


def test_synthetic_preflight_never_echoes_values():
    values={name:'synthetic-private-value' for name in REQUIRED}
    values.update(META_APP_ID='123',META_CONFIG_ID='456',META_TEST_ACCOUNT_ID='789',META_MODE='development',META_REDIRECT_URI=REDIRECT,META_ENCRYPTION_KEY=Fernet.generate_key().decode())
    result=inspect_configuration(values)
    assert result['configuration_valid'] and result['isolated_profile_all_modules_off']
    assert not result['real_oauth_verified'] and result['network_requests']==0
    output=json.dumps(result)
    assert all(str(value) not in output for value in values.values())


def test_synthetic_preflight_empty_invalid_or_enabled_not_ready():
    assert not inspect_configuration({})['configuration_valid']
    result=inspect_configuration({'META_APP_ID':'１２３','META_MODE':'live','META_ENCRYPTION_KEY':'invalid','META_REDIRECT_URI':REDIRECT+'/'})
    for name in ('META_APP_ID','META_MODE','META_ENCRYPTION_KEY','META_REDIRECT_URI'):
        assert result['variables'][name]=='zły format'
    for name in FLAGS:
        assert not inspect_configuration({name:'true'})['isolated_profile_all_modules_off']
        assert inspect_configuration({name:'invalid'})['variables'][name]=='zły format'
