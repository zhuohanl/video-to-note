from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class QueueMessage:
    id: str
    body: dict[str, object]
    attempt: int = 1


@dataclass(frozen=True)
class DeadLetter:
    message: QueueMessage
    reason: str


class QueueProvider(Protocol):
    def send(self, message: dict[str, object]) -> str: ...

    def receive(self) -> QueueMessage | None: ...

    def complete(self, message: QueueMessage) -> None: ...

    def dead_letter(self, message: QueueMessage, reason: str) -> None: ...


class InMemoryQueue:
    def __init__(self) -> None:
        self._messages: deque[QueueMessage] = deque()
        self.dead_letters: list[DeadLetter] = []
        self._next_id = 1

    def send(self, message: dict[str, object]) -> str:
        message_id = f"mem-{self._next_id}"
        self._next_id += 1
        raw_attempt = message.get("attempt", 1)
        attempt = raw_attempt if isinstance(raw_attempt, int) else 1
        self._messages.append(QueueMessage(id=message_id, body=message, attempt=attempt))
        return message_id

    def receive(self) -> QueueMessage | None:
        if not self._messages:
            return None
        return self._messages[0]

    def complete(self, message: QueueMessage) -> None:
        try:
            self._messages.remove(message)
        except ValueError:
            return

    def dead_letter(self, message: QueueMessage, reason: str) -> None:
        self.complete(message)
        self.dead_letters.append(DeadLetter(message=message, reason=reason))
