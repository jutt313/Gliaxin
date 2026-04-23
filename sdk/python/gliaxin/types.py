from dataclasses import dataclass
from typing import Optional


@dataclass
class Memory:
    memory_id: str
    content: str
    category: str
    memory_type: str
    importance: float
    slot: Optional[str]
    status: str
    scope: str
    agent_id: Optional[str]
    created_at: str


@dataclass
class MemoryList:
    memories: list[Memory]
    total: int
    page: int
    pages: int


@dataclass
class AddResult:
    raw_id: str
    status: str


@dataclass
class AddTurnResult:
    turn_id: str
    raw_ids: list[str]
    status: str


@dataclass
class ForgetResult:
    deleted: bool


@dataclass
class ReprocessResult:
    queued: int


@dataclass
class Conflict:
    conflict_id: str
    slot: Optional[str]
    old_memory: dict
    new_memory: dict
    status: str
    created_at: str


@dataclass
class ConflictList:
    conflicts: list[Conflict]
    total: int


@dataclass
class ResolveResult:
    resolved: bool
    winner: str


@dataclass
class Agent:
    agent_id: str
    name: str
    created_at: str


@dataclass
class AgentList:
    agents: list[Agent]
    total: int


@dataclass
class RegisterResult:
    agent_id: str
    name: str
    created_at: str
    registered: bool


@dataclass
class DeleteResult:
    deleted: bool
    agent_id: str


@dataclass
class RawRecord:
    raw_id: str
    content: str
    processing_status: str
    agent_id: Optional[str]
    created_at: str
    metadata: Optional[dict] = None


@dataclass
class RawList:
    records: list['RawRecord']
    total: int
    page: int
    pages: int


@dataclass
class FixResult:
    queued: bool
    memory_id: str
    raw_id: str
