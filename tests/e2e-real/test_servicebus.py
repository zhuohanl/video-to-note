from __future__ import annotations

import os
from uuid import uuid4

import pytest
from vtn_storage.servicebus import ServiceBusQueue

pytestmark = pytest.mark.real_infra


def _queue() -> ServiceBusQueue:
    if os.environ.get("RUN_REAL") != "1":
        pytest.skip("set RUN_REAL=1 to run live Service Bus tests")
    if not (
        os.environ.get("AZURE_SERVICE_BUS_CONNECTION_STRING")
        or os.environ.get("AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE")
    ):
        pytest.skip("missing Service Bus connection string or namespace")
    return ServiceBusQueue.from_env()


def test_servicebus_round_trip_and_dead_letter() -> None:
    queue = _queue()
    job_id = str(uuid4())
    message_id = queue.send({"job_id": job_id, "attempt": 1})
    assert message_id == f"{job_id}:1"

    received = queue.receive()
    assert received is not None
    assert received.body == {"job_id": job_id, "attempt": 1}
    assert received.attempt >= 1
    queue.complete(received)

    poison_job_id = str(uuid4())
    queue.send({"job_id": poison_job_id, "attempt": 2})
    poison = queue.receive()
    assert poison is not None
    queue.dead_letter(poison, "test-poison")

    dead = queue.receive_dead_letter()
    assert dead is not None
    assert dead.body["job_id"] == poison_job_id
