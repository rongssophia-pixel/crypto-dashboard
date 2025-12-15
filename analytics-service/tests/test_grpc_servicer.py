from datetime import datetime, timezone, timedelta

from api.grpc_servicer import dt_to_timestamp, timestamp_to_dt


def test_dt_to_timestamp_naive_treated_as_utc():
    dt = datetime(2024, 1, 2, 3, 4, 5, 123456)  # naive UTC
    ts = dt_to_timestamp(dt)
    roundtrip = timestamp_to_dt(ts)

    expected = datetime(2024, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc)
    assert ts.seconds == int(expected.timestamp())
    assert ts.nanos == expected.microsecond * 1000
    assert roundtrip == expected


def test_dt_to_timestamp_with_offset_normalizes_to_utc():
    dt = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=-5)))
    ts = dt_to_timestamp(dt)
    roundtrip = timestamp_to_dt(ts)

    expected_utc = dt.astimezone(timezone.utc)
    assert roundtrip == expected_utc
    assert ts.seconds == int(expected_utc.timestamp())
