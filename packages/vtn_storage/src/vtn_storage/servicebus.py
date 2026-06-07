from __future__ import annotations

import json
import os
from collections.abc import Iterable

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage, ServiceBusSubQueue
from azure.servicebus._common.message import ServiceBusReceivedMessage

from vtn_storage.queue import QueueMessage


class ServiceBusQueue:
    def __init__(
        self,
        *,
        queue_name: str,
        connection_string: str | None = None,
        fully_qualified_namespace: str | None = None,
    ) -> None:
        if connection_string:
            self._client = ServiceBusClient.from_connection_string(connection_string)
        elif fully_qualified_namespace:
            self._client = ServiceBusClient(
                fully_qualified_namespace=fully_qualified_namespace,
                credential=DefaultAzureCredential(),
            )
        else:
            msg = "connection_string or fully_qualified_namespace is required"
            raise ValueError(msg)
        self._queue_name = queue_name
        self._received: dict[str, ServiceBusReceivedMessage] = {}

    @classmethod
    def from_env(cls) -> ServiceBusQueue:
        queue_name = os.environ.get("AZURE_SERVICE_BUS_QUEUE_NAME", "jobs")
        return cls(
            queue_name=queue_name,
            connection_string=os.environ.get("AZURE_SERVICE_BUS_CONNECTION_STRING"),
            fully_qualified_namespace=os.environ.get(
                "AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE",
            ),
        )

    def send(self, message: dict[str, object]) -> str:
        message_id = _message_id(message)
        payload = json.dumps(message, sort_keys=True)
        with self._client.get_queue_sender(queue_name=self._queue_name) as sender:
            sender.send_messages(
                ServiceBusMessage(
                    payload,
                    content_type="application/json",
                    message_id=message_id,
                ),
            )
        return message_id

    def receive(self) -> QueueMessage | None:
        with self._client.get_queue_receiver(
            queue_name=self._queue_name,
            max_wait_time=5,
        ) as receiver:
            messages = receiver.receive_messages(max_message_count=1, max_wait_time=5)
            if not messages:
                return None
            raw = messages[0]
            body = _decode_body(raw.body)
            delivery_count = raw.delivery_count or 1
            attempt = body.get("attempt", delivery_count)
            queue_message = QueueMessage(
                id=str(raw.message_id),
                body=body,
                attempt=attempt if isinstance(attempt, int) else delivery_count,
            )
            self._received[queue_message.id] = raw
            return queue_message

    def complete(self, message: QueueMessage) -> None:
        raw = self._received.pop(message.id, None)
        if raw is None:
            return
        with self._client.get_queue_receiver(queue_name=self._queue_name) as receiver:
            receiver.complete_message(raw)

    def dead_letter(self, message: QueueMessage, reason: str) -> None:
        raw = self._received.pop(message.id, None)
        if raw is None:
            return
        with self._client.get_queue_receiver(queue_name=self._queue_name) as receiver:
            receiver.dead_letter_message(raw, reason=reason)

    def receive_dead_letter(self) -> QueueMessage | None:
        with self._client.get_queue_receiver(
            queue_name=self._queue_name,
            sub_queue=ServiceBusSubQueue.DEAD_LETTER,
            max_wait_time=5,
        ) as receiver:
            messages = receiver.receive_messages(max_message_count=1, max_wait_time=5)
            if not messages:
                return None
            raw = messages[0]
            body = _decode_body(raw.body)
            receiver.complete_message(raw)
            delivery_count = raw.delivery_count or 1
            attempt = body.get("attempt", delivery_count)
            return QueueMessage(
                id=str(raw.message_id),
                body=body,
                attempt=attempt if isinstance(attempt, int) else delivery_count,
            )

    def close(self) -> None:
        self._client.close()


def _message_id(message: dict[str, object]) -> str:
    job_id = message.get("job_id")
    attempt = message.get("attempt", 1)
    if job_id:
        return f"{job_id}:{attempt}"
    return json.dumps(message, sort_keys=True)


def _decode_body(body: str | bytes | Iterable[bytes]) -> dict[str, object]:
    if isinstance(body, str):
        raw = body
    elif isinstance(body, bytes):
        raw = body.decode()
    else:
        raw = b"".join(body).decode()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        msg = "Service Bus payload must be a JSON object"
        raise ValueError(msg)
    return payload
