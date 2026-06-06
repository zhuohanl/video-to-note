from __future__ import annotations

import json
from uuid import uuid4

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from common import require_env, require_real


def main() -> int:
    if not require_real():
        return 0
    env = require_env("AZURE_SERVICEBUS_FULLY_QUALIFIED_NAMESPACE", "AZURE_SERVICEBUS_QUEUE")
    credential = DefaultAzureCredential()
    body = json.dumps({"job_id": f"spike-{uuid4()}", "attempt": 1})
    with ServiceBusClient(env["AZURE_SERVICEBUS_FULLY_QUALIFIED_NAMESPACE"], credential) as client:
        sender = client.get_queue_sender(env["AZURE_SERVICEBUS_QUEUE"])
        with sender:
            sender.send_messages(ServiceBusMessage(body))
        receiver = client.get_queue_receiver(env["AZURE_SERVICEBUS_QUEUE"], max_wait_time=20)
        with receiver:
            messages = receiver.receive_messages(max_message_count=1, max_wait_time=20)
            if not messages:
                raise RuntimeError("no Service Bus message received")
            receiver.complete_message(messages[0])
    print(json.dumps({"round_trip": True, "body": body}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
