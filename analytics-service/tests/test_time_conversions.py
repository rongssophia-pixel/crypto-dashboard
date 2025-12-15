import math
from datetime import datetime, timezone

from api.grpc_servicer import dt_to_timestamp, timestamp_to_dt


def test_timestamp_to_dt_uses_utc_conversion():
    dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts = dt_to_timestamp(dt)

    converted = timestamp_to_dt(ts)

    assert converted == dt
    # Confirm the underlying seconds match expected UTC epoch seconds
    assert math.isclose(ts.seconds, dt.timestamp(), rel_tol=0, abs_tol=1)


def test_timestamp_round_trip_naive_is_treated_as_utc():
    naive_dt = datetime(2025, 1, 1, 12, 0, 0)  # interpret as UTC
    ts = dt_to_timestamp(naive_dt)

    converted = timestamp_to_dt(ts)

    expected = naive_dt.replace(tzinfo=timezone.utc)
    assert converted == expected
