import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any


@dataclass
class TraceContext:
    trace_id: str
    user_request: str
    start_time: datetime


@dataclass
class TaskEvent:
    event_type: str
    trace_id: str
    timestamp: datetime
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type,
            'trace_id': self.trace_id,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'TaskEvent':
        return cls(
            event_type=d['event_type'],
            trace_id=d['trace_id'],
            timestamp=datetime.fromisoformat(d['timestamp']),
            data=d['data']
        )


class EventSink(ABC):
    @abstractmethod
    def emit(self, event: TaskEvent) -> None:
        pass


class FileEventSink(EventSink):
    def __init__(self, file_path: str):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    def emit(self, event: TaskEvent) -> None:
        with open(self.file_path, 'a') as f:
            json.dump(event.to_dict(), f)
            f.write('\n')
