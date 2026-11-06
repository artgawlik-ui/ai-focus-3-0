"""Pure recurrence rules; no database, network or customer data."""
import pytest
from backend.native_planning import recurring_due

@pytest.mark.parametrize('source,days,expected',[
 ('2027-03-27T01:30:00+00:00',1,'2027-03-29T00:30:00+00:00'),
 ('2027-03-21T01:30:00+00:00',7,'2027-04-04T00:30:00+00:00'),
 ('2027-10-30T00:30:00+00:00',1,'2027-10-31T00:30:00+00:00'),
 ('2027-03-27T08:00:00+00:00',1,'2027-03-28T07:00:00+00:00'),
])
def test_recurrence_preserves_wall_time_without_nonexistent_slots(source,days,expected):
    assert recurring_due(source,days)==expected
