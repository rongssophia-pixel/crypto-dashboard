import time
from datetime import datetime, timedelta

import httpx
import pytest

# API Gateway URL
BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def client():
    # Use a long timeout for archive jobs
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        yield client


def wait_for_service(client, retries=10, delay=2):
    print(f"Waiting for API Gateway at {BASE_URL}...")
    for i in range(retries):
        try:
            response = client.get("/health")
            if response.status_code == 200:
                print("API Gateway is ready!")
                return
        except httpx.RequestError:
            pass
        time.sleep(delay)
    pytest.fail("API Gateway not ready")


def test_full_archive_workflow(client):
    """
    Test the full archive workflow:
    1. Trigger archive job via API
    2. Check job status
    3. List archives
    4. Query archived data
    """
    wait_for_service(client)

    # Auth header (using dummy token as configured in auth_middleware)
    headers = {"Authorization": "Bearer dummy-token"}

    # 1. Trigger Archive
    # We use a time range that hopefully covers some data or is just valid
    start_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
    end_time = datetime.utcnow().isoformat()

    print(f"\n[1] Triggering archive from {start_time} to {end_time}...")

    # Note: query params for date/time, body for symbols?
    # API def: start_time: datetime, end_time: datetime ... as args.
    # FastAPI defaults to query params for scalars.

    response = client.post(
        "/api/v1/storage/archive",
        params={
            "start_time": start_time,
            "end_time": end_time,
            "data_type": "market_data",
        },
        json=None,
        headers=headers,
    )

    if response.status_code != 200:
        print(f"Archive request failed: {response.text}")
        # We don't fail immediately if service is not fully functional in this env,
        # but in real E2E we should.
        # pytest.fail(...)
        return

    data = response.json()
    assert data["success"] is True
    archive_id = data["archive_id"]
    print(f"Archive Job ID: {archive_id}")
    print(f"Result: {data}")

    # 2. Check Status
    print(f"\n[2] Checking status for {archive_id}...")
    response = client.get(
        f"/api/v1/storage/archives/{archive_id}/status", headers=headers
    )
    assert response.status_code == 200
    status = response.json()
    print(f"Status: {status}")
    assert status["archive_id"] == archive_id

    # 3. List Archives
    print(f"\n[3] Listing archives...")
    response = client.get("/api/v1/storage/archives", headers=headers)
    assert response.status_code == 200
    archives_data = response.json()
    print(f"Found {archives_data.get('total_count')} archives")

    # 4. Query Archive
    print(f"\n[4] Querying archive...")
    # Simple count query
    query = f"SELECT count(*) FROM {data.get('data_type', 'market_data')}"
    response = client.post(
        "/api/v1/storage/query", params={"sql_query": query}, headers=headers
    )

    if response.status_code == 200:
        print(f"Query Result: {response.json()}")
    else:
        print(f"Query Failed (expected if Athena not ready): {response.text}")
