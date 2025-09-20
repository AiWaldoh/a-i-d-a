from dataclasses import dataclass
from typing import Protocol, List, Dict, Optional, Any
from datetime import datetime


@dataclass
class Message:
    role: str
    content: str
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MemoryPort(Protocol):
    def append(self, thread_id: str, msg: Message) -> None:
        ...
    
    def last_events(self, thread_id: str, n: int) -> List[Message]:
        ...
    
    def summary(self, thread_id: str) -> str:
        ...
    
    def update_summary(self, thread_id: str, text: str) -> None:
        ...


class InMemoryMemory:
    def __init__(self):
        self._events: Dict[str, List[Message]] = {}
        self._summaries: Dict[str, str] = {}
    
    def append(self, thread_id: str, msg: Message) -> None:
        if thread_id not in self._events:
            self._events[thread_id] = []
        self._events[thread_id].append(msg)
    
    def last_events(self, thread_id: str, n: int) -> List[Message]:
        return self._events.get(thread_id, [])[-n:]
    
    def summary(self, thread_id: str) -> str:
        return self._summaries.get(thread_id, "")
    
    def update_summary(self, thread_id: str, text: str) -> None:
        self._summaries[thread_id] = text

