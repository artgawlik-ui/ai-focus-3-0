import copy,pytest
from scripts.data_release_gate import compare_snapshots


def test_identical_synthetic_snapshot_and_fail_closed_changes():
    before={'salons':{'count':2,'sha256':'a'*64},'users':{'count':3,'sha256':'b'*64}}
    assert compare_snapshots(before,copy.deepcopy(before))['tables']==2
    variants=[{}, {'salons':before['salons']}, {**before,'salons':{'count':1,'sha256':'a'*64}}, {**before,'salons':{'count':2,'sha256':'c'*64}}, {**before,'salons':{'count':-1,'sha256':'a'*64}}]
    for after in variants:
        with pytest.raises(ValueError):compare_snapshots(before,after)
